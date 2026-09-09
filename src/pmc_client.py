"""Bounded network client for the official PMC OAI-PMH endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import urllib.error
import urllib.parse
import urllib.request
import zlib

from src.open_registry import OpenEvidenceSource


PMC_HOST = "pmc.ncbi.nlm.nih.gov"
PMC_OAI_BASE_URL = f"https://{PMC_HOST}/api/oai/v1/mh/"
PMC_USER_AGENT = "NICE-RAG/1.0 open-evidence research validation"
ALLOWED_XML_MEDIA_TYPES = frozenset({"application/xml", "text/xml"})


class PmcClientError(RuntimeError):
    """Raised when a PMC response violates the bounded retrieval contract."""


@dataclass(frozen=True, slots=True)
class PmcResponse:
    """Validated response bytes and non-content transport metadata."""

    body: bytes
    status: int
    content_type: str
    final_url: str


class PmcTransport(Protocol):
    """Small injectable transport boundary used by offline tests."""

    def open(
        self, request: urllib.request.Request, timeout: float
    ) -> object: ...


def _is_allowed_url(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.casefold() != "https":
        return False, "HTTPS"
    if parsed.hostname is None or parsed.hostname.casefold() != PMC_HOST:
        return False, "host"
    return True, ""


class SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects before urllib can contact a non-PMC destination."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        allowed, reason = _is_allowed_url(newurl)
        if not allowed:
            raise PmcClientError(f"Unsafe redirect {reason}: destination rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _DefaultTransport:
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(SameHostRedirectHandler())

    def open(self, request: urllib.request.Request, timeout: float) -> object:
        return self._opener.open(request, timeout=timeout)


def build_oai_url(source: OpenEvidenceSource) -> str:
    """Build one exact OAI GetRecord request for a registry source."""
    numeric_pmcid = source.pmcid.removeprefix("PMC")
    query = urllib.parse.urlencode(
        {
            "verb": "GetRecord",
            "identifier": f"oai:pubmedcentral.nih.gov:{numeric_pmcid}",
            "metadataPrefix": "pmc",
        }
    )
    return f"{PMC_OAI_BASE_URL}?{query}"


def _decode_bounded(body: bytes, encoding: str, max_bytes: int) -> bytes:
    if not encoding:
        return body
    if encoding == "gzip":
        window_bits = zlib.MAX_WBITS | 16
    elif encoding == "deflate":
        window_bits = zlib.MAX_WBITS
    else:
        raise PmcClientError(f"Unsupported content encoding: {encoding}")

    try:
        decompressor = zlib.decompressobj(window_bits)
        decoded = decompressor.decompress(body, max_bytes + 1)
        if len(decoded) > max_bytes or decompressor.unconsumed_tail:
            raise PmcClientError("PMC response exceeds decoded size limit")
        decoded += decompressor.flush(max_bytes + 1 - len(decoded))
    except zlib.error as exc:
        raise PmcClientError("PMC response compression is invalid") from exc
    if len(decoded) > max_bytes:
        raise PmcClientError("PMC response exceeds decoded size limit")
    return decoded


def fetch_pmc_record(
    source: OpenEvidenceSource,
    *,
    transport: PmcTransport | None = None,
    timeout_seconds: float = 20.0,
    max_bytes: int = 8_000_000,
) -> PmcResponse:
    """Fetch one PMC full-text record without retrying, writing, or falling back."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")

    url = build_oai_url(source)
    allowed, reason = _is_allowed_url(url)
    if not allowed:
        raise PmcClientError(f"PMC request must use the allowlisted {reason}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": PMC_USER_AGENT,
            "Accept": "application/xml,text/xml",
            "Accept-Encoding": "gzip, deflate",
        },
        method="GET",
    )

    active_transport = transport or _DefaultTransport()
    try:
        with active_transport.open(request, timeout_seconds) as response:
            status = int(response.status)
            content_type = response.headers.get_content_type().casefold()
            content_encoding = (
                response.headers.get("Content-Encoding", "").strip().casefold()
            )
            final_url = str(response.geturl())
            encoded_body = response.read(max_bytes + 1)
    except PmcClientError:
        raise
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        raise PmcClientError(f"PMC request failed: {type(exc).__name__}") from exc

    if status != 200:
        raise PmcClientError(f"Unexpected HTTP status: {status}")
    if content_type not in ALLOWED_XML_MEDIA_TYPES:
        raise PmcClientError(f"Unexpected content type: {content_type}")
    allowed, reason = _is_allowed_url(final_url)
    if not allowed:
        raise PmcClientError(f"PMC response must remain on allowlisted {reason}")
    if len(encoded_body) > max_bytes:
        raise PmcClientError("PMC response exceeds encoded size limit")

    decoded_body = _decode_bounded(encoded_body, content_encoding, max_bytes)
    return PmcResponse(
        body=decoded_body,
        status=status,
        content_type=content_type,
        final_url=final_url,
    )
