"""v21.2 tests for Minifolio: the Content Security Policy (CSP).

The CSP is a <meta> tag in index.html that tells the browser what the page may load and run.
These checks make sure it's there, has the right rules, really blocks outside code, and that
nothing the app needs got blocked by mistake.

Checks:
1. Version numbers (plain numbers), sw.js matches, the Updates entry, CNAME and the ocr folder kept,
   storage names and the data version unchanged (still 1).
2. The CSP tag: there's exactly one, it comes before every <script>, and it has each expected rule.
3. It really works: a script or picture from another website is refused (these deliberate tries
   have "csp-probe" in the address, so the suite's CSP watcher ignores them).
4. Every tab opens with no CSP errors and no page errors; screenshots of each tab.
5. Photos still show: a photo added through the real file picker (blob: address) shows on the card,
   in the unit's photo strip and in the photo viewer; an old-style photo (data: address) shows too.
6. The pot-label reader still reads a test picture (WebAssembly in a background worker).
7. Offline: after the app has loaded once, it reloads and works with the internet off.
8. Feedback link: still a plain link to the form, now with noopener noreferrer. Privacy and Help text.
9. Nothing scrolls sideways at 360 px; no page errors anywhere.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, struct, sys, zlib
from playwright.sync_api import sync_playwright
from dialog_watch import DialogAnswers

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    # v21.4: the app's code moved out of index.html into early.js and app.js, so "index.html"
    # here means the page plus those two files (the source checks look across all three).
    if name == "index.html":
        return "\n".join(open(os.path.join(ROOT, n), encoding="utf-8").read() for n in ("index.html", "early.js", "app.js"))
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

def png(width=64, height=48, rgb=(40, 90, 160)):
    """A small plain-coloured PNG picture, made here so the test needs no image files."""
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

TINY_DATA_URL = "data:image/png;base64," + __import__("base64").b64encode(png(8, 8, (200, 60, 60))).decode()

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 3]]},
    {"id": 2, "name": "Old photo unit", "hobby": "40K", "faction": "Tyranids", "stage": 1, "count": 1,
     "photo": TINY_DATA_URL, "log": [["2026-09-01", 1]]},
]
TABS = ["dashboard", "units", "recipes", "help", "updates", "settings"]

EXPECTED = {
    "default-src": ["'self'"],
    # v21.4: 'unsafe-inline' dropped from script-src (the app's code moved into app.js and early.js).
    "script-src": ["'self'", "'wasm-unsafe-eval'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    # v27: plus the visit counter's one picture address (a picture, not a script).
    "img-src": ["'self'", "blob:", "data:", "https://dim3ry.goatcounter.com/count"],
    "media-src": ["'self'", "blob:"],
    "connect-src": ["'self'"],
    "worker-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'none'"],
    "form-action": ["'none'"],
    "frame-src": ["'none'"],
}

def seed(page, units=UNITS, settings=None):
    page.goto(URL)
    page.evaluate("""([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings])
    page.reload()
    page.wait_for_timeout(300)

def full_settings(**extra):
    s = {"palette": "ice", "tab": "dashboard", "stages": STAGES, "doneFrom": 5}
    s.update(extra)
    return s

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(120)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def loaded(page, selector):
    """True when the picture at `selector` has actually loaded (the browser didn't refuse it)."""
    return page.evaluate("""sel => { const img = document.querySelector(sel);
        return !!img && img.complete && img.naturalWidth > 0; }""", selector)

def watch(page, errors, csp):
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text and "csp-probe" not in m.text else None)
    DialogAnswers(page)

