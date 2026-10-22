#!/usr/bin/env python3
"""Build the static VeluneOS website pages in site/ from page bodies.

Each page body lives in tools/site_pages/<name>.html. This script wraps it in
the shared head, navigation and footer so every page uses identical chrome.
`{root}` in a body is replaced by the relative path to site/ ("" or "../").

Usage: python3 tools/build_site_pages.py
"""

from __future__ import annotations

from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
BODIES = Path(__file__).resolve().parent / "site_pages"
ORIGIN = "https://veluneos.ai"
COMPARE_URL = "https://compare.veluneos.ai/compare"

# Official horizontal lockup (Final Magenta V + outlined VeluneOS wordmark), 20px high.
LOCKUP = "assets/brand/veluneos-lockup-horizontal.svg"
FAVICON = "assets/brand/veluneos-favicon.svg"


def brand(root: str) -> str:
    return f'<img class="lockup" src="{root}{LOCKUP}" alt="VeluneOS" width="130" height="20" />'

# (output path in site/, body file, title, description, canonical path, nav key)
PAGES = [
    ("index.html", "home", "VeluneOS — See what changed between robot runs",
     "Structural comparison for robotics. Compare a Reference and a Target recording "
     "and see which streams appeared, disappeared, went quiet or changed timing. "
     "Raw MCAP stays on your machine.", "/", "home"),
    ("comparison-beta.html", "compare", "VeluneOS Compare — Compare two robot runs",
     "Prepare two MCAP recordings locally with Velune Adapter, upload one derived file, "
     "and get an evidence report of the structural differences.", "/comparison-beta", "compare"),
    ("trace.html", "trace", "Velune Trace — Find irregular timing in ROS 2 MCAP logs",
     "Open-source, local CLI for ROS 2 MCAP recordings. Ranks the time windows with "
     "the most irregular message timing. Raw logs stay on your machine.", "/trace", "trace"),
    ("sample-comparison.html", "sample", "Sample report — VeluneOS Compare",
     "Four designed changes in, one unedited VeluneOS Compare report out.",
     "/sample-comparison", "sample"),
    ("docs/index.html", "docs-index", "Docs — VeluneOS",
     "Get started with Velune Trace, Velune Adapter and VeluneOS Compare.", "/docs/", "docs"),
    ("docs/trace.html", "docs-trace", "Install and run Velune Trace on a ROS 2 MCAP log — Docs — VeluneOS",
     "Install Velune Trace, run it locally on one ROS 2 MCAP log and read the ranked "
     "evidence windows of irregular message timing.", "/docs/trace", "docs"),
    ("docs/adapter.html", "docs-adapter", "Prepare two runs with Velune Adapter — Docs — VeluneOS",
     "Install the Beta Kit, discover streams, configure mapping, confirm pairings and "
     "generate comparison.velune.", "/docs/adapter", "docs"),
    ("docs/compare.html", "docs-compare", "Upload and read the report — Docs — VeluneOS",
     "Upload comparison.velune to VeluneOS Compare and read the evidence report.",
     "/docs/compare", "docs"),
    ("docs/data-boundaries.html", "docs-boundaries", "Data boundaries — Docs — VeluneOS",
     "What stays on your machine, what is uploaded, and what VeluneOS never decides.",
     "/docs/data-boundaries", "docs"),
    ("docs/reference.html", "docs-reference", "Formats, limitations and troubleshooting — Docs — VeluneOS",
     "Supported formats, current limitations and troubleshooting for the Beta Kit and Compare.",
     "/docs/reference", "docs"),
]

DOCS_NAV = [
    ("Start", [("index.html", "Getting started")]),
    ("Velune Trace", [("trace.html", "Install and run Trace")]),
    ("Compare workflow", [
        ("adapter.html", "Prepare two runs"),
        ("compare.html", "Upload and read the report"),
    ]),
    ("Reference", [
        ("data-boundaries.html", "Data boundaries"),
        ("reference.html", "Formats, limits, troubleshooting"),
    ]),
]


