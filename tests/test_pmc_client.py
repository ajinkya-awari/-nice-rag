from email.message import Message
import gzip
import urllib.parse
import urllib.request
import zlib

import pytest

from src.open_registry import OPEN_EVIDENCE_SOURCES
from src.pmc_client import (
    PMC_OAI_BASE_URL,
    PmcClientError,
    SameHostRedirectHandler,
    build_oai_url,
    fetch_pmc_record,
)


XML_BODY = b'<?xml version="1.0"?><OAI-PMH></OAI-PMH>'


class FakeResponse:
    def __init__(
        self,
        body: bytes = XML_BODY,
        *,
        status: int = 200,
        content_type: str = "text/xml; charset=UTF-8",
        content_encoding: str = "",
        final_url: str = PMC_OAI_BASE_URL,
    ) -> None:
        self._body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_encoding:
            self.headers["Content-Encoding"] = content_encoding
        self._final_url = final_url

    def read(self, amount: int = -1) -> bytes:
        return self._body if amount < 0 else self._body[:amount]

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class RecordingTransport:
    def __init__(self, response: FakeResponse | None = None) -> None:
        self.response = response or FakeResponse()
        self.calls: list[tuple[urllib.request.Request, float]] = []

    def open(
        self, request: urllib.request.Request, timeout: float
    ) -> FakeResponse:
        self.calls.append((request, timeout))
        return self.response


def test_oai_url_uses_exact_getrecord_contract() -> None:
    parsed = urllib.parse.urlsplit(build_oai_url(OPEN_EVIDENCE_SOURCES[0]))

    assert (parsed.scheme, parsed.netloc, parsed.path) == (
        "https",
        "pmc.ncbi.nlm.nih.gov",
        "/api/oai/v1/mh/",
    )
    assert urllib.parse.parse_qs(parsed.query) == {
        "verb": ["GetRecord"],
        "identifier": ["oai:pubmedcentral.nih.gov:5256065"],
        "metadataPrefix": ["pmc"],
    }


def test_fetch_sends_bounded_xml_request_and_returns_metadata() -> None:
    transport = RecordingTransport()

    result = fetch_pmc_record(
        OPEN_EVIDENCE_SOURCES[0], transport=transport, timeout_seconds=7.5
    )

    assert result.body == XML_BODY
    assert result.status == 200
    assert result.content_type == "text/xml"
    assert result.final_url == PMC_OAI_BASE_URL
    assert len(transport.calls) == 1
    request, timeout = transport.calls[0]
    headers = {key.casefold(): value for key, value in request.header_items()}
    assert timeout == 7.5
    assert "nice-rag" in headers["user-agent"].casefold()
    assert headers["accept"] == "application/xml,text/xml"
    assert headers["accept-encoding"] == "gzip, deflate"


@pytest.mark.parametrize(
    ("encoding", "encoded"),
    (("gzip", gzip.compress(XML_BODY)), ("deflate", zlib.compress(XML_BODY))),
)
def test_fetch_decodes_supported_compression(encoding: str, encoded: bytes) -> None:
    transport = RecordingTransport(
        FakeResponse(body=encoded, content_encoding=encoding)
    )

    result = fetch_pmc_record(OPEN_EVIDENCE_SOURCES[0], transport=transport)

    assert result.body == XML_BODY


@pytest.mark.parametrize(
    ("response", "message"),
    (
        (FakeResponse(status=503), "HTTP status"),
        (FakeResponse(content_type="text/html"), "content type"),
        (FakeResponse(content_encoding="br"), "content encoding"),
        (
            FakeResponse(final_url="http://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/"),
            "HTTPS",
        ),
        (
            FakeResponse(final_url="https://example.org/api/oai/v1/mh/"),
            "host",
        ),
    ),
)
def test_fetch_rejects_unsafe_response_metadata(
    response: FakeResponse, message: str
) -> None:
    with pytest.raises(PmcClientError, match=message):
        fetch_pmc_record(
            OPEN_EVIDENCE_SOURCES[0], transport=RecordingTransport(response)
        )


def test_fetch_rejects_encoded_or_decoded_size_over_limit() -> None:
    with pytest.raises(PmcClientError, match="size limit"):
        fetch_pmc_record(
            OPEN_EVIDENCE_SOURCES[0],
            transport=RecordingTransport(FakeResponse(body=b"x" * 11)),
            max_bytes=10,
        )

    compressed = gzip.compress(b"x" * 100)
    with pytest.raises(PmcClientError, match="size limit"):
        fetch_pmc_record(
            OPEN_EVIDENCE_SOURCES[0],
            transport=RecordingTransport(
                FakeResponse(body=compressed, content_encoding="gzip")
            ),
            max_bytes=50,
        )


def test_fetch_makes_no_retry_or_fallback_after_transport_failure() -> None:
    class FailingTransport:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, request: urllib.request.Request, timeout: float) -> FakeResponse:
            self.calls += 1
            raise TimeoutError("offline test timeout")

    transport = FailingTransport()
    with pytest.raises(PmcClientError, match="request failed"):
        fetch_pmc_record(OPEN_EVIDENCE_SOURCES[0], transport=transport)
    assert transport.calls == 1


def test_redirect_handler_rejects_off_host_before_following() -> None:
    handler = SameHostRedirectHandler()
    original = urllib.request.Request(build_oai_url(OPEN_EVIDENCE_SOURCES[0]))

    with pytest.raises(PmcClientError, match="redirect host"):
        handler.redirect_request(
            original,
            None,
            302,
            "Found",
            Message(),
            "https://example.org/elsewhere",
        )


def test_redirect_handler_allows_only_same_https_host() -> None:
    handler = SameHostRedirectHandler()
    original = urllib.request.Request(build_oai_url(OPEN_EVIDENCE_SOURCES[0]))

    redirected = handler.redirect_request(
        original,
        None,
        302,
        "Found",
        Message(),
        "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/?next=1",
    )

    assert redirected is not None
    assert redirected.full_url.startswith("https://pmc.ncbi.nlm.nih.gov/")
