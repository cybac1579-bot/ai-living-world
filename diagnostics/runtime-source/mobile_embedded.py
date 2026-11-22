"""Termux-free embedded Android engine bootstrap (Chaquopy + Android Java shell).

The world engine, OAuth credentials and save journal stay within the app private
files directory. Only the validated local /api/state contract reaches WebView.
No import opens a network connection, browser or consent UI.
"""
from __future__ import annotations
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
from typing import Callable

from live_story import authorized_catalog, initial_demo_store
from siwc_client import SIWCError, oauth_login
from world_engine import WorldError
import vn_server

_DEFAULT_WEB = vn_server.WEB
_DEFAULT_SAMPLE = vn_server.SAMPLE

_LOCK = threading.RLock()
_SERVER = None
_THREAD = None
_MODE = None
_BASE = None
_SESSION_SECRET = None


def _paths(private_files, resources):
    private = Path(private_files).resolve(strict=True)
    root = Path(resources).resolve(strict=True)
    if not private.is_dir() or not root.is_dir() or not root.is_relative_to(private):
        raise ValueError('resources must remain inside app-private directory')
    demo = root / 'examples' / 'live_demo_world.json'
    web = root / 'web'
    expected = [demo, web / 'index.html', web / 'app.js', web / 'style.css', web / 'assets' / 'forest.jpg']
    if not all(p.is_file() and p.resolve().is_relative_to(root) for p in expected):
        raise ValueError('app resources are missing or point outside resource directory')
    return private, demo, web


def _ensure_private(folder):
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    try: folder.chmod(0o700)
    except OSError: pass


def login(private_files, browser_open: Callable[[str],bool], *, auth_fn=oauth_login):
    """Explicit user action: open the Android system browser, not a WebView."""
    private = Path(private_files).resolve(strict=True)
    auth = private / 'auth'
    _ensure_private(auth)
    # Chaquopy Java bridge is a Java object with a public method, not callable.
    if not callable(browser_open) and hasattr(browser_open,'openSystemBrowser'):
        browser_open = browser_open.openSystemBrowser
    if not callable(browser_open):
        raise ValueError('a native system browser opener is required')
    def constrained(url):
        p = urlsplit(url)
        if (p.scheme != 'https' or p.netloc != 'auth.openai.com' or
            p.path != '/api/accounts/authorize' or p.username or p.password or p.fragment):
            return False
        return bool(browser_open(url))
    result = auth_fn(auth,timeout=240,browser_open=constrained)
    if not result.get('plan_usage_permission'):
        raise SIWCError('ChatGPT plan usage permission not granted')
    return 'ChatGPT 로그인과 사용량 공유 권한이 확인됐어. 앱에서 온라인 시작을 눌러줘.'


def start_engine(private_files, resources, offline=False, *, catalog=authorized_catalog):
    """Start a single in-app loopback world server. No duplicate server on rotation."""
    global _SERVER, _THREAD, _MODE, _BASE, _SESSION_SECRET
    private, sample, web = _paths(private_files,resources)
    with _LOCK:
        # Reuse a live server; offline/online switching requires safe restart.
        if _SERVER is not None and _THREAD is not None and _THREAD.is_alive() and _MODE == bool(offline):
            return f'http://127.0.0.1:{_SERVER.server_port}/?access={_SESSION_SECRET}'
        stop_engine()
        auth = private / 'auth';save = private / 'saves' / 'DEMO'
        _ensure_private(auth);_ensure_private(save.parent)
        if offline:
            token,models = None, []
        else:
            if not (auth/'credentials.json').is_file():
                raise SIWCError('휴대폰 앱에서 ChatGPT 로그인을 먼저 승인해줘.')
            token,models = catalog(credentials_dir=auth)
        store = initial_demo_store(save,sample_file=sample)
        vn_server.WEB = web
        vn_server.SAMPLE = sample
        bridge = vn_server.StoryBridge(store,token=token,models=models)
        secret = secrets.token_urlsafe(32)
        server = vn_server.LoopbackServer(('127.0.0.1',0),bridge,bootstrap_secret=secret)
        thread = threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.15},daemon=True,name='alw-android-local')
        try:
            thread.start()
        except BaseException:
            server.server_close()
            raise
        _SERVER,_THREAD,_MODE,_BASE,_SESSION_SECRET = server,thread,bool(offline),private,secret
        return f'http://127.0.0.1:{server.server_port}/?access={secret}'


def stop_engine():
    global _SERVER,_THREAD,_MODE,_BASE,_SESSION_SECRET
    with _LOCK:
        server,thread = _SERVER,_THREAD
        _SERVER=_THREAD=_MODE=_BASE=_SESSION_SECRET=None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=3)
        # Do not leak the temporary mobile asset root into other worlds/tests.
        vn_server.WEB = _DEFAULT_WEB
        vn_server.SAMPLE = _DEFAULT_SAMPLE


def status():
    with _LOCK:
        return {'running': bool(_THREAD and _THREAD.is_alive()), 'mode': 'offline' if _MODE else 'online',
                'port': _SERVER.server_port if _SERVER else None}
