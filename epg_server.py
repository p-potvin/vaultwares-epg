"""Bounded XMLTV/M3U proxy for the private VaultWares EPG service."""

from __future__ import annotations

import gzip
import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen


MAX_EPG_BYTES = 64 * 1024 * 1024
MAX_PLAYLIST_BYTES = 8 * 1024 * 1024


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE configuration without overriding process values."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"invalid .env line in {path}")
        os.environ.setdefault(key.strip(), value.strip())


class RemoteCache:
    def __init__(self, source_url: str, ttl_seconds: int, max_bytes: int, validator) -> None:
        self.source_url = source_url
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self.validator = validator
        self._body: bytes | None = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    @property
    def age_seconds(self) -> int | None:
        return None if self._body is None else max(0, int(time.time() - self._fetched_at))

    def get(self, force_refresh: bool = False) -> bytes:
        if not force_refresh and self._body is not None and time.time() - self._fetched_at < self.ttl_seconds:
            return self._body
        with self._lock:
            if not force_refresh and self._body is not None and time.time() - self._fetched_at < self.ttl_seconds:
                return self._body
            request = Request(self.source_url, headers={"User-Agent": "VaultWares-EPG/1.0"})
            with urlopen(request, timeout=30) as response:
                body = response.read(self.max_bytes + 1)
            if len(body) > self.max_bytes:
                raise ValueError("upstream response exceeds the configured safety limit")
            self.validator(body)
            self._body = body
            self._fetched_at = time.time()
            return body


class LocalXmltvCache:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._signature: tuple[int, int] | None = None
        self._body: bytes | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.path.is_file()

    def get(self) -> bytes:
        stat = self.path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        if self._body is not None and self._signature == signature:
            return self._body
        if stat.st_size > 256 * 1024 * 1024:
            raise ValueError("local XMLTV file exceeds the 256 MiB safety limit")
        with self._lock:
            body = self.path.read_bytes()
            if b"<tv" not in body[:4096]:
                raise ValueError("local file is not XMLTV")
            self._body = body
            self._signature = signature
            return body


def validate_epg(body: bytes) -> None:
    payload = gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body
    if b"<tv" not in payload[:4096]:
        raise ValueError("upstream response is not XMLTV")


def validate_playlist(body: bytes) -> None:
    if not body.lstrip().startswith(b"#EXTM3U"):
        raise ValueError("upstream response is not an M3U playlist")


def make_handler(epg: RemoteCache, playlist: RemoteCache | None, french: LocalXmltvCache | None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "VaultWaresEPG/1.0"

        def do_GET(self) -> None:  # noqa: N802
            request = urlsplit(self.path)
            if request.path == "/health":
                self._send_json({
                    "ok": True,
                    "epg_cache_age_seconds": epg.age_seconds,
                    "playlist_cache_age_seconds": playlist.age_seconds if playlist else None,
                    "french_file_available": french.available if french else False,
                })
                return
            try:
                if request.path in ("/", "/epg.xml", "/epg.xml.gz"):
                    raw = epg.get()
                    body = gzip.compress(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw, compresslevel=6, mtime=0) if request.path.endswith(".gz") else (gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
                    self._send(body, "application/gzip" if request.path.endswith(".gz") else "application/xml; charset=utf-8", epg.ttl_seconds)
                    return
                if request.path == "/playlist.m3u" and playlist:
                    force = parse_qs(request.query).get("refresh") == ["1"]
                    self._send(playlist.get(force), "application/x-mpegURL; charset=utf-8", playlist.ttl_seconds)
                    return
                if request.path in ("/epg-fr.xml", "/epg-fr.xml.gz") and french and french.available:
                    raw = french.get()
                    body = gzip.compress(raw, compresslevel=6, mtime=0) if request.path.endswith(".gz") else raw
                    self._send(body, "application/gzip" if request.path.endswith(".gz") else "application/xml; charset=utf-8", 3600)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as exc:
                print(f"request failed: {type(exc).__name__}: {exc}", flush=True)
                self.send_error(HTTPStatus.BAD_GATEWAY, "EPG source unavailable")

        def _send(self, body: bytes, content_type: str, max_age: int) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", f"public, max-age={max_age}")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, value: dict) -> None:
            self._send(json.dumps(value).encode("utf-8"), "application/json", 0)

        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.client_address[0]} - {fmt % args}", flush=True)

    return Handler


def main() -> None:
    root = Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    epg_url = os.environ["EPG_SOURCE_URL"]
    ttl = int(os.getenv("EPG_CACHE_SECONDS", "86400"))
    playlist_url = os.getenv("M3U_PLAYLIST_SOURCE_URL", "")
    french_path = os.getenv("EPG_FRENCH_FILE", "")
    if french_path and not Path(french_path).is_absolute():
        french_path = str(root / french_path)
    if ttl < 60:
        raise SystemExit("EPG_CACHE_SECONDS must be at least 60")
    epg = RemoteCache(epg_url, ttl, MAX_EPG_BYTES, validate_epg)
    playlist = RemoteCache(playlist_url, ttl, MAX_PLAYLIST_BYTES, validate_playlist) if playlist_url else None
    french = LocalXmltvCache(french_path) if french_path else None
    host, port = os.getenv("EPG_HOST", "0.0.0.0"), int(os.getenv("EPG_PORT", "8787"))
    print(f"Serving VaultWares EPG on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), make_handler(epg, playlist, french)).serve_forever()


if __name__ == "__main__":
    main()