def main():
    sw = read("sw.js")
    html = read("index.html")
    errors, csp = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        watch(page, errors, csp)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page, settings=full_settings())
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21.2 or later", float(version[1:]) >= 21.2, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.2')")
        if page.evaluate("['v21.2'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v21.2 entry", entry and len(entry["changes"]) >= 1, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v21.2 entry')
        if page.evaluate("['v21.2'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the v21.2 entry mentions the safety change", entry and "Content Security Policy" in " ".join(entry["changes"]))
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the v21.2 entry mentions the safety change')
        tab(page, "updates")
        heads = page.locator("#view-updates h3").all_inner_texts()
        if page.evaluate("['v21.2'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab shows v21.2", any(h.startswith("v21.2") for h in heads), heads[:3])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab shows v21.2')
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "tesseract-core-simd-lstm.wasm", "tesseract-core-lstm.wasm", "eng.traineddata"]))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") in (1, 2))  # v62 raised DATA_VERSION to 2 for the "Needs touch-ups" rename
        for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes"]:
            check(f"storage key {key} still used", key in html)

        # ---------- 2. The CSP tag ----------
        print("\n--- 2. The CSP tag ---")
        tags = re.findall(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        check("exactly one CSP tag", len(tags) == 1, len(tags))
        policy = tags[0] if tags else ""
        first_script = html.find("<script")
        check("the CSP tag comes before every <script>", 0 < html.find("Content-Security-Policy\" content") < first_script)
        rules = {}
        for part in policy.split(";"):
            words = part.split()
            if words:
                rules[words[0]] = words[1:]
        for name, values in EXPECTED.items():
            check(f"{name} is exactly {' '.join(values)}", sorted(rules.get(name, [])) == sorted(values), rules.get(name))
        everything = " ".join(" ".join(v) for v in rules.values())
        # v27: the only outside address is the visit counter's picture, and only in img-src.
        outside = [w for w in everything.split() if w.startswith("http")]
        check("no outside websites are allowed anywhere except the visit counter's one picture", outside == ["https://dim3ry.goatcounter.com/count"] and "*" not in everything, everything)
        check("no 'unsafe-eval' (only the WebAssembly one)", "'unsafe-eval'" not in rules.get("script-src", []))
        live = page.evaluate("document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]').content")
        check("the browser sees the same policy", live == policy)
        check("no inline onclick= style handlers (the CSP would allow them, but we don't use any)",
              not re.search(r"<[^>]+\son[a-z]+\s*=", html))

        # ---------- 3. It really blocks outside code ----------
        print("\n--- 3. It really blocks outside things ---")
        outcome = page.evaluate("""() => new Promise(resolve => {
            const seen = [];
            document.addEventListener('securitypolicyviolation', e => seen.push(e.violatedDirective));
            const s = document.createElement('script');
            s.src = 'https://example.com/csp-probe.js';
            const img = document.createElement('img');
            img.src = 'https://example.com/csp-probe.png';
            document.body.append(s, img);
            setTimeout(() => { s.remove(); img.remove(); resolve(seen); }, 800);
        })""")
        check("a script from another website is refused", any(d.startswith("script-src") for d in outcome), outcome)
        check("a picture from another website is refused", any(d.startswith("img-src") for d in outcome), outcome)
        talk = page.evaluate("""() => fetch('https://example.com/csp-probe').then(() => 'sent', () => 'refused')""")
        check("the page can't send anything to another website", talk == "refused", talk)

        # ---------- 4. Every tab, no CSP errors ----------
        print("\n--- 4. Every tab ---")
        seed(page, settings=full_settings())
        for name in TABS:
            tab(page, name)
            if name == "help":
                page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
            check(f"{name} tab opens", page.is_visible(f"#view-{name}"))
            check(f"{name}: nothing scrolls sideways at 390 px", no_sideways(page))
            shot(page, f"v21-2-tab-{name}.png")
        check("no CSP errors on any tab", not csp, csp[:3])

        # ---------- 5. Photos ----------
        print("\n--- 5. Photos ---")
        tab(page, "units")
        page.click('#view-units li.unit[data-id="1"] .info')
        page.wait_for_timeout(200)
        picker = page.locator('#view-units input[type="file"][accept="image/*"]').first
        picker.set_input_files(files=[{"name": "army.png", "mimeType": "image/png", "buffer": png(300, 200)}])
        page.wait_for_function("""() => { const i = document.querySelector('#view-units .photo-tile img');
                                          return i && i.complete && i.naturalWidth > 0; }""", timeout=10000)
        check("a new photo shows in the unit's photo strip (blob: address)", loaded(page, "#view-units .photo-tile img"))
        src = page.evaluate("document.querySelector('#view-units .photo-tile img').src")
        check("…and it really is a blob: address", src.startswith("blob:"), src)
        check("the card's small picture shows", loaded(page, '#view-units li.unit[data-id="1"] img.thumb'))
        page.click("#view-units .photo-tile")
        page.wait_for_timeout(400)
        check("the photo viewer shows the full photo", page.evaluate("""() => [...document.querySelectorAll('.viewer img')]
              .some(i => i.complete && i.naturalWidth > 0)"""))
        shot(page, "v21-2-photo-viewer.png")
        page.keyboard.press("Escape")
        page.go_back()
        page.wait_for_timeout(300)
        seed(page, settings=full_settings(tab="units"))
        tab(page, "units")
        page.wait_for_timeout(300)
        check("an old-style photo (data: address) shows on its card", loaded(page, '#view-units li.unit[data-id="2"] img.thumb'))
        shot(page, "v21-2-photos-units.png")
        check("no CSP errors with photos", not csp, csp[:3])
        context.close()

        # ---------- 6 + 7. Label reader and offline ----------
        print("\n--- 6. Label reader ---")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        watch(page, errors, csp)
        seed(page, settings=full_settings())
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
        text = page.evaluate("""async () => {
          const c = document.createElement('canvas'); c.width = 700; c.height = 140;
          const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, 700, 140);
          g.fillStyle = '#000'; g.font = 'bold 64px Arial'; g.fillText('MACRAGGE BLUE', 30, 95);
          const w = await getOcrWorker(); const { data } = await w.recognize(c); return data.text; }""")
        check("the label reader still reads a test picture", "MACRAGGE" in text.upper(), text)
        check("no CSP errors from the label reader", not csp, csp[:3])

        print("\n--- 7. Offline ---")
        page.wait_for_timeout(500)
        context.set_offline(True)
        page.reload()
        page.wait_for_timeout(800)
        check("with the internet off, the app reloads", page.evaluate("typeof APP_VERSION") == "string")
        check("…shows the Dashboard", page.is_visible("#view-dashboard"))
        tab(page, "units")
        check("…and the units are there", page.locator("#view-units li.unit").count() == 2)
        tab(page, "help")
        check("…and other tabs open", page.is_visible("#view-help"))
        shot(page, "v21-2-offline.png")
        context.set_offline(False)
        check("no CSP errors offline", not csp, csp[:3])
        context.close()

        # ---------- 8. Feedback link, Privacy, Help ----------
        print("\n--- 8. Feedback link and Privacy ---")
        context = browser.new_context(viewport={"width": 360, "height": 740})
        page = context.new_page()
        watch(page, errors, csp)
        seed(page, settings=full_settings())
        tab(page, "updates")
        link = page.locator("#feedback-link")
        href = link.get_attribute("href") or ""
        check("feedback link still goes to the form", href.startswith("https://tally.so/"), href)
        check("feedback link opens in a new tab", link.get_attribute("target") == "_blank")
        rel = (link.get_attribute("rel") or "").split()
        check("feedback link has noopener and noreferrer", "noopener" in rel and "noreferrer" in rel, rel)
        check("feedback link is visible", link.is_visible())
        blank = page.evaluate("""() => [...document.querySelectorAll('a[target=_blank]')]
              .filter(a => !/noopener/.test(a.rel)).map(a => a.outerHTML.slice(0, 80))""")
        check("every new-tab link has noopener", not blank, blank)
        tab(page, "help")
        privacy = page.text_content("#privacy")
        check("Privacy mentions the Content Security Policy", "Content Security Policy" in privacy, privacy[:200])
        check("Privacy still says what stays on your phone", "Stays on your phone" in privacy)
        check("Privacy still says no tracking", "No tracking" in privacy)

        # ---------- 9. 360 px ----------
        print("\n--- 9. 360 px wide ---")
        for name in TABS:
            tab(page, name)
            check(f"{name}: nothing scrolls sideways at 360 px", no_sideways(page),
                  page.evaluate("document.documentElement.scrollWidth"))
        shot(page, "v21-2-settings-360.png")
        context.close()

        check("no CSP errors anywhere", not csp, csp[:5])
        check("no page errors", not errors, errors[:5])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
