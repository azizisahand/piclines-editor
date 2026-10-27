# Piclines Editor

The editor of [Piclines](https://piclines.com), a web tool that turns pictures into lines in
DXF and DWG files: a user opens the drawing they just made, changes it and saves it. It
runs at `edit.piclines.com` as static files, separate from Piclines; the two only pass a
drawing from one to the other.

## Licence and source

Free software under the **GNU General Public License v3.0** ([`LICENSE`](../LICENSE)). It
is a modified version of Open CAD Studio, changed by Zehando since 27 October 2026; every
change is in this repository's history, and in the Rust code each is marked
`// Piclines:`. The source of every build is this repository at the tag the build names.

The name "Piclines" and its logo (`brand/`, `assets/logo.svg`) belong to Zehando and are
not licensed under the GPL: a fork of this repository must use its own name and icon.

## What is ours

- **Rust** — `src/piclines.rs` (name, addresses, the link filter, our texts) and
  `src/app/view/piclines.rs` (start page, About, the plugin notice, help and feedback).
  Upstream's files only call in, at lines marked `// Piclines:`:
  `src/lib.rs`, `src/sys.rs` (every link the web build opens goes through
  `piclines::link`), `src/app/view/mod.rs` (the start page), `src/app/view/modal.rs`
  (About, plugins), `src/app/commands/view.rs` (help, feedback, donations, release
  notes), `src/app/startup.rs` (no donation prompt on the web), `src/ui/window/about.rs`
  (the copied info's name), `src/app/config.rs` (our colours as the default theme).
  `assets/logo.svg` is our icon.
- **Strings** — `build.py` puts our name into every language's strings for the build
  only, and stops when one still names the original; the locale files themselves stay as
  upstream has them.
- **The page** (`page/`, applied by `build.py`) — the name, loading screen and icon; the
  hand-over: Piclines opens `/app/#piclines=TOKEN&name=FILE`, and `piclines.js` fetches
  that drawing from Piclines and opens it through the app's control channel
  ([`docs/automation/web.md`](../docs/automation/web.md)); a Content-Security-Policy that
  lets the page talk only to its own server and to Piclines; the start page's upstream
  data files emptied.

## Build and test

In Linux (on Windows: WSL): Rust with the `wasm32-unknown-unknown` target, Trunk, and
wasm-bindgen-cli at the version in `Cargo.lock`; Python 3.10+ and Node 22+.

```sh
python3 piclines/build.py                                   # → piclines/dist/, for piclines.com
python3 piclines/build.py --piclines http://127.0.0.1:8042  # for the test
node piclines/test/open.mjs                                 # headless Chrome; screenshots in piclines/test/out/
cargo test --lib piclines                                   # the link filter
```

Serve `piclines/dist/` as static files, `/` redirecting to `/app/`.

## Taking in a new upstream release

1. `git fetch upstream --tags && git merge vYYYY.NN` — conflicts only where upstream
   changed a line marked `// Piclines:`; keep ours, take the rest of theirs.
2. Build and test. If `build.py` stops, either a patch to the page no longer fits or a new
   string names the original: adjust `build.py`.
3. Look at the start page, About and the menus in English and German.
4. Tag `piclines-vYYYY.NN-1`: the workflow builds the release package.
