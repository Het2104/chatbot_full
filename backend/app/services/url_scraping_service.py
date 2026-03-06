"""
URL Scraping Service
Fetches a public web page and extracts clean plain text from it.

Security:
- SSRF protection: rejects requests to private/loopback IP ranges
- Only http/https schemes allowed
- 10-second timeout to avoid hanging requests
"""
import ipaddress
import socket
import time
from typing import Dict, Any
from urllib.parse import urlparse

from app.logging_config import get_logger

logger = get_logger(__name__)

# Private / loopback / link-local CIDR ranges to block (SSRF prevention)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC-1918 private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC-1918 private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC-1918 private
    ipaddress.ip_network("169.254.0.0/16"),    # link-local (AWS metadata etc.)
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique-local
]

_REQUEST_TIMEOUT = 10  # seconds
_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB — refuse payloads larger than this
_USER_AGENT = "Mozilla/5.0 (compatible; RAGBot/1.0; +https://github.com/your-org/chatbot)"


def _validate_url(url: str) -> None:
    """
    Raise ValueError if the URL is unsafe or not http/https.
    Resolves the hostname to its IP and checks against blocked ranges.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http and https URLs are allowed (got '{parsed.scheme}').")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    # Resolve hostname → IP
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname '{hostname}': {exc}") from exc

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        for network in _BLOCKED_NETWORKS:
            if ip_obj in network:
                raise ValueError(
                    f"Requests to private/internal addresses are not allowed (resolved to {ip_str})."
                )


class URLScrapingService:
    """Fetches a web page and returns clean plain text."""

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Fetch the given URL and extract plain text.

        Args:
            url: Fully-qualified http/https URL.

        Returns:
            {
                "url":       str,
                "title":     str,   # <title> tag, empty string if missing
                "text":      str,   # main body text
                "num_chars": int,
            }

        Raises:
            ValueError: if the URL is invalid, blocked, or returns no usable content.
            RuntimeError: on network or parse errors.
        """
        import requests
        from bs4 import BeautifulSoup

        start = time.time()
        logger.info(f"Scraping URL: {url}")

        # --- SSRF guard ---
        _validate_url(url)

        # --- Fetch page ---
        try:
            resp = requests.get(
                url,
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
                stream=True,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Request timed out after {_REQUEST_TIMEOUT}s: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Failed to fetch URL: {exc}") from exc

        # Honour content-length and cap download size
        raw = b""
        for chunk in resp.iter_content(chunk_size=65536):
            raw += chunk
            if len(raw) > _MAX_CONTENT_BYTES:
                logger.warning(f"Page exceeds {_MAX_CONTENT_BYTES // (1024*1024)}MB limit, truncating.")
                break

        content_type = resp.headers.get("content-type", "")
        if "text" not in content_type and "html" not in content_type:
            raise ValueError(
                f"URL does not appear to be an HTML page (Content-Type: {content_type})."
            )

        # --- Parse HTML ---
        soup = BeautifulSoup(raw, "html.parser")

        # Remove noise tags — navigation, scripts, styles, etc.
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "noscript", "iframe", "form"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(separator=" ", strip=True)

        elapsed = round(time.time() - start, 2)
        num_chars = len(text)

        logger.info(
            f"Scraped '{title}' from {url} — {num_chars} chars in {elapsed}s"
        )

        if num_chars < 50:
            raise ValueError(
                f"Extracted text is too short ({num_chars} chars). "
                "The page may be JavaScript-rendered or contain no readable content."
            )

        return {
            "url": url,
            "title": title,
            "text": text,
            "num_chars": num_chars,
        }
