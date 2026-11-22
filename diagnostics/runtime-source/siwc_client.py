"""User-initiated Sign in with ChatGPT connector for LOCAL open-source ALW.

This code NEVER runs a paid API-key path. Tokens only come from an approved
SIWC OAuth authorization-code/PKCE flow. No login attempt or inference is made
by import. Network calls occur only after user executes a CLI command.

Verified against public OpenAI SIWC preview docs (2026-11-22).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

AUTH_BASE = "https://auth.openai.com"
API_BASE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
SCOPE_REQUIRED = "chatgpt.tokens.use.direct"
ALLOWED_JWT_ALGS = ["RS256", "ES256"]

class SIWCError(ValueError):
    """Safe, credential-free error for presentation to end users."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _json_request(url: str, *, data: dict | None = None, bearer: str | None = None,
                  timeout: int = 25) -> dict:
    """TLS only; URL fixed by this module. Never logs credentials."""
    if not url.startswith((AUTH_BASE + "/", API_BASE + "/")):
        raise SIWCError("untrusted auth/API endpoint")
    headers = {"Accept": "application/json"}
    encoded = None
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if bearer is not None:
        headers["Authorization"] = "Bearer " + bearer
    request = urllib.request.Request(url, data=encoded, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SIWCError(f"OpenAI endpoint returned HTTP {exc.code}; no game state changed") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SIWCError("OpenAI network request failed; no game state changed") from None


@dataclass(frozen=True)
class AuthorizationAttempt:
    state: str
    nonce: str
    verifier: str
    redirect_uri: str
    host_id: str
    client_id: str
    url: str
    new_registration: bool


def create_auth_attempt(host_id: str, *, port: int, client_id: str | None = None) -> AuthorizationAttempt:
    """Create browser URL; no request is sent until caller opens it."""
    if not host_id.startswith("urn:uuid:"):
        raise SIWCError("invalid local host id")
    try:
        uuid.UUID(host_id[len("urn:uuid:"):])
    except ValueError:
        raise SIWCError("invalid local host id") from None
    if type(port) is not int or not (1024 <= port <= 65535):
        raise SIWCError("invalid loopback port")
    fresh = client_id is None
    cid = client_id or "dynamic_agent_client"
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    callback = f"http://127.0.0.1:{port}/auth/callback"
    params = {
        "client_id": cid,
        "ext_agent_host_id": host_id,
        "response_type": "code",
        "redirect_uri": callback,
        "scope": SCOPES,
        "resource": API_BASE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
    }
    if fresh:
        params["agent_name_hint"] = "AI Living World"
    return AuthorizationAttempt(state, nonce, verifier, callback, host_id, cid,
                                AUTH_BASE + "/api/accounts/authorize?" + urllib.parse.urlencode(params), fresh)


def read_callback(attempt: AuthorizationAttempt, params: dict[str, str]) -> tuple[str, str]:
    """Validate state before accepting any returned authorization code."""
    if not secrets.compare_digest(params.get("state", ""), attempt.state):
        raise SIWCError("OAuth state mismatch")
    if params.get("error"):
        raise SIWCError("Sign-in/plan permission was declined")
    code = params.get("code")
    if not isinstance(code, str) or not code:
        raise SIWCError("missing authorization code")
    issued = params.get("client_id")
    if attempt.new_registration:
        if not issued or issued == "dynamic_agent_client" or not issued.startswith("oaiapp_"):
            raise SIWCError("registration missing issued OAuth client ID")
        return code, issued
    if issued and issued != attempt.client_id:
        raise SIWCError("unexpected OAuth client ID")
    return code, attempt.client_id


def validate_identity(id_token: str, client_id: str, nonce: str, jwks: dict) -> dict:
    """Validate OIDC signature, issuer, audience, expiry and nonce. Requires PyJWT."""
    try:
        import jwt
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") not in ALLOWED_JWT_ALGS:
            raise SIWCError("unsupported ID-token signature algorithm")
        kid = header.get("kid")
        keys = [k for k in jwks.get("keys", []) if k.get("kid") == kid and k.get("kty") in ("RSA", "EC")]
        if len(keys) != 1:
            raise SIWCError("ID-token signing key missing/ambiguous")
        key = jwt.PyJWK.from_dict(keys[0]).key
        claims = jwt.decode(id_token, key=key, algorithms=ALLOWED_JWT_ALGS,
                            audience=client_id, issuer=AUTH_BASE, options={"require": ["exp", "iat", "sub", "iss", "aud", "nonce"]})
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise SIWCError("OIDC nonce mismatch")
        return {"subject": claims["sub"], "email": claims.get("email", "")}
    except ImportError:
        raise SIWCError("PyJWT and cryptography are required for secure login") from None
    except SIWCError:
        raise
    except Exception:
        raise SIWCError("ID-token signature or claims verification failed") from None


def exchange_authorization_code(attempt: AuthorizationAttempt, code: str, client_id: str) -> dict:
    return _json_request(AUTH_BASE + "/api/accounts/oauth/token", data={
        "grant_type": "authorization_code", "client_id": client_id, "code": code,
        "code_verifier": attempt.verifier, "redirect_uri": attempt.redirect_uri, "resource": API_BASE,
    })


def finalize_tokens(attempt: AuthorizationAttempt, callback: dict[str, str],
                    token_data: dict, jwks: dict) -> dict:
    _, client_id = read_callback(attempt, callback)
    scopes = str(token_data.get("scope", "")).split()
    if SCOPE_REQUIRED not in scopes:
        raise SIWCError("ChatGPT plan permission was not granted")
    required = ("id_token", "access_token", "refresh_token")
    if any(not isinstance(token_data.get(key), str) or not token_data[key] for key in required):
        raise SIWCError("incomplete token response")
    identity = validate_identity(token_data["id_token"], client_id, attempt.nonce, jwks)
    expires_in = token_data.get("expires_in")
    if type(expires_in) not in (int, float) or expires_in <= 0:
        raise SIWCError("token expiry missing")
    return {"issuer": AUTH_BASE, "subject": identity["subject"], "email": identity["email"],
            "client_id": client_id, "host_id": attempt.host_id, "scopes": scopes,
            "id_token": token_data["id_token"], "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"], "expires_at": time.time() + expires_in}