def nav(root: str, current: str) -> str:
    def item(key: str, href: str, label: str) -> str:
        cur = ' aria-current="page"' if key == current else ""
        return f'<li><a href="{root}{href}"{cur}>{label}</a></li>'

    links = "".join([
        item("compare", "comparison-beta.html", "Compare"),
        item("trace", "trace.html", "Trace"),
        item("docs", "docs/index.html", "Docs"),
        item("sample", "sample-comparison.html", "Sample report"),
    ]) + '<li><a href="https://github.com/veluneos/velune-trace">GitHub</a></li>'
    return f"""<a class="skip" href="#main">Skip to content</a>
<header class="nav">
  <div class="wrap">
    <a class="brand" href="{root}index.html" aria-label="VeluneOS home">{brand(root)}</a>
    <ul class="nav-links">{links}</ul>
    <div class="nav-right">
      <a class="req" href="{COMPARE_URL}">Sign in <span aria-hidden="true">↗</span></a>
      <a class="btn btn-dark btn-sm" href="{root}comparison-beta.html#request">Request <span class="nav-long">Beta </span>Access</a>
      <details class="menu">
        <summary>Menu</summary>
        <nav class="menu-panel" aria-label="Menu">
          <a href="{root}comparison-beta.html">Compare</a>
          <a href="{root}trace.html">Trace</a>
          <a href="{root}docs/index.html">Docs</a>
          <a href="{root}sample-comparison.html">Sample report</a>
          <a href="https://github.com/veluneos/velune-trace">GitHub</a>
          <a href="{root}downloads/velune-adapter-beta-kit.zip">Adapter Kit (.zip)</a>
          <a href="{root}comparison-beta.html#request">Request Beta Access</a>
          <a href="{COMPARE_URL}">Sign in to Compare <span aria-hidden="true">↗</span></a>
        </nav>
      </details>
    </div>
  </div>
</header>"""


def footer(root: str) -> str:
    return f"""<footer class="footer">
  <div class="wrap">
    <a class="brand" href="{root}index.html">{brand(root)}</a>
    <span>Find the events. Engineers find the cause.</span>
    <nav aria-label="Footer">
      <a href="{root}comparison-beta.html">Compare</a>
      <a href="{root}trace.html">Trace</a>
      <a href="{root}docs/index.html">Docs</a>
      <a href="{root}sample-comparison.html">Sample report</a>
      <a href="https://github.com/veluneos/velune-trace">GitHub</a>
      <a href="mailto:contact@veluneos.ai">contact@veluneos.ai</a>
    </nav>
  </div>
</footer>"""


def docs_nav(current_file: str) -> str:
    links = []
    current_label = "Docs"
    for group, items in DOCS_NAV:
        links.append(f"<p>{group}</p>")
        for href, label in items:
            cur = ' aria-current="page"' if href == current_file else ""
            if cur:
                current_label = label
            links.append(f'<a href="{href}"{cur}>{label}</a>')
    inner = "".join(links)
    return (f'<details class="docs-toc"><summary><span class="eyebrow">Docs</span> {current_label}</summary>'
            f'<nav aria-label="Docs (menu)">{inner}</nav></details>'
            f'<nav class="docs-nav" aria-label="Docs">{inner}</nav>')


def sample_report() -> tuple[str, str]:
    """The service's sample report, embedded without an iframe.

    Returns (body_html, scoped_css). The report text and markup are copied from
    site/samples/compare-sample-report.html (unedited service output); only the
    heading levels are shifted down by one so the page keeps a single <h1>,
    its <main> becomes <div class="svc-main"> (one main landmark per page),
    scrollable tables get tabindex=0 for keyboard access, and
    the report's stylesheet is scoped to .svc-report (light theme only).
    """
    import re

    raw = (SITE / "samples" / "compare-sample-report.html").read_text(encoding="utf-8")
    body = re.search(r"<body[^>]*>(.*)</body>", raw, re.S).group(1).strip()
    # one <main> per page: the report's own <main> becomes a div
    body = re.sub(r"<main(\b[^>]*)>", r'<div class="svc-main"\1>', body).replace("</main>", "</div>")
    # scrollable tables must be keyboard reachable on this page
    body = body.replace('<div class="table-wrap">', '<div class="table-wrap" tabindex="0">')
    for n in (5, 4, 3, 2, 1):
        body = re.sub(rf"<(/?)h{n}(\b[^>]*)>", rf"<\1h{n + 1}\2>", body)
    css = re.search(r"<style>(.*?)</style>", raw, re.S).group(1)
    css = re.sub(r':root\[data-theme="dark"\]\s*\{[^{}]*\}', "", css)

    def scope_rules(block: str) -> list[str]:
        rules = []
        for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            scoped = []
            for part in sel.split(","):
                part = part.strip()
                if not part:
                    continue
                if part in (":root", "body", ':root:not([data-theme="light"])'):
                    scoped.append(".svc-report")
                else:
                    part = re.sub(r"\bh([1-5])\b", lambda m: f"h{int(m.group(1)) + 1}", part)
                    part = re.sub(r"^main\b", ".svc-main", part)
                    scoped.append(f".svc-report {part}")
            if scoped:
                rules.append(f"{', '.join(scoped)} {{{decl.strip()}}}")
        return rules

    out = []
    pos = 0
    for m in re.finditer(r"@media([^{]+)\{((?:[^{}]*\{[^{}]*\})*)\s*\}", css):
        out += scope_rules(css[pos:m.start()])
        query = m.group(1).strip()
        if "prefers-color-scheme" not in query:  # the site is light-only
            out.append(f"@media {query} {{\n  " + "\n  ".join(scope_rules(m.group(2))) + "\n}")
        pos = m.end()
    out += scope_rules(css[pos:])
    header = "/* Scoped copy of the stylesheet in samples/compare-sample-report.html (generated by tools/build_site_pages.py). */\n"
    return body, header + "\n".join(out) + "\n"


