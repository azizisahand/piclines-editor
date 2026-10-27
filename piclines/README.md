# Piclines Editor, based on Open CAD Studio

The Piclines Editor is [Open CAD Studio](https://github.com/HakanSeven12/OpenCADStudio)'s
web app, by Hakan Seven and its contributors, with a small page of our own around it. It
lets a user of [Piclines](https://piclines.com) — a web tool that turns pictures into lines
in DXF and DWG files — open the drawing they just made, change it and save it. It runs at
`edit.piclines.com` as static files, separate from Piclines: the two only pass a drawing
from one to the other.

All the CAD work is Open CAD Studio's. Thank you, Hakan. If the editor is useful to you,
please [support Open CAD Studio on Patreon](https://patreon.com/HakanSeven12).

## Licence and source

Open CAD Studio is free software under the **GNU General Public License v3.0**, and so is
this editor: see [`LICENSE`](../LICENSE). You may use, study, share and change it under
its terms.

The editor that runs at `edit.piclines.com` is built from:

1. **Open CAD Studio's released web app, unchanged** — version and checksum in
   [`upstream.json`](upstream.json). Its source is upstream's tag of that version
   (v2026.43: commit `dbd50b2`), which is also in this repository.
2. **The files in this folder**, which change only the page around the app.

Each release of this fork names both.

The name "Piclines" and its logo (`brand/`) belong to Zehando and are not licensed under
the GPL: a fork of this repository must use its own name and icon.

## What is changed

Nothing inside Open CAD Studio. `build.py` takes upstream's release, checks it, and:

- names the page "Piclines Editor" and shows "based on Open CAD Studio" while it loads,
  with Piclines' colours and icon;
- adds a link in the top right corner to this page: licence, source and credits;
- adds [`page/piclines.js`](page/piclines.js), the hand-over: Piclines opens
  `/app/#piclines=TOKEN&name=FILE`, and the script fetches that drawing from Piclines and
  opens it through Open CAD Studio's own control channel
  ([`docs/automation/web.md`](../docs/automation/web.md)). The token leaves the address
  bar at once and works for a few minutes only;
- adds a Content-Security-Policy that lets the page talk only to its own server and to
  Piclines, and empties the welcome screen's video list (its thumbnails come from YouTube),
  so the editor asks no other server for anything;
- takes Open CAD Studio's supporters list from its site at build time, so it still shows.

Open CAD Studio's start page, About, donation prompt and everything else stay as they are.

## What it keeps in your browser

Settings, the names of open and recent files, and the app's own files (for working
offline) — in your browser only. Drawings are not stored; nothing is sent anywhere but to
download your drawing from Piclines.

## Build and test

Python 3.10+ and Node 22+; no Rust needed.

```sh
python piclines/build.py                                   # → piclines/dist/, for piclines.com
python piclines/build.py --piclines http://127.0.0.1:8042  # for the test
node piclines/test/open.mjs                                # headless Chrome; screenshots in piclines/test/out/
```

`build.py` downloads upstream's release once into `piclines/.cache/` and refuses it if
the checksum differs. Serve `piclines/dist/` as static files, `/` redirecting to `/app/`.

## Updating Open CAD Studio

1. Merge upstream's tag into `main` (`git fetch upstream --tags && git merge vYYYY.NN`).
2. Put its web zip's URL, SHA-256 (GitHub shows it as the asset's digest) and commit into
   `upstream.json`.
3. Build and run the test. If `build.py` stops because a patch no longer fits, upstream
   changed its page: adjust the patch.
4. Tag `piclines-vYYYY.NN-1`: the workflow builds the release package.
