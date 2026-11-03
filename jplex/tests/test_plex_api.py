from __future__ import annotations

import httpx

from jplex.plex_api import PlexAPIError, PlexClient


def test_requests_include_plex_token_header() -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(
            200, content=b'<MediaContainer machineIdentifier="machine" />'
        )

    client = PlexClient(
        "http://plex",
        "secret-token",
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.machine_id() == "machine"
    assert seen_headers["x-plex-token"] == "secret-token"


def test_errors_redact_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request, content=b"boom secret-token")

    client = PlexClient(
        "http://plex",
        "secret-token",
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    try:
        client.machine_id()
    except PlexAPIError as error:
        assert "secret-token" not in str(error)
    else:
        raise AssertionError("expected PlexAPIError")
