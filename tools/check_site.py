#!/usr/bin/env python3
"""Static checks for site/ before a release.

- every relative href/src resolves to a file in site/, and every #anchor exists
- no external resource loads (stylesheets, scripts, images, iframes, fonts)
- each page: <html lang="en">, one <h1>, <title>, meta description, canonical
- no claims the product must not make (root cause, regression detection, anonymity, ...)
- every Beta Kit ZIP matches its .sha256; sample files are byte-identical to a base revision

Usage: python3 tools/check_site.py [base-revision]   (default 83cb11f)
"""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
SKIP_DIRS = {"samples"}  # service output, checked byte-for-byte instead

FORBIDDEN = [
    r"automatic(ally)? root[- ]cause",
    r"root[- ]cause analysis",
    r"detects? regressions?",
    r"regression detected",
    r"fully anonymous",
    r"guarantee",
    r"upload (your|the) (raw )?mcap",
    r"\d+\s*% (faster|cheaper|savings?)",
    r"trusted by",
    r"benchmark (your|against peers)",
]


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self.h1 = 0
        self.lang = None
        self.title = False
        self.meta_desc = False
        self.canonical = False
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.meta_desc = True
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = True
        for attr in ("href", "src"):
            if a.get(attr) and not (tag == "link" and a.get("rel") == "canonical"):
                self.links.append((tag, a[attr]))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else "83cb11f"
    problems: list[str] = []
    pages = {
        p: Page() for p in SITE.rglob("*.html")
        if not (set(p.relative_to(SITE).parts) & SKIP_DIRS)
    }
    for path, page in pages.items():
        page.feed(path.read_text(encoding="utf-8"))

    for path, page in pages.items():
        rel = path.relative_to(SITE)
        is_stub = 'http-equiv="refresh"' in path.read_text(encoding="utf-8")
        if page.lang != "en":
            problems.append(f"{rel}: html lang is {page.lang!r}")
        if not page.title:
            problems.append(f"{rel}: no <title>")
        if page.h1 != 1:
            problems.append(f"{rel}: {page.h1} <h1> elements")
        if rel.name != "404.html" and not page.canonical:
            problems.append(f"{rel}: no canonical link")
        if rel.name != "404.html" and not is_stub and not page.meta_desc:
            problems.append(f"{rel}: no meta description")

        text = " ".join(page.text)
        for pattern in FORBIDDEN:
            for m in re.finditer(pattern, text, re.I):
                window = text[max(0, m.start() - 60): m.end() + 20]
                if not re.search(r"\b(not|never|no|does not|doesn't|don't)\b", window, re.I):
                    problems.append(f"{rel}: forbidden claim {m.group(0)!r}")

        for tag, url in page.links:
            parts = urlsplit(url)
            if parts.scheme in ("http", "https"):
                if tag in ("link", "script", "img", "iframe", "source") and parts.netloc:
                    problems.append(f"{rel}: external resource {url}")
                continue
            if parts.scheme in ("mailto", "data") or url.startswith("data:"):
                continue
            if rel.name == "404.html":
                target = SITE / parts.path.lstrip("/") if parts.path else path
                if parts.path.endswith("/"):
                    target = target / "index.html"
            else:
                target = (path.parent / parts.path).resolve() if parts.path else path
            if not target.exists():
                problems.append(f"{rel}: broken link {url}")
                continue
            if parts.fragment and target.suffix == ".html" and target in pages:
                if parts.fragment not in pages[target].ids:
                    problems.append(f"{rel}: missing anchor {url}")

    css = (SITE / "assets/site.css").read_text(encoding="utf-8")
    for url in re.findall(r"url\(\"?([^\")]+)\"?\)", css):
        if url.startswith("http"):
            problems.append(f"site.css: external url {url}")
        elif not (SITE / "assets" / url).exists():
            problems.append(f"site.css: missing {url}")

    # Evidence Yellow is a highlight device: never a text colour (1.6:1 on white).
    for m in re.finditer(r"(?<![-\w])color:\s*(var\(--window\)|#f5c518)", css, re.I):
        problems.append(f"site.css: Evidence Yellow used as text colour near: {css[max(0, m.start() - 60):m.end()]!r}")

    kit_hashes = []
    for kit in sorted((SITE / "downloads").glob("velune-adapter-beta-kit*.zip")):
        line = (kit.parent / f"{kit.name}.sha256").read_text().split()
        got = sha256(kit.read_bytes()).hexdigest()
        if line != [got, kit.name]:
            problems.append(f"{kit.name}: sha256 {got} does not match {kit.name}.sha256 ({' '.join(line)})")
        kit_hashes.append(f"{kit.name} {got}")

    for f in sorted((SITE / "samples").iterdir()):
        if f.is_file():
            old = subprocess.run(
                ["git", "show", f"{base}:site/samples/{f.name}"],
                cwd=REPO, capture_output=True, check=False,
            ).stdout
            if old != f.read_bytes():
                problems.append(f"samples/{f.name} differs from {base}")

    print(f"pages checked: {len(pages)}; Beta Kits: {'; '.join(kit_hashes)}")
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
