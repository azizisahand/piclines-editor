"""Build the Piclines Editor from Open CAD Studio's released web app.

Upstream's release, pinned in upstream.json and checked by its SHA-256, is unpacked
unchanged; only the page around the WebAssembly is changed: the name, the loading
screen, the icon, our hand-over script (page/piclines.js) and a Content-Security-Policy.
No Rust is built. See README.md.

    python piclines/build.py [--zip FILE] [--piclines ORIGIN] [--out DIR] [--package NAME]

Python's standard library only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / "upstream.json").read_text(encoding="utf-8"))
NAME = "Piclines Editor"
BG = "#0b0d10"
ACCENT = "#6f9bff"
SUPPORTERS = "https://www.opencadstudio.com/app/supporters.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def upstream_zip(given: Path | None) -> Path:
    """The pinned release: the file given, or downloaded once into piclines/.cache."""
    path = given or HERE / ".cache" / PIN["url"].rsplit("/", 1)[1]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {PIN['url']}")
        part = path.with_suffix(".part")
        with urllib.request.urlopen(PIN["url"], timeout=120) as r, part.open("wb") as f:
            shutil.copyfileobj(r, f)
        part.replace(path)
    got = sha256(path)
    if got != PIN["sha256"]:
        sys.exit(f"{path}: SHA-256 {got}, expected {PIN['sha256']} (upstream.json)")
    return path


def replace_once(text: str, old: str, new: str, where: str) -> str:
    """Upstream's page changes now and then: a patch that no longer fits fails the build."""
    count = text.count(old)
    if count != 1:
        sys.exit(f"{where}: expected {old!r} once, found it {count} times")
    return text.replace(old, new)


def inline_hashes(html: str, tag: str) -> list[str]:
    """CSP hashes of the page's inline <script> blocks."""
    hashes, start = [], 0
    while (i := html.find(f"<{tag}", start)) != -1:
        open_end = html.index(">", i) + 1
        close = html.index(f"</{tag}>", open_end)
        if "src=" not in html[i:open_end]:
            digest = hashlib.sha256(html[open_end:close].encode()).digest()
            hashes.append("'sha256-" + base64.b64encode(digest).decode() + "'")
        start = close
    return hashes


def patch_page(app: Path, origin: str) -> None:
    page = app / "index.html"
    html = page.read_text(encoding="utf-8")
    where = "app/index.html"
    html = replace_once(html, "<title>Open CAD Studio Web App</title>", f"<title>{NAME}</title>", where)
    html = replace_once(html, '<meta name="theme-color" content="#1e1e1e" />', f'<meta name="theme-color" content="{BG}" />', where)
    html = replace_once(html, "background: #1e1e1e;\n        color: #cfcfcf;", f"background: {BG};\n        color: #e8eaed;", where)
    html = replace_once(html, "#loading .title span { color: #3399e6; }", f"#loading .title span {{ color: {ACCENT}; }}", where)
    html = replace_once(html, "border-top-color: #3399e6;", f"border-top-color: {ACCENT};", where)
    html = replace_once(
        html,
        '<div class="title">Open <span>CAD</span> Studio</div>',
        '<div class="title">Piclines <span>Editor</span></div>\n'
        '      <div class="sub">based on Open CAD Studio</div>',
        where,
    )
    # upstream's site puts its own icons at the root; ours is one SVG
    start = html.find('<link rel="icon" href="/favicon.ico"')
    end = html.find(">", html.find('<link rel="apple-touch-icon"')) + 1
    if start == -1 or end == 0:
        sys.exit(f"{where}: the icon links have changed")
    html = html[:start] + '<link rel="icon" href="/favicon.svg" type="image/svg+xml" />' + html[end:]
    html = replace_once(
        html,
        '<script src="ocs-control.js" defer></script>',
        '<script src="ocs-control.js" defer></script>\n    <script src="piclines.js" defer></script>',
        where,
    )
    head = (
        f'<meta name="piclines-origin" content="{origin}" />\n'
        '    <link rel="stylesheet" href="piclines.css" />\n  </head>'
    )
    html = replace_once(html, "</head>", head, where)
    # Only our own server and Piclines: the page asks no one else for anything (no
    # thumbnails, nothing that phones home). Inline scripts by their hashes, the
    # WebAssembly by 'wasm-unsafe-eval'. Styles inline too: the app sizes its canvas
    # with a style attribute, and blocked it stays 300 x 150 px.
    csp = "; ".join(
        [
            "default-src 'self'",
            "script-src 'self' 'wasm-unsafe-eval' " + " ".join(inline_hashes(html, "script")),
            "style-src 'self' 'unsafe-inline'",
            f"connect-src 'self' {origin}",
            "img-src 'self' data: blob:",
            "font-src 'self' data: blob:",
            "worker-src 'self' blob:",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'none'",
        ]
    )
    html = replace_once(html, '<meta charset="utf-8" />', f'<meta charset="utf-8" />\n    <meta http-equiv="Content-Security-Policy" content="{csp}" />', where)
    page.write_text(html, encoding="utf-8", newline="\n")


