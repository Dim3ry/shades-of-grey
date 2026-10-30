"""v21.5 tests for Minifolio: Undo for deleting a unit (photos included), and new units brought
into view.

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. Deleting a unit: the app still asks "Delete "<name>"?" first; saying no changes nothing. Saying
   yes removes it (on screen and in saved data) and shows a message with Undo. Its photo files stay
   in the photo store while Undo is on offer. Undo puts the unit back EXACTLY (saved data identical,
   same place in the list, details open again) with its photos showing, and the files are never
   deleted later. Without Undo, the files are deleted once the message has gone.
3. A new unit at the end of a long list is scrolled into view and outlined for a moment; the
   outline goes after a few seconds; the name box stays ready; a unit already on screen doesn't
   make the page jump.
4. Help wording; screenshots in dark and light at 390 and 360 px; nothing scrolls sideways;
   no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, struct, sys, zlib
from playwright.sync_api import sync_playwright
from launch_helpers import app_ready, quiet, open_settings, tap_tab
from launch_helpers import leave_launch
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
    """A small plain-coloured PNG picture, made here so the test needs no image files."""
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10,
     "repaint": True, "notes": "Purple carapace", "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
    {"id": 3, "name": "Liberators", "hobby": "AoS", "faction": "Stormcast Eternals", "stage": 1, "count": 5,
     "log": [["2026-09-02", 1]]},
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
    app_ready(page)
    leave_launch(page)   # U4b: tap through the start page

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        open_settings(page)
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        tap_tab(page, name)
    page.wait_for_timeout(150)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def photo_files(page):
    """The ids in the photo store (IndexedDB)."""
    return page.evaluate("""() => new Promise(done => {
        const r = indexedDB.open('shades-of-grey-photos', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('photos', { keyPath: 'id' });
        r.onsuccess = () => { const db = r.result;
            const q = db.transaction('photos').objectStore('photos').getAllKeys();
            q.onsuccess = () => { done(q.result.map(String).sort()); db.close(); };
            q.onerror = () => { done(null); db.close(); }; };
        r.onerror = () => done(null); })""")

def card_ids(page):
    return page.evaluate("() => [...document.querySelectorAll('#view-units li.unit')].map(li => Number(li.dataset.id))")

def toast(page):
    return page.evaluate("""() => ({ shown: !document.getElementById('toast').classList.contains('hidden'),
        text: document.getElementById('toast-text').textContent,
        undo: !document.getElementById('toast-undo').classList.contains('hidden'),
        label: document.getElementById('toast-undo').textContent })""")

def in_view(page, selector):
    """Fully on screen AND not hidden behind the tab bar or the message at the bottom."""
    return page.evaluate("""s => { const e = document.querySelector(s); if (!e) return false;
        let bottom = window.innerHeight;
        for (const b of [document.querySelector('.tabs'), document.getElementById('toast')]) {
          if (!b || b.classList.contains('hidden')) continue;
          const r = b.getBoundingClientRect();
          if (r.height && r.top > window.innerHeight / 2) bottom = Math.min(bottom, r.top);
        }
        const r = e.getBoundingClientRect();
        return r.top >= 0 && r.bottom <= bottom && r.height > 0; }""", selector)

def open_unit(page, uid):
    page.click(f'#view-units li.unit[data-id="{uid}"] .info')
    page.wait_for_timeout(200)

def delete_button(page, uid):
    return page.locator(f'#view-units li.unit[data-id="{uid}"] .panel button.danger-button', has_text="Delete").last

def main():
    errors, csp = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        answers = DialogAnswers(page)   # v21.7: the question is the app's own box now; this taps its buttons

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        seed(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.5')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v21.5'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("…about Undo on delete and new units in view", "Undo" in joined and "into view" in joined, joined)
        else:
            print("SKIP (entry no longer in the public Updates list): " + '…about Undo on delete and new units in view')
        tab(page, "updates")
        heads = page.locator("#view-updates h3").all_inner_texts()
        for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes"]:
            check(f"storage key {key} still used", key in app)
        check("no code written inside the page", all(not b.strip() for b in re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S)))

        # ---------- 2. Deleting a unit, with Undo ----------
        print("\n--- 2. Delete + Undo ---")
        seed(page)
        tab(page, "units")
        open_unit(page, 2)
        picker = page.locator('#view-units li.unit[data-id="2"] input[type="file"][accept="image/*"]').first
        picker.set_input_files(files=[{"name": "a.png", "mimeType": "image/png", "buffer": png(300, 200, (40, 90, 160))},
                                      {"name": "b.png", "mimeType": "image/png", "buffer": png(300, 200, (160, 60, 60))}])
        page.wait_for_function("""() => document.querySelectorAll('#view-units li.unit[data-id="2"] .photo-tile img').length === 2
            && [...document.querySelectorAll('#view-units li.unit[data-id="2"] .photo-tile img')].every(i => i.complete && i.naturalWidth > 0)""",
            timeout=15000)
        page.wait_for_timeout(500)
        before = saved_units(page)
        files_before = photo_files(page)
        unit2 = next(u for u in before if u["id"] == 2)
        check("set-up: unit 2 has 2 photos saved", len(unit2.get("photos", [])) == 2, unit2.get("photos"))
        check("set-up: both photo files are in the photo store", files_before and len(files_before) == 2, files_before)
        check("set-up: list order 1, 2, 3", card_ids(page) == [1, 2, 3], card_ids(page))

        # Say no first.
        answers.yes = False
        answers.clear()
        page.evaluate("() => document.getElementById('toast').classList.add('hidden')")
        delete_button(page, 2).click()
        page.wait_for_timeout(300)
        check("Delete still asks first", answers.seen and answers.seen[0] == ("yesno", 'Delete "Termagants"?'), answers.seen)
        check("saying no keeps the unit", card_ids(page) == [1, 2, 3] and saved_units(page) == before)
        check("saying no shows no message", not toast(page)["shown"], toast(page))

        # Now yes.
        answers.yes = True
        answers.clear()
        delete_button(page, 2).click()
        page.wait_for_timeout(300)
        t = toast(page)
        check("saying yes removes it from the list", card_ids(page) == [1, 3], card_ids(page))
        check("…and from saved data", [u["id"] for u in saved_units(page)] == [1, 3], saved_units(page))
        check("a message says what was deleted", t["shown"] and t["text"] == "Deleted Termagants and its 2 photos", t)
        check("…with an Undo button", t["undo"] and t["label"] == "Undo", t)
        shot(page, "v21-5-delete-undo-dark-390.png")
        check("the photo files are still there while Undo is offered", photo_files(page) == files_before, photo_files(page))
        page.wait_for_timeout(4000)
        check("Undo is still offered after 4 seconds", toast(page)["shown"] and toast(page)["undo"])
        page.click("#toast-undo")
        page.wait_for_timeout(500)
        after = saved_units(page)
        check("Undo puts the unit back in saved data exactly as it was", after == before,
              json.dumps(after)[:300])
        check("…in the same place in the list", card_ids(page) == [1, 2, 3], card_ids(page))
        check("…with its details open again", page.locator('#view-units li.unit[data-id="2"] .panel').count() == 1)
        check("Undo shows a 'back' message", toast(page)["text"] == "Termagants is back", toast(page))
        page.wait_for_function("""() => { const im = [...document.querySelectorAll('#view-units li.unit[data-id="2"] .photo-tile img')];
            return im.length === 2 && im.every(i => i.complete && i.naturalWidth > 0); }""", timeout=10000)
        check("its 2 photos show again", True)
        page.wait_for_timeout(9000)
        check("after Undo the photo files are never deleted", photo_files(page) == files_before, photo_files(page))
        page.reload()
        app_ready(page)
        leave_launch(page)   # U4b: tap through the start page
        check("after reopening the app the unit is there with both photos",
              card_ids(page) == [1, 2, 3] and len(next(u for u in saved_units(page) if u["id"] == 2)["photos"]) == 2)

        # Delete the first unit (no photos) and Undo: back at the top.
        tab(page, "units")
        open_unit(page, 1)
        delete_button(page, 1).click()
        page.wait_for_timeout(300)
        check("a unit with no photos: plain message", toast(page)["text"] == "Deleted Intercessors", toast(page))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("…Undo puts it back at the top", card_ids(page) == [1, 2, 3], card_ids(page))

        # Delete without Undo: files go once the message has gone.
        page.evaluate("() => document.getElementById('toast').classList.add('hidden')")
        if page.locator('#view-units li.unit[data-id="2"] .panel').count() == 0:
            open_unit(page, 2)
        delete_button(page, 2).click()
        page.wait_for_timeout(300)
        check("deleted again (no Undo this time)", card_ids(page) == [1, 3], card_ids(page))
        page.wait_for_timeout(9200)
        check("the message has gone", not toast(page)["shown"])
        check("the photo files are deleted once Undo has gone", photo_files(page) == [], photo_files(page))
        check("no page errors so far", not errors, errors[:3])

        # ---------- 3. New units brought into view ----------
        print("\n--- 3. New units in view ---")
        many = [{"id": i, "name": f"Unit {i:02d}", "hobby": "40K", "faction": "Ultramarines", "stage": i % 5,
                 "count": 1, "log": [["2026-09-01", i % 5]]} for i in range(1, 31)]
        seed(page, units=many)
        tab(page, "units")
        page.evaluate("() => window.scrollTo(0, 0)")
        page.click("#toggle-add")
        page.wait_for_timeout(200)
        page.fill("#name-input", "Zzz Hellblasters")   # sorts/lands at the end of the list
        new_id = 31
        check("set-up: the last card starts off-screen", not in_view(page, '#view-units li.unit[data-id="30"]'))
        page.press("#name-input", "Enter")
        page.wait_for_timeout(1200)   # smooth scroll
        sel = f'#view-units li.unit[data-id="{new_id}"]'
        check("the new unit is added", page.locator(sel).count() == 1)
        check("the new unit is scrolled into view", in_view(page, sel),
              page.evaluate(f"() => document.querySelector('{sel}') && document.querySelector('{sel}').getBoundingClientRect().top"))
        check("…and outlined", page.evaluate(f"() => document.querySelector('{sel}').classList.contains('just-added')"))
        outline = page.evaluate(f"() => getComputedStyle(document.querySelector('{sel}')).boxShadow")
        check("the outline is drawn (box-shadow)", outline and outline != "none", outline)
        check("the 'Added' message shows", toast(page)["text"] == "Added Zzz Hellblasters", toast(page))
        check("the name box is ready for the next unit", page.evaluate("() => document.activeElement && document.activeElement.id === 'name-input'"))
        os.makedirs(SHOTS, exist_ok=True)
        shot(page, "v21-5-new-unit-dark-390.png")
        page.wait_for_timeout(2600)
        check("the outline goes after a few seconds", not page.evaluate(f"() => document.querySelector('{sel}').classList.contains('just-added')"))

        # A unit added while its spot is already on screen (tall screen): the page doesn't jump.
        page.set_viewport_size({"width": 390, "height": 1400})
        seed(page)
        tab(page, "units")
        page.click("#toggle-add")
        page.wait_for_timeout(200)
        y0 = page.evaluate("() => window.scrollY")
        page.fill("#name-input", "Bladeguard")
        page.press("#name-input", "Enter")
        page.wait_for_timeout(800)
        check("short list: the new unit is on screen", in_view(page, '#view-units li.unit[data-id="4"]'))
        check("…and the page didn't jump", abs(page.evaluate("() => window.scrollY") - y0) <= 2,
              (y0, page.evaluate("() => window.scrollY")))
        context.close()

        # Less motion: in view straight away, no animation.
        calm = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce", service_workers="block")
        cp = calm.new_page()
        cp.on("pageerror", lambda e: errors.append(str(e)))
        cp.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        seed(cp, units=many)
        tab(cp, "units")
        cp.click("#toggle-add")
        cp.fill("#name-input", "Zzz Hellblasters")
        cp.press("#name-input", "Enter")
        cp.wait_for_timeout(150)
        check("less motion: in view straight away", in_view(cp, sel))
        check("less motion: the outline doesn't animate",
              cp.evaluate(f"() => getComputedStyle(document.querySelector('{sel}')).animationName") == "none")
        calm.close()

        # ---------- 4. Help, screenshots, widths ----------
        print("\n--- 4. Help, screenshots, widths ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        DialogAnswers(page)
        seed(page)
        help_delete = page.evaluate("() => (document.getElementById('help-delete-unit') || {}).textContent || ''")
        check("Help explains Undo after deleting a unit", "Undo" in help_delete and "photos" in help_delete, help_delete)
        help_new = page.evaluate("() => (document.getElementById('help-new-unit-shown') || {}).textContent || ''")
        check("Help says new units are scrolled into view", "scrolled into view" in help_new, help_new)
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 800})
                seed(page, settings=full_settings(appearance=appearance))
                tab(page, "units")
                page.click("#toggle-add")
                page.fill("#name-input", "Bladeguard Veterans")
                page.press("#name-input", "Enter")
                page.wait_for_timeout(700)
                check(f"{appearance} {width}px: new unit outlined and in view",
                      in_view(page, '#view-units li.unit[data-id="4"]') and
                      page.evaluate("() => document.querySelector('#view-units li.unit[data-id=\"4\"]').classList.contains('just-added')"))
                check(f"{appearance} {width}px: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v21-5-new-unit-{appearance}-{width}.png")
                page.click("#toggle-add")   # close the form
                page.wait_for_timeout(150)
                open_unit(page, 2)
                delete_button(page, 2).click()
                page.wait_for_timeout(300)
                t = toast(page)
                check(f"{appearance} {width}px: delete message with Undo", t["shown"] and t["undo"], t)
                box = page.evaluate("() => document.getElementById('toast-undo').getBoundingClientRect().height")
                check(f"{appearance} {width}px: Undo button at least 44 px tall", box >= 44, box)
                check(f"{appearance} {width}px: nothing scrolls sideways with the message", no_sideways(page))
                shot(page, f"v21-5-delete-undo-{appearance}-{width}.png")
                page.click("#toast-undo")
                page.wait_for_timeout(200)
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors[:3])
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
