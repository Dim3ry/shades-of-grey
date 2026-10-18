"""v21.6 tests for Minifolio: notices are the app's own messages, not browser pop-ups.

v21.6 is the first half of "in-app messages": the 35 alert() notices became toasts (the little
message at the bottom). The 16 confirm() questions and 5 prompt() questions are left for v21.7,
which adds the in-app dialog (Back button = Cancel, 44 px buttons and so on), so those checks
belong to test_v21_7.

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. The source: no alert( left in app.js, 35 notices go through notify(), confirm( and prompt( are
   still there (16 and 5) for v21.7.
3. Real notices, each with the same words as before, no browser pop-up at all, and nothing changed
   behind them: stage editor (10 stages, a blank name, a repeated name), restore (not a backup,
   damaged, newer version, nothing in it), CSV (no name column, a picture, nothing in the file,
   export with no units), Warhammer paste that isn't a list.
4. How a notice behaves: longer ones stay longer, a tap hides one, a tap does NOT hide a message
   with an Undo button, the next ordinary message is not marked as a notice, long words wrap.
5. Screenshots in dark and light at 390 and 360 px; the message stays inside the screen and nothing
   scrolls sideways; no page errors and no CSP errors.
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
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

def png(width=64, height=48, rgb=(40, 90, 160)):
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10,
     "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
]
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")

def full_settings(**extra):
    s = {"palette": "ice", "tab": "units", "stages": STAGES, "doneFrom": 5, "examplesChecked": True}
    s.update(extra)
    return s

def seed(page, units=UNITS, settings=None):
    page.goto(URL)
    page.evaluate("""async ([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s || {}));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""",
                  [units, settings or full_settings()])
    page.reload()
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def toast(page):
    return page.evaluate("""() => { const t = document.getElementById('toast');
        return { shown: !t.classList.contains('hidden'),
                 text: document.getElementById('toast-text').textContent,
                 kind: t.dataset.kind || '',
                 undo: !document.getElementById('toast-undo').classList.contains('hidden') }; }""")

def main():
    errors, csp, browser_boxes = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        # Any browser pop-up at all is a failure (since v21.7 the questions are the app's own box too;
        # this test only needs the in-app box answered if one ever shows).
        def on_dialog(d):
            browser_boxes.append(d.message)
            d.accept()
        page.on("dialog", on_dialog)
        DialogAnswers(page)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21.6 or later", float(version[1:]) >= 21.6, version)
        check("version is a plain number", re.fullmatch(r"v\d+(\.\d+)?", version) is not None, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="(early|app)\.js\?v=([\d.]+)"', html)
        check("both script tags carry ?v= matching APP_VERSION", sorted(tags) == [("app", version[1:]), ("early", version[1:])], tags)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.6')")
        if page.evaluate("['v21.6'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v21.6 entry", entry and len(entry["changes"]) >= 2, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v21.6 entry')
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v21.6'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("…about notices, and says questions come next", "notice" in joined.lower() and "yes or no" in joined, joined)
        else:
            print("SKIP (entry no longer in the public Updates list): " + '…about notices, and says questions come next')
        check("v21.6 is the newest Updates entry or later", float(page.evaluate("CHANGELOG[0].version")[1:]) >= 21.6)
        tab(page, "updates")
        heads = page.locator("#view-updates h3").all_inner_texts()
        if page.evaluate("['v21.6'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab lists v21.6", any(h.startswith("v21.6") for h in heads), heads[:4])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab lists v21.6')
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "tesseract-core-simd-lstm.wasm", "tesseract-core-lstm.wasm", "eng.traineddata"]))
        check("LICENSE-paint-list.txt is kept", os.path.exists(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        wf = read(".github/workflows/zap-scan.yml")
        check("ZAP workflow is still the passive baseline scan", "action-baseline" in wf and "action-full-scan" not in wf)
        csp_tag = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        check("the CSP is exactly v21.4's", csp_tag and csp_tag.group(1) == V21_4_CSP, csp_tag and csp_tag.group(1))
        check("no code written inside the page", not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        for key in ["mini-tracker-models", "shades-of-grey-settings"]:
            check(f"storage key {key} still used", key in app)

        # ---------- 2. The source ----------
        print("\n--- 2. The source ---")
        check("no alert( left in app.js", re.search(r"(?<![A-Za-z_.])alert\(", app) is None)
        check("no window.alert either", "window.alert" not in app)
        code = "\n".join(re.sub(r"\s//.*$", "", l) for l in app.splitlines() if not l.strip().startswith("//"))   # without comments
        calls = len(re.findall(r"(?<![A-Za-z_.])notify\(", code)) - 1   # minus the definition
        check("at least the 35 original notices go through notify() (later versions add a few)", calls >= 35, calls)
        # v21.7 replaced these, so "left for v21.7" became "no more than at v21.6" (16 and 5).
        check("no more than the 16 confirm( questions of v21.6", len(re.findall(r"(?<![A-Za-z_.])confirm\(", app)) <= 16,
              len(re.findall(r"(?<![A-Za-z_.])confirm\(", app)))
        check("no more than the 5 prompt( questions of v21.6", len(re.findall(r"(?<![A-Za-z_.])prompt\(", app)) <= 5,
              len(re.findall(r"(?<![A-Za-z_.])prompt\(", app)))

        # ---------- 3. Real notices ----------
        print("\n--- 3. Real notices ---")
        def says(fragment):
            page.wait_for_timeout(250)
            t = toast(page)
            return t["shown"] and t["kind"] == "notice" and not t["undo"] and fragment in t["text"], t

        # Stage editor
        seed(page)
        tab(page, "settings")
        # v21.9: the Settings page has the Settings / Help / Updates switch above it now, so the button sits lower.
        # Near the bottom edge the tab bar coming back (the cursor leaves the new box) would cover it, so centre it first.
        centre = "() => document.getElementById('add-stage').scrollIntoView({ block: 'center' })"
        page.evaluate(centre)
        page.click("#add-stage")
        page.evaluate(centre)
        page.click("#add-stage")           # 8 + 2 = 10
        page.evaluate(centre)
        page.click("#add-stage")           # the 11th is refused
        ok, t = says("You can have up to 10 stages.")
        check("an 11th stage gets the notice 'You can have up to 10 stages.'", ok, t)
        check("…and the list stays at 10", page.locator("#stage-list input").count() == 10, page.locator("#stage-list input").count())
        page.fill("#stage-list input >> nth=9", "")
        page.click("#save-stages")
        ok, t = says("Every stage needs a name.")
        check("a blank stage name gets 'Every stage needs a name.'", ok, t)
        page.fill("#stage-list input >> nth=9", "Assembled")
        page.click("#save-stages")
        ok, t = says("Each stage needs a different name.")
        check("a repeated stage name gets 'Each stage needs a different name.'", ok, t)
        saved = json.loads(page.evaluate("() => localStorage.getItem('shades-of-grey-settings')"))
        check("…and the saved stages didn't change", saved.get("stages") == STAGES, saved.get("stages"))

        # Restore backup refusals
        def restore_try(name, data, mime="application/json"):
            seed(page, UNITS)
            tab(page, "settings")
            page.set_input_files("#restore-file", files=[{"name": name, "mimeType": mime, "buffer": data}])
            page.wait_for_timeout(400)

        def untouched():
            return [u["name"] for u in saved_units(page)] == ["Intercessors", "Termagants"]

        restore_try("text.json", b'"hello"')
        ok, t = says("That file doesn't look like a Minifolio backup.")
        check("restore: a file that isn't a backup gets the same words", ok, t)
        check("…and nothing changed", untouched())
        restore_try("bad-shape.json", json.dumps({"app": "Minifolio", "models": "nope"}).encode())
        ok, t = says("This backup is damaged")
        check("restore: a damaged backup is refused with the same words", ok and "Nothing has changed." in t["text"], t)
        check("…and nothing changed", untouched())
        restore_try("newer.json", json.dumps({"app": "Minifolio", "dataVersion": 99, "models": UNITS}).encode())
        ok, t = says("saved by a newer version of Minifolio")
        check("restore: a newer backup asks you to reload first", ok, t)
        check("…and nothing changed", untouched())
        restore_try("stages.json", json.dumps({"app": "Minifolio", "stages": ["A", "A"], "models": UNITS}).encode())
        ok, t = says("list of stages is damaged")
        check("restore: a damaged stage list is refused", ok, t)
        restore_try("empty.json", json.dumps({"app": "Minifolio", "models": []}).encode())
        ok, t = says("it has no units or recipes in it")
        check("restore: a backup with nothing in it is refused", ok, t)
        check("…and nothing changed", untouched())

        # CSV
        def csv_try(name, data, mime="text/csv"):
            seed(page, UNITS)
            tab(page, "settings")
            page.set_input_files("#csv-file", files=[{"name": name, "mimeType": mime, "buffer": data}])
            page.wait_for_timeout(350)

        csv_try("nonames.csv", b"unit_title,faction\nBoyz,Orks\n")
        ok, t = says('no "name" column')
        check("CSV: no name column gets the same words", ok, t)
        csv_try("renamed.csv", png())
        ok, t = says("isn't a CSV file")
        check("CSV: a picture renamed to .csv is refused", ok, t)
        check("…and no review box opened, nothing changed", not page.is_visible("#review") and untouched())
        csv_try("titles-only.csv", b"name,faction\n")
        ok, t = says("No units found in that file.")
        check("CSV: a file with only the title line says 'No units found in that file.'", ok, t)
        seed(page, [])
        tab(page, "settings")
        page.click("#csv-export-button")
        ok, t = says("There are no units to export yet.")
        check("CSV export with no units says 'There are no units to export yet.'", ok, t)

        # Warhammer paste
        seed(page, UNITS)
        tab(page, "units")
        page.click("#toggle-add")
        page.click("#add-wh")
        page.fill("#wh-text", "this is not an army list")
        page.click("#wh-read")
        ok, t = says("doesn't look like a list exported from the Warhammer app")
        check("army list paste that isn't a list gets the same words", ok and 'Lictor (60 points)' in t["text"], t)

        check("none of these showed a browser pop-up", not browser_boxes, browser_boxes[:3])

        # ---------- 4. How a notice behaves ----------
        print("\n--- 4. How a notice behaves ---")
        seed(page)
        secs = page.evaluate("""() => { const real = window.setTimeout; let last = null;
            window.setTimeout = (fn, ms, ...rest) => { last = ms; return real(fn, ms, ...rest); };
            notify('Short one.'); const a = last;
            notify('x'.repeat(300)); const b = last;
            notify('Mid '.repeat(25)); const c = last;
            window.setTimeout = real; return [a, b, c]; }""")
        check("a short notice stays 6 seconds", secs[0] == 6000, secs)
        check("a very long notice stays 20 seconds (the most)", secs[1] == 20000, secs)
        check("a medium one stays longer than a short one but less than the longest", 6000 < secs[2] < 20000, secs)
        page.evaluate("notify('Tap me away.')")
        page.click("#toast-text")
        page.wait_for_timeout(100)
        check("a tap hides a notice", not toast(page)["shown"], toast(page))
        page.evaluate("showToast('Deleted Thing', () => { window.__undone = true; }, 'Undo', 8)")
        page.click("#toast-text")
        page.wait_for_timeout(100)
        t = toast(page)
        check("a tap does NOT hide a message that has an Undo button", t["shown"] and t["undo"], t)
        check("…and an ordinary message is not marked as a notice", t["kind"] == "", t)
        page.click("#toast-undo")
        check("Undo still works", page.evaluate("window.__undone === true"))
        page.evaluate("notify('First')")
        page.evaluate("showToast('Saved something')")
        check("a notice followed by an ordinary message loses its mark", toast(page)["kind"] == "")

        # ---------- 5. Screenshots, widths ----------
        print("\n--- 5. Screenshots and widths ---")
        long_photo = ("Backup restored, but 3 of 5 photos couldn't be loaded on this device (2 of 5 in the file worked), "
                      "so they won't show. Keep the backup file safe: you can restore it again later, for example after freeing some space.")
        wide_word = "A_very_long_file_name_with_no_spaces_at_all_just_underscores_" * 2 + ".csv"
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 800})
                seed(page, settings=full_settings(appearance=appearance))
                tab(page, "units")
                page.evaluate("t => notify(t)", long_photo)
                page.wait_for_timeout(200)
                box = page.evaluate("""() => { const r = document.getElementById('toast').getBoundingClientRect();
                    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: window.innerWidth, h: window.innerHeight }; }""")
                check(f"{appearance} {width}px: long notice sits inside the screen",
                      box["left"] >= 0 and box["right"] <= box["w"] and box["top"] >= 0 and box["bottom"] <= box["h"], box)
                check(f"{appearance} {width}px: nothing scrolls sideways with a long notice", no_sideways(page))
                shot(page, f"v21-6-notice-{appearance}-{width}.png")
                page.evaluate("t => notify('\"' + t + '\" isn\\'t a CSV file (it isn\\'t plain text). Nothing has changed.')", wide_word)
                page.wait_for_timeout(200)
                check(f"{appearance} {width}px: a long file name wraps, nothing scrolls sideways", no_sideways(page))
                inside = page.evaluate("""() => { const t = document.getElementById('toast').getBoundingClientRect();
                    const s = document.getElementById('toast-text').getBoundingClientRect();
                    return s.right <= t.right + 1 && s.left >= t.left - 1; }""")
                check(f"{appearance} {width}px: the words stay inside the message box", inside)
                shot(page, f"v21-6-notice-long-word-{appearance}-{width}.png")
        context.close()
        browser.close()

    check("no browser pop-up boxes for notices at any point", not browser_boxes, browser_boxes[:3])
    check("no page errors", not errors, errors[:3])
    check("no CSP errors", not csp, csp[:3])
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