def patch_data(app: Path) -> None:
    labels_path = app / "locale-labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    for label in labels.values():
        label["title"] = NAME
    labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = app / "app.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        name=NAME,
        short_name=NAME,
        description=f"{NAME}, based on Open CAD Studio: edit DWG and DXF drawings.",
        background_color=BG,
        theme_color=BG,
        icons=[{"src": "piclines-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # The welcome screen's videos load their thumbnails from YouTube: none here.
    (app / "videos.json").write_text("[]\n", encoding="utf-8")
    # Upstream's site makes the supporters list from Patreon when it deploys; we take
    # theirs at build time, so the author's supporters still show. No list, no panel rows.
    supporters: list[dict[str, object]] = []
    try:
        with urllib.request.urlopen(SUPPORTERS, timeout=15) as r:
            got = json.loads(r.read())
        if isinstance(got, list) and all(
            isinstance(s, dict) and isinstance(s.get("name"), str) and isinstance(s.get("cents"), int) for s in got
        ):
            supporters = [{"name": s["name"], "cents": s["cents"]} for s in got]
    except (OSError, ValueError) as e:
        print(f"supporters: none ({e})")
    (app / "supporters.json").write_text(json.dumps(supporters, ensure_ascii=False) + "\n", encoding="utf-8")


def stamp_service_worker(app: Path) -> None:
    """A new cache name for every build, as upstream's deploy does, so old files go."""
    h = hashlib.sha256()
    for path in sorted(p for p in app.rglob("*") if p.is_file() and p.name != "sw.js"):
        h.update(path.relative_to(app).as_posix().encode())
        h.update(sha256(path).encode())
    sw = app / "sw.js"
    text = sw.read_text(encoding="utf-8")
    old = text[text.index('const CACHE_VERSION = "') : text.index(";", text.index('const CACHE_VERSION = "'))]
    sw.write_text(text.replace(old, f'const CACHE_VERSION = "pl-{h.hexdigest()[:12]}"'), encoding="utf-8", newline="\n")


def build(zip_path: Path, out: Path, origin: str) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)
    app = out / "app"
    for leftover in (app / ".trunk-lock", app / "fonts" / "generate.sh"):
        leftover.unlink(missing_ok=True)
    for f in (HERE / "page").iterdir():
        shutil.copy2(f, app / f.name)
    shutil.copy2(HERE / "brand" / "favicon.svg", out / "favicon.svg")
    shutil.copy2(HERE / "brand" / "piclines-icon.svg", app / "piclines-icon.svg")
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=/app/">'
        f'<title>{NAME}</title><a href="/app/">{NAME}</a>\n',
        encoding="utf-8",
    )
    patch_page(app, origin)
    patch_data(app)
    stamp_service_worker(app)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--zip", type=Path, help="upstream's web zip, instead of downloading it")
    p.add_argument("--piclines", default="https://piclines.com", help="the Piclines site the drawings come from")
    p.add_argument("--out", type=Path, default=HERE / "dist")
    p.add_argument("--package", metavar="NAME", help="also write NAME.zip next to --out, and print its SHA-256")
    a = p.parse_args()
    origin = a.piclines.rstrip("/")
    build(upstream_zip(a.zip), a.out, origin)
    print(f"built {a.out} from Open CAD Studio v{PIN['version']}, drawings from {origin}")
    if a.package:
        package = a.out.parent / f"{a.package}.zip"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(a.out.rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(a.out).as_posix())
        print(f"{package}  sha256 {sha256(package)}")


if __name__ == "__main__":
    main()