def read_or_create_host_id(private_dir: Path) -> str:
    private_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    host_path = private_dir / "host-id.txt"
    if host_path.exists():
        host_id = host_path.read_text(encoding="utf-8").strip()
        if not host_id.startswith("urn:uuid:"):
            raise SIWCError("invalid saved host ID")
        uuid.UUID(host_id[9:])
        return host_id
    host_id = "urn:uuid:" + str(uuid.uuid4())
    descriptor = os.open(host_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as f:
        f.write(host_id)
    return host_id


# Windows Defender, indexing tools and file syncing utilities sometimes acquire
# a short-lived sharing lock on a *closed* newly created tempfile.  Windows
# os.replace then raises WinError 32 (sometimes 5).  Replacing only after the
# writer has closed plus bounded retries avoids throwing away an approved login.
_LOCK_RETRY_DELAYS = (0.05, 0.10, 0.15, 0.25, 0.40, 0.50, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70)


def _is_transient_file_lock(exc: OSError) -> bool:
    import errno
    return (getattr(exc, "winerror", None) in (5, 32, 33)
            or exc.errno in (errno.EACCES, errno.EBUSY))


def _retry_file_action(action) -> None:
    """Bounded retry for temporary sharing violations, never sleep after success."""
    for delay in (*_LOCK_RETRY_DELAYS, None):
        try:
            action()
            return
        except OSError as exc:
            if not _is_transient_file_lock(exc):
                raise
            if delay is None:
                raise SIWCError(
                    "Windows locked the local credential file. Close any second "
                    "AI Living World window, wait briefly, then try login again. "
                    "No model request or paid API call was made."
                ) from None
            time.sleep(delay)


def write_credentials(path: Path, credentials: dict):
    """Atomic credential storage with Windows sharing-lock retries.

    Never print the credential dict.  On failure an existing token file is not
    overwritten with partial JSON; the temporary file is cleaned up if possible.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=".siwc-", dir=path.parent)
    written = False
    try:
        try:
            os.fchmod(fd, 0o600)
        except AttributeError:
            # Some Python/Windows runtimes expose chmod but not fchmod.
            pass
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(credentials, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        _retry_file_action(lambda: os.replace(name, path))
        written = True
        os.chmod(path, 0o600)
    finally:
        if not written and os.path.exists(name):
            try:
                _retry_file_action(lambda: os.unlink(name))
            except (OSError, SIWCError):
                # Never print credential-bearing temp paths or file contents.
                # If another process persistently holds the file it will need
                # user-side cleanup after the locking process exits.
                pass


def read_credentials(path: Path) -> dict:
    if not path.is_file():
        raise SIWCError("Not signed in. Run the explicit login command first")
    if os.name != "nt" and path.stat().st_mode & 0o077:
        raise SIWCError("insecure credential-file permissions")
    data = json.loads(path.read_text(encoding="utf-8"))
    if SCOPE_REQUIRED not in data.get("scopes", []):
        raise SIWCError("ChatGPT plan usage is not authorized")
    if not data.get("access_token") or not data.get("refresh_token") or not data.get("client_id"):
        raise SIWCError("incomplete local credentials")
    return data


def refresh_credentials(path: Path, credentials: dict | None = None) -> dict:
    """Renew rotating refresh token; no retry with paid API key."""
    credentials = credentials or read_credentials(path)
    response = _json_request(AUTH_BASE + "/api/accounts/oauth/token", data={
        "grant_type": "refresh_token", "client_id": credentials["client_id"],
        "refresh_token": credentials["refresh_token"], "resource": API_BASE,
    })
    granted = str(response.get("scope", " ".join(credentials["scopes"]))).split()
    if SCOPE_REQUIRED not in granted:
        raise SIWCError("ChatGPT plan permission revoked")
    if not response.get("access_token") or not response.get("refresh_token"):
        raise SIWCError("invalid refresh response")
    updated = {**credentials, "access_token": response["access_token"],
               "refresh_token": response["refresh_token"], "scopes": granted,
               "expires_at": time.time() + int(response.get("expires_in", 3600))}
    write_credentials(path, updated)
    return updated


def oauth_login(private_dir: Path, *, timeout: int = 180, browser_open=None) -> dict:
    """Explicit interactive action; opens system browser and waits on loopback callback.

    No URL, OAuth code, nonce, or token is ever printed by this module.
    """
    import webbrowser
    host_id = read_or_create_host_id(private_dir)
    creds_path = private_dir / "credentials.json"
    client_id = None
    previous = None
    if creds_path.exists():
        previous = read_credentials(creds_path)
        client_id = previous["client_id"]
    receiver = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    attempt = create_auth_attempt(host_id, port=receiver.server_port, client_id=client_id)
    result: dict[str, str] = {}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/auth/callback":
                self.send_error(404); return
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            try:
                normalized = {k: values[0] for k, values in params.items() if len(values) == 1}
                code, issued_client_id = read_callback(attempt, normalized)
                result.update({"code": code, "client_id": issued_client_id, "state": normalized["state"]})
                message = "AI Living World: authorization received. Return to the app."
                status = 200
            except SIWCError:
                message = "AI Living World: authorization failed. Return to the app."
                status = 400
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode())
        def log_message(self, *_):  # NEVER log callback URL containing code
            return
    receiver.RequestHandlerClass = Handler
    receiver.timeout = timeout
    try:
        opener = browser_open if browser_open is not None else webbrowser.open
        if not opener(attempt.url):
            raise SIWCError("system browser could not be opened")
        receiver.handle_request()
    finally:
        receiver.server_close()
    if not result:
        raise SIWCError("OAuth login did not complete")
    token_data = exchange_authorization_code(attempt, result["code"], result["client_id"])
    oidc = _json_request(AUTH_BASE + "/.well-known/openid-configuration")
    jwks_uri = oidc.get("jwks_uri", "")
    if not jwks_uri.startswith(AUTH_BASE + "/"):
        raise SIWCError("untrusted OpenID key endpoint")
    jwks = _json_request(jwks_uri)
    creds = finalize_tokens(attempt, result, token_data, jwks)
    if previous and previous["subject"] != creds["subject"]:
        raise SIWCError("sign-in identity changed; refusing to overwrite account")
    write_credentials(creds_path, creds)
    return {"signed_in": True, "email": creds["email"], "plan_usage_permission": True}


def list_models(access_token: str) -> list[dict]:
    catalog = _json_request(API_BASE + "/models", bearer=access_token)
    models = catalog.get("models", [])
    if not isinstance(models, list):
        raise SIWCError("invalid model catalog")
    return [{"slug": m["slug"], "display_name": m.get("display_name", m["slug"])}
            for m in models if isinstance(m, dict) and m.get("visibility") == "list" and isinstance(m.get("slug"), str)]


def _parse_stream_line(line: str) -> tuple[str | None, Any]:
    if not line.startswith("data:"):
        return None, None
    data = line[5:].lstrip()
    if data == "[DONE]":
        return "done", None
    try:
        event = json.loads(data)
    except json.JSONDecodeError as exc:
        raise SIWCError("invalid streamed response JSON") from exc
    if not isinstance(event, dict):
        raise SIWCError("invalid streamed response event")
    return event.get("type"), event


def collect_response_events(lines, *, max_chars: int = 30000) -> str:
    """Collect only completed streamed text; reject failure/incomplete/abrupt endings."""
    chunks = []
    count = 0
    complete = None
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="strict")
        event_type, event = _parse_stream_line(line.strip("\r\n"))
        if event_type == "response.output_text.delta":
            chunk = event.get("delta")
            if not isinstance(chunk, str):
                raise SIWCError("invalid streamed text delta")
            count += len(chunk)
            if count > max_chars:
                raise SIWCError("stream too long; no game state changed")
            chunks.append(chunk)
        elif event_type in ("response.failed", "response.incomplete", "error"):
            raise SIWCError(f"AI streaming result was {event_type}; no game state changed")
        elif event_type == "response.completed":
            if complete is not None:
                raise SIWCError("multiple completion events")
            complete = event.get("response", {})
        elif event_type == "done":
            break
    if complete is None or complete.get("status", "completed") != "completed":
        raise SIWCError("AI stream ended without response.completed")
    # A completion object carries canonical final assistant text; stream may omit deltas.
    output = complete.get("output") if isinstance(complete, dict) else None
    if isinstance(output, list):
        for msg in output:
            if isinstance(msg, dict) and msg.get("type") == "message" and msg.get("role") == "assistant":
                parts = [p.get("text") for p in msg.get("content", []) if isinstance(p, dict) and p.get("type") == "output_text"]
                if len(parts) == 1 and isinstance(parts[0], str):
                    text = parts[0]
                    if text and len(text) <= max_chars:
                        return text
    text = "".join(chunks)
    if not text:
        raise SIWCError("AI response completed without text")
    return text


def stream_response(access_token: str, model: str, model_context: dict, *, timeout: int = 120) -> str:
    """Calls the public Responses endpoint with OAuth only; never a paid API-key fallback."""
    if not isinstance(model, str) or not model.strip():
        raise SIWCError("model must be selected from the signed-in account catalog")
    instructions = (
        "You narrate a Korean fantasy RPG. Return exactly one JSON object compatible with AI Living World: "
        "{events:[...],scene:{id,beats:[{kind:'narration'|'dialogue',text,speaker_id?}],"
        "choices:[{id,label,effect?}],awaiting_player:boolean,event_image_id?,character_image_id?}}. "
        "Follow the provided rules; never invent player actions or feelings. "
        "Never assume access to private facts not provided. Output valid JSON only."
    )
    payload = {"model": model, "instructions": instructions,
               "input": [{"role": "user", "content": json.dumps(model_context, ensure_ascii=False)}],
               "store": False, "stream": True}
    request = urllib.request.Request(API_BASE + "/responses", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as stream:
            return collect_response_events(stream)
    except urllib.error.HTTPError as exc:
        raise SIWCError(f"ChatGPT-plan response HTTP {exc.code}; game state unchanged") from None
    except (urllib.error.URLError, TimeoutError):
        raise SIWCError("ChatGPT-plan connection interrupted; game state unchanged") from None
