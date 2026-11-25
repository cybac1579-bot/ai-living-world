"""Inject synthetic OIDC cases ONLY in the CI emulator copy, before first engine start."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

app = Path(sys.argv[1]) / "app"
gradle = app / "build.gradle"
source = gradle.read_text()
assert source.count("abiFilters 'arm64-v8a'") == 1
gradle.write_text(source.replace("abiFilters 'arm64-v8a'", "abiFilters 'x86_64'"))
now = int(time.time())
claims = {"iss":"https://auth.openai.com","sub":"ci","aud":"ci-client","nonce":"ci-attempt",
          "iat":now-300,"exp":now+86400}
message = ".".join(b64(json.dumps(part).encode()) for part in
                   ({"alg":"RS256","kid":"fixture"}, claims))
with tempfile.TemporaryDirectory() as tmp:
    key = str(Path(tmp)/"key")
    subprocess.run(["openssl","genrsa","-out",key,"2048"],check=True)
    modulus = subprocess.check_output(["openssl","rsa","-in",key,"-modulus","-noout"]).decode().strip().split("=")[1]
    signature = subprocess.check_output(["openssl","dgst","-sha256","-sign",key],input=message.encode())
jwks = {"keys":[{"kty":"RSA","kid":"fixture","alg":"RS256","e":"AQAB","n":b64(bytes.fromhex(modulus))}]}
jwt = message+"."+b64(signature)
probe = f"""
    from siwc_client import validate_identity, SIWCError
    from java import jclass
    signed = {jwt!r}
    keys = {jwks!r}
    assert validate_identity(signed, "ci-client", "ci-attempt", keys)["subject"] == "ci"
    try:
        validate_identity(signed, "ci-client", "unrelated-attempt", keys)
    except SIWCError:
        pass
    else:
        raise AssertionError("Android identity accepted an unrelated nonce")
    jclass("android.util.Log").i("ALW_PLAN_CHECK", "ANDROID_SIGNED_IDENTITY_PASS")
"""
mobile = app / "src/main/python/mobile_embedded.py"
s = mobile.read_text()
anchor = "    private, sample, web = _paths(private_files,resources)"
assert s.count(anchor) == 1
mobile.write_text(s.replace(anchor,probe+anchor))
