// The Piclines Editor's browser test: the hand-over opens a drawing, an expired link says
// so, and the page asks nobody but its own server and Piclines for anything.
//
//   python3 piclines/build.py --piclines http://127.0.0.1:8042
//   node piclines/test/open.mjs [OUTDIR]
//
// Serves piclines/dist on 127.0.0.1:8041 and a stand-in for Piclines on :8042 (another
// origin, as edit.piclines.com and piclines.com are), then drives headless Chrome over
// its DevTools protocol — nothing to install. CHROME names the browser if it is not in
// the usual place. Screenshots go to OUTDIR (default piclines/test/out).
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "dist");
const out = process.argv[2] ?? join(here, "out");
const EDITOR = "http://127.0.0.1:8041";
const PICLINES = "http://127.0.0.1:8042";
const TOKEN = "a-good-token-of-the-right-length";
const drawing = readFileSync(join(here, "pattern-sewing.dwg"));
mkdirSync(out, { recursive: true });

const types = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".webmanifest": "application/manifest+json",
  ".wasm": "application/wasm", ".svg": "image/svg+xml", ".ttf": "font/ttf", ".txt": "text/plain",
};
const missing = [];
const editor = createServer((req, res) => {
  let path = normalize(join(dist, decodeURIComponent(new URL(req.url, EDITOR).pathname)));
  if (path.startsWith(dist) && existsSync(path) && statSync(path).isDirectory()) path = join(path, "index.html");
  if (!path.startsWith(dist) || !existsSync(path)) {
    missing.push(req.url);
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, { "Content-Type": types[extname(path)] ?? "application/octet-stream" });
  res.end(readFileSync(path));
}).listen(8041, "127.0.0.1");
const fetched = [];
const piclines = createServer((req, res) => {
  fetched.push(req.url);
  const cors = { "Access-Control-Allow-Origin": EDITOR, "Cache-Control": "no-store" };
  if (req.url === `/api/editor/${TOKEN}`) res.writeHead(200, { ...cors, "Content-Type": "application/acad" }).end(drawing);
  else res.writeHead(404, cors).end();
}).listen(8042, "127.0.0.1");

const chrome = process.env.CHROME ?? [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].find(existsSync);
const browser = spawn(chrome, [
  "--headless=new", "--remote-debugging-port=9335", `--user-data-dir=${mkdtempSync(join(tmpdir(), "pe-chrome-"))}`,
  "--no-first-run", "--window-size=1440,900", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const failures = [];
const check = (ok, what) => { console.log(`${ok ? "ok  " : "FAIL"} ${what}`); if (!ok) failures.push(what); };
const done = (code) => { browser.kill(); editor.close(); piclines.close(); process.exit(code); };
setTimeout(() => { console.log("FAIL timed out"); done(1); }, 300000).unref();

let target;
for (let i = 0; i < 100 && !target; i++) {
  try { target = (await (await fetch("http://127.0.0.1:9335/json")).json()).find((t) => t.type === "page"); }
  catch { await sleep(200); }
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let next = 1;
const waiting = new Map();
const problems = [];
const outside = new Set();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id) { waiting.get(m.id)?.(m); waiting.delete(m.id); return; }
  const p = m.params;
  if (m.method === "Network.requestWillBeSent") {
    const url = p.request.url;
    if (!/^(data|blob|about|chrome-extension):/.test(url) && !url.startsWith(EDITOR) && !url.startsWith(PICLINES)) outside.add(url);
  }
  if (m.method === "Runtime.exceptionThrown") problems.push("exception: " + (p.exceptionDetails.exception?.description ?? p.exceptionDetails.text));
  if (m.method === "Runtime.consoleAPICalled" && p.type === "error") problems.push("console: " + p.args.map((a) => a.value ?? a.description).join(" "));
  // upstream's own notes: its old-style wasm-bindgen call, and which GPU it found
  if (m.method === "Log.entryAdded" && !/deprecated parameters for the initialization|integrity` attribute is currently ignored/.test(p.entry.text))
    problems.push("log: " + p.entry.text);
});
const send = (method, params = {}) => new Promise((r) => { const id = next++; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text);
  return r.result.result.value;
};
const until = async (expression, ms) => {
  for (const end = Date.now() + ms; Date.now() < end; await sleep(250)) if (await evaluate(expression)) return true;
  return false;
};
const shot = async (name) => writeFileSync(join(out, name), Buffer.from((await send("Page.captureScreenshot")).result.data, "base64"));
for (const domain of ["Page", "Runtime", "Log", "Network"]) await send(`${domain}.enable`);
const state = `window.ocsControl.request({op: "state"}, {timeoutMs: 20000})`;

// 1. A good link opens the drawing, and the token leaves the address bar.
await send("Page.navigate", { url: `${EDITOR}/app/#piclines=${TOKEN}&name=pattern-sewing.dwg` });
const opened = await until(`(async () => {
  if (!window.ocsControl) return false;
  await window.ocsControl.ready;
  return (await ${state}).documents?.some((d) => d.path === "pattern-sewing.dwg");
})()`, 120000);
check(opened, "a good link opens the drawing as a tab");
check(await evaluate(`document.querySelector("canvas")?.clientWidth >= innerWidth - 1`), "the app fills the window");
check((await evaluate("location.hash")) === "", "the token is gone from the address bar");
check(await until(`!document.getElementById("piclines-note")`, 5000), "the note goes once it is open");
check(fetched.includes(`/api/editor/${TOKEN}`), "the drawing came from Piclines");
check(await evaluate(`document.title === "Piclines Editor"`), "the tab is called Piclines Editor");
await sleep(1500);
await shot("1-opened.png");

// 2. An expired link says so — here in the tab already open, where only the hash changes.
await evaluate(`location.hash = "piclines=an-expired-token-0000000&name=old.dwg"`);
check(await until(`document.querySelector("#piclines-note.error")?.textContent.includes("expired")`, 60000), "an expired link says so");
await shot("2-expired.png");

// 3. The page asked nobody else for anything, and nothing went wrong on the way.
const unexpected = problems.filter((p) => !/Failed to load resource: .* 404/.test(p)); // the expired link's own 404
check(outside.size === 0, `nothing asked of other servers${outside.size ? ": " + [...outside].join(", ") : ""}`);
check(missing.length === 0, `no file missing${missing.length ? ": " + missing.join(", ") : ""}`);
check(unexpected.length === 0, `no errors${unexpected.length ? ":\n  " + unexpected.join("\n  ") : ""}`);
console.log(failures.length ? `${failures.length} failed` : "all passed");
done(failures.length ? 1 : 0);
