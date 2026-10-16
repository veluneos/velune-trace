#!/usr/bin/env python3
"""Local preview of site/ with Cloudflare-Pages-like routing.

Serves /path from path.html or path/index.html, applies the 301 rules in
site/_redirects, and answers unknown paths with site/404.html (status 404).
It approximates Pages for local review; it is not Cloudflare itself.

Usage: python3 tools/preview_site.py [port]   (default 8787, binds 127.0.0.1)
"""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlsplit

SITE = Path(__file__).resolve().parent.parent / "site"


def load_redirects() -> dict[str, tuple[str, int]]:
    rules: dict[str, tuple[str, int]] = {}
    path = SITE / "_redirects"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and not line.lstrip().startswith("#"):
                rules[parts[0]] = (parts[1], int(parts[2]) if len(parts) > 2 else 302)
    return rules


REDIRECTS = load_redirects()


def resolve(url_path: str) -> tuple[str, Path | str | None]:
    """Return ("redirect", location) | ("file", path) | ("missing", None)."""
    if url_path in REDIRECTS:
        return "redirect", REDIRECTS[url_path][0]
    rel = url_path.lstrip("/")
    candidate = (SITE / rel).resolve()
    if SITE.resolve() not in candidate.parents and candidate != SITE.resolve():
        return "missing", None
    if candidate.is_dir():
        if not url_path.endswith("/"):
            return "redirect", url_path + "/"
        index = candidate / "index.html"
        return ("file", index) if index.exists() else ("missing", None)
    if candidate.is_file():
        return "file", candidate
    html = candidate.with_name(candidate.name + ".html")
    if html.is_file():
        return "file", html
    return "missing", None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def send_head(self):  # noqa: D401 - http.server hook
        kind, target = resolve(urlsplit(self.path).path)
        if kind == "redirect":
            self.send_response(REDIRECTS.get(urlsplit(self.path).path, (None, 301))[1])
            self.send_header("Location", str(target))
            self.end_headers()
            return None
        if kind == "missing":
            body = (SITE / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return None
        self.path = "/" + str(Path(target).relative_to(SITE))
        return super().send_head()


def main(argv: list[str]) -> int:
    port = int(argv[1]) if len(argv) > 1 else 8787
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Previewing {SITE} at http://127.0.0.1:{port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
