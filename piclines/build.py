"""Build the Piclines Editor from this repository's source.

    python3 piclines/build.py [--piclines ORIGIN] [--out DIR] [--package NAME]

Three steps, so upstream's own files stay as they are in git and its new releases merge
cleanly (README.md):

1. the app's name in every language's strings (`locales/*/opencadstudio.ftl`) becomes
   ours, for the build only — the files are put back afterwards;
2. `trunk build --release` (Rust, the wasm32 target, Trunk and wasm-bindgen-cli);
3. the page around the WebAssembly: the name, loading screen and icon, our hand-over
   script (page/piclines.js), a Content-Security-Policy, and the data files of the start
   page's upstream panels emptied.

Python's standard library only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAME = "Piclines Editor"
BG = "#0b0d10"
ACCENT = "#6f9bff"

# The app's name in the strings, and what replaces it. Checked afterwards: a string
# still naming the original stops the build (a new upstream string, an inflected form).
RENAMES = [(re.compile(r"Open ?CAD ?Studio"), NAME), (re.compile(r"\bOCS\b"), NAME)]
LEFT = re.compile(r"Open\s*CAD\s*Stud|\bOCS\b", re.IGNORECASE)
# Hungarian inflects the name: each ending on "Editor", and "a" for "az" before it.
RENAMES_BY_LANGUAGE = {
    "hu-HU": [
        (re.compile(r"Open CAD Studiót"), "Piclines Editort"),
        (re.compile(r"Open CAD Studiónak"), "Piclines Editornak"),
        (re.compile(r"Open CAD Studióban"), "Piclines Editorban"),
        (re.compile(r"Open CAD Studióval"), "Piclines Editorral"),
        (re.compile(r"Open CAD Studión"), "Piclines Editoron"),
        (re.compile(r"\b([Aa])z (?=(?:Open CAD Studi|Piclines))"), r"\1 "),
    ],
}
# Strings that would send people to the original project, in our words.
OWN = {
    "window-hit-something-broken-or-missing-report-it-on-the": {
        "en-US": "Hit something broken or missing? Tell us at support@piclines.com.",
        "de-DE": "Etwas fehlt oder funktioniert nicht? Schreiben Sie uns an support@piclines.com.",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_assume_unchanged(paths: list[Path], yes: bool) -> None:
    """While the strings are renamed, git (and so build.rs's version) sees no change."""
    flag = "--assume-unchanged" if yes else "--no-assume-unchanged"
    subprocess.run(["git", "update-index", flag, *map(str, paths)], cwd=ROOT, check=True)


def rename_strings() -> dict[Path, str]:
    """Our name in every language's strings; the original texts, to put back."""
    git_assume_unchanged(sorted(ROOT.glob("locales/*/opencadstudio.ftl")), True)
    originals: dict[Path, str] = {}
    left: list[str] = []
    for ftl in sorted(ROOT.glob("locales/*/opencadstudio.ftl")):
        language = ftl.parent.name
        text = ftl.read_text(encoding="utf-8")
        originals[ftl] = text
        lines = []
        for line in text.split("\n"):
            key, sep, value = line.partition(" = ")
            if sep:
                attribute = key.strip().lstrip(".")
                if attribute in OWN:
                    value = OWN[attribute].get(language, OWN[attribute]["en-US"])
                for pattern, new in RENAMES_BY_LANGUAGE.get(language, []) + RENAMES:
                    value = pattern.sub(new, value)
                if LEFT.search(value):
                    left.append(f"{ftl.relative_to(ROOT)}: {key.strip()} = {value}")
                line = key + sep + value
            lines.append(line)
        ftl.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    if left:
        restore(originals)
        sys.exit("strings still naming the original project:\n  " + "\n  ".join(left))
    return originals


def restore(originals: dict[Path, str]) -> None:
    for path, text in originals.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    git_assume_unchanged(sorted(originals), False)


def trunk(out: Path) -> None:
    subprocess.run(
        [
            "trunk", "build", "--locked", "--release", "--public-url", "/app/",
            "--dist", str(out / "app"), "--html-output", "index.html", "web-app.html",
        ],
        cwd=ROOT,
        check=True,
    )


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
        '<div class="title">Piclines <span>Editor</span></div>',
        where,
    )
    # upstream's site puts its own icons at the root; ours is one SVG
    html = re.sub(r'<link rel="icon"[^>]*>\s*', "", html)
    html = re.sub(r'<link rel="apple-touch-icon"[^>]*>\s*', "", html)
    html = replace_once(html, "</title>", '</title>\n    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />', where)
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
    # Only our own server and Piclines: the page asks no one else for anything. Inline
    # scripts by their hashes, the WebAssembly by 'wasm-unsafe-eval'. Styles inline too:
    # the app sizes its canvas with a style attribute, and blocked it stays 300 x 150 px.
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
        description="Edit DWG and DXF drawings from Piclines.",
        background_color=BG,
        theme_color=BG,
        icons=[{"src": "piclines-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # The data of upstream's start-page panels (its discussions, videos, supporters):
    # our start page shows none of them, and the app finds them empty.
    for name in ("discussions.json", "videos.json", "supporters.json"):
        (app / name).write_text("[]\n", encoding="utf-8")


def stamp_service_worker(app: Path) -> None:
    """A new cache name for every build, so browsers drop the old files."""
    h = hashlib.sha256()
    for path in sorted(p for p in app.rglob("*") if p.is_file() and p.name != "sw.js"):
        h.update(path.relative_to(app).as_posix().encode())
        h.update(sha256(path).encode())
    sw = app / "sw.js"
    text = sw.read_text(encoding="utf-8")
    start = text.index('const CACHE_VERSION = "')
    old = text[start : text.index(";", start)]
    text = text.replace(old, f'const CACHE_VERSION = "pl-{h.hexdigest()[:12]}"')
    text = text.replace("Open CAD Studio is offline.", f"{NAME} is offline.")
    sw.write_text(text, encoding="utf-8", newline="\n")


def build(out: Path, origin: str) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    originals = rename_strings()
    try:
        trunk(out)
    finally:
        restore(originals)
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
    p.add_argument("--piclines", default="https://piclines.com", help="the Piclines site the drawings come from")
    p.add_argument("--out", type=Path, default=HERE / "dist")
    p.add_argument("--package", metavar="NAME", help="also write NAME.zip next to --out, and print its SHA-256")
    a = p.parse_args()
    origin = a.piclines.rstrip("/")
    build(a.out, origin)
    print(f"built {a.out}, drawings from {origin}")
    if a.package:
        package = a.out.parent / f"{a.package}.zip"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(a.out.rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(a.out).as_posix())
        print(f"{package}  sha256 {sha256(package)}")


if __name__ == "__main__":
    main()
