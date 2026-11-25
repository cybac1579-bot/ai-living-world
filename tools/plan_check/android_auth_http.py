import json
from urllib.parse import urlencode


class AuthTransportError(Exception):
    """Only fixed labels and protocol status codes may reach the UI."""


def request(address, data, timeout, *, send=None):
    if send is None:
        from java import jclass
        send = jclass("com.ailivingworld.mobile.PlanAuthHttp").request
    status, body = send(address, urlencode(data) if data is not None else None, int(timeout * 1000))
    status = str(status)
    reasons = {"dns": "서버 주소 조회 실패", "tls": "보안 연결 실패", "timeout": "응답 시간 초과",
               "network": "네트워크 연결 실패", "endpoint": "요청 주소 확인 실패", "size": "응답 크기 초과"}
    if status in reasons:
        raise AuthTransportError(reasons[status])
    if not (len(status) == 3 and status.isascii() and status.isdigit()):
        raise AuthTransportError("응답 상태 확인 실패")
    try:
        obj = json.loads(str(body))
    except ValueError:
        obj = None
    if status.startswith("2"):
        if isinstance(obj, dict):
            return obj
        raise AuthTransportError("응답 형식 확인 실패")
    error = obj.get("error") if isinstance(obj, dict) else None
    if isinstance(error, dict):
        error = error.get("code")
    allowed = ("invalid_grant", "invalid_client", "invalid_request", "invalid_scope", "access_denied")
    detail = " · " + error if error in allowed else ""
    raise AuthTransportError("HTTP " + status + detail)
