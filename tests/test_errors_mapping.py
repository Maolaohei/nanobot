import json

import httpx

from nanobot.utils.errors import ErrorCodes, ToolError, error_json, map_exception


def test_map_exception_proxy():
    info = map_exception(httpx.ProxyError("proxy down"))
    assert info.code == ErrorCodes.HTTP_PROXY


def test_map_exception_timeout():
    info = map_exception(httpx.TimeoutException("timeout"))
    assert info.code == ErrorCodes.HTTP_TIMEOUT


def test_map_exception_http_status():
    # Synthesize a status error by raising HTTPStatusError with a fake response
    req = httpx.Request("GET", "https://example.com")
    resp = httpx.Response(500, request=req)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        info = map_exception(e)
        assert info.code == ErrorCodes.HTTP_STATUS
        assert info.details and info.details.get("status") == 500


def test_error_json_shape():
    j = error_json(ErrorCodes.INVALID_PARAMS, "bad", {"a": 1})
    payload = json.loads(j)
    assert payload["error"] == ErrorCodes.INVALID_PARAMS
    assert payload["message"] == "bad"
    assert payload["details"]["a"] == 1


def test_toolerror_passthrough():
    err = ToolError(info=map_exception(httpx.TimeoutException("t")))
    info = map_exception(err)
    assert info.code == ErrorCodes.HTTP_TIMEOUT
