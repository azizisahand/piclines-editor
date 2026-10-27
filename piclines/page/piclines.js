// Piclines Editor: the hand-over from Piclines.
//
// Piclines opens this page as  /app/#piclines=TOKEN&name=FILE.dwg  after a download was
// paid for. The token is taken out of the address bar at once; the drawing is fetched
// from the Piclines site named in <meta name="piclines-origin"> and opened through the
// app's control channel (docs/automation/web.md).
(() => {
  const origin = document.querySelector('meta[name="piclines-origin"]')?.content;
  const german = (navigator.language || "").toLowerCase().startsWith("de");
  const text = german
    ? {
        opening: (name) => `${name} wird geöffnet …`,
        expired: "Dieser Link ist abgelaufen. Gehen Sie zurück zu Piclines und klicken Sie noch einmal auf „Im Editor öffnen“.",
        failed: "Die Zeichnung ließ sich nicht öffnen. Versuchen Sie es auf Piclines noch einmal, oder laden Sie sie dort herunter.",
        close: "Schließen",
      }
    : {
        opening: (name) => `Opening ${name} …`,
        expired: "This link has expired. Go back to Piclines and click “Open in editor” again.",
        failed: "The drawing could not be opened. Try again on Piclines, or download it there.",
        close: "Close",
      };

  const base64 = (bytes) => {
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  };
  let sent = 0;
  const control = (request) =>
    window.ocsControl.request({ protocol: 1, request_id: `piclines-${Date.now()}-${++sent}`, ...request }, { timeoutMs: 60000 });
  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // On load, and again when a link changes only the part after "#" of a tab already open.
  const handOver = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const token = params.get("piclines");
    if (token === null) return;
    history.replaceState(null, "", location.pathname + location.search);
    const name = (params.get("name") || "drawing.dwg").split(/[\\/]/).pop().slice(0, 200);

    document.getElementById("piclines-note")?.remove();
    const note = document.createElement("div");
    note.id = "piclines-note";
    note.setAttribute("role", "status");
    const message = document.createElement("span");
    note.append(message);
    document.body.append(note);
    const say = (words, error = false) => {
      message.textContent = words;
      note.classList.toggle("error", error);
      if (error && !note.querySelector("button")) {
        const close = document.createElement("button");
        close.type = "button";
        close.textContent = text.close;
        close.addEventListener("click", () => note.remove());
        note.append(close);
      }
    };
    say(text.opening(name));
    openDrawing(token, name, say, note).catch((error) => {
      console.error("Piclines Editor:", error);
      say(text.failed, true);
    });
  };

  const openDrawing = async (token, name, say, note) => {
    if (!origin || !/^[A-Za-z0-9_-]{16,128}$/.test(token)) return say(text.expired, true);
    const response = await fetch(`${origin}/api/editor/${token}`, {
      credentials: "omit",
      cache: "no-store",
      referrerPolicy: "no-referrer",
    });
    if (response.status === 404 || response.status === 410) return say(text.expired, true);
    if (!response.ok) throw new Error(`Piclines answered ${response.status}`);
    const data = base64(new Uint8Array(await response.arrayBuffer()));
    await window.ocsControl.ready;
    // "busy" while an earlier drawing (a restored session) is still opening
    for (let tries = 0; tries < 40; tries++) {
      const reply = await control({ op: "open", name, data_base64: data });
      if (reply.ok) return note.remove();
      if (reply.code !== "busy") throw new Error(`open: ${reply.code} ${reply.error ?? ""}`);
      await pause(500);
    }
    throw new Error("open: still busy");
  };

  handOver();
  addEventListener("hashchange", handOver);
})();