def page(out: str, body_name: str, title: str, desc: str, canonical: str, current: str) -> str:
    root = "../" if "/" in out else ""
    raw_body = (BODIES / f"{body_name}.html").read_text(encoding="utf-8")
    body = raw_body.replace("{root}", root)
    if out.startswith("docs/"):
        body = body.replace("{docs_nav}", docs_nav(out.split("/", 1)[1]))
    if "{sample_report}" in body:
        body = body.replace("{sample_report}", sample_report()[0])
    # Scrollable regions must be reachable by keyboard.
    body = (body.replace("<pre>", '<pre tabindex="0">')
                .replace('<div class="term">', '<div class="term" tabindex="0">')
                .replace('<div class="tablebox">', '<div class="tablebox" tabindex="0">'))
    url = ORIGIN + canonical
    extra_css = f'\n  <link rel="stylesheet" href="{root}assets/sample-report.css" />' if "{sample_report}" in raw_body else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc)}" />
  <link rel="canonical" href="{url}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="VeluneOS" />
  <meta property="og:title" content="{escape(title)}" />
  <meta property="og:description" content="{escape(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta name="theme-color" content="#ffffff" />
  <link rel="icon" href="{root}{FAVICON}" type="image/svg+xml" />
  <link rel="stylesheet" href="{root}assets/site.css" />{extra_css}
</head>
<body>
{nav(root, current)}
<main id="main">
{body}
</main>
{footer(root)}
</body>
</html>
"""


# Former English URLs. Cloudflare Pages applies site/_redirects (301); the stub
# pages keep each old address working even where the redirect rule is not applied.
MOVED = [
    ("en.html", "/en", "index.html", "/"),
    ("comparison-beta-en.html", "/comparison-beta-en", "comparison-beta.html", "/comparison-beta"),
    ("trace-en.html", "/trace-en", "trace.html", "/trace"),
]


def stub(target_file: str, target_path: str) -> str:
    url = ORIGIN + target_path
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Moved — VeluneOS</title>
  <meta name="robots" content="noindex" />
  <link rel="canonical" href="{url}" />
  <meta http-equiv="refresh" content="0; url={target_file}" />
  <link rel="stylesheet" href="assets/site.css" />
</head>
<body>
<main id="main" class="page-hero"><div class="wrap">
  <h1>This page has moved.</h1>
  <p class="lead">Continue to <a class="text-link" href="{target_file}">{url}</a>.</p>
</div></main>
</body>
</html>
"""


NOT_FOUND = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Page not found — VeluneOS</title>
  <meta name="robots" content="noindex" />
  <link rel="icon" href="/assets/brand/veluneos-favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="/assets/site.css" />
</head>
<body>
<main id="main" class="page-hero"><div class="wrap">
  <p class="eyebrow">404</p>
  <h1 style="margin-top:14px">No events here.</h1>
  <p class="lead">This page does not exist.</p>
  <div class="cta-row">
    <a class="btn btn-dark" href="/">VeluneOS home</a>
    <a class="btn btn-line" href="/docs/">Docs</a>
  </div>
</div></main>
</body>
</html>
"""


def sitemap() -> str:
    urls = "".join(
        f"  <url><loc>{ORIGIN}{canonical}</loc></url>\n"
        for _out, _body, _t, _d, canonical, _c in PAGES
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def redirects() -> str:
    lines = ["# Former English URLs (the site is English-only). Stub pages remain as a fallback."]
    for _stub, old, _target_file, new in MOVED:
        lines.append(f"{old} {new} 301")
        lines.append(f"{old}.html {new} 301")
    return "\n".join(lines) + "\n"


def main() -> int:
    for out, body_name, title, desc, canonical, current in PAGES:
        path = SITE / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page(out, body_name, title, desc, canonical, current), encoding="utf-8")
        print(f"wrote site/{out}")
    for stub_file, _old, target_file, new in MOVED:
        (SITE / stub_file).write_text(stub(target_file, new), encoding="utf-8")
        print(f"wrote site/{stub_file} (moved stub)")
    (SITE / "404.html").write_text(NOT_FOUND, encoding="utf-8")
    (SITE / "assets" / "sample-report.css").write_text(sample_report()[1], encoding="utf-8")
    (SITE / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    (SITE / "_redirects").write_text(redirects(), encoding="utf-8")
    print("wrote site/404.html, site/sitemap.xml, site/_redirects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
