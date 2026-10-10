"""v18.3 tests for Minifolio: small safety fixes.

Checks:
1. Version numbers, the Updates entry, the README licence line, CNAME kept, storage names unchanged.
2. Camera: a double tap opens ONE camera; Cancel, leaving the app, closing the scan panel and
   leaving while it's still starting all leave no camera running.
3. Dates: at 00:30 UK summer time, backup names and "last backup" use the UK date, not the day before.
4. Recipes-only restore: Undo puts your recipes back; the old recipes are listed in Recover earlier data.
5. Data version number: saved in settings and backups; newer data stops an older copy saving
   (at start-up, from another window, and on restore of a newer backup).
6. Label reader: loads from the app's own ocr folder (no outside websites), reads printed text,
   and still reads with the internet off after the first scan. About no longer mentions a download.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, json, os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

OLD_BOOK = {
    "paints": [{"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a"}],
    "recipes": [{"id": 1, "name": "Old armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}],
    "schemes": [],
}
BACKUP_BOOK = {
    "paints": [{"id": 1, "brand": "", "name": "Blue", "colour": "#0000ff"}],
    "recipes": [{"id": 1, "name": "Backup armour", "part": "Armour",
                 "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]},
                {"id": 2, "name": "Backup eyes", "part": "Eyes",
                 "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}],
}

def seed(page, book=None):
    page.goto(URL)
    page.evaluate("b => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]');"
                  " if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }", book)
    page.reload()
    page.wait_for_timeout(300)

def stored(page, key):
    return page.evaluate("k => JSON.parse(localStorage.getItem(k) || 'null')", key)

def recipe_names(page):
    return [r["name"] for r in stored(page, "shades-of-grey-recipes")["recipes"]]

def main():
    sw = read("sw.js")
    html = read("index.html")
    readme = read("README.md")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

        # ---------- 1. Versions, Updates, README, kept names ----------
        print("--- 1. Versions and paperwork ---")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialogs = []
        def on_dialog(d):
            dialogs.append(d.message)
            d.accept()
        page.on("dialog", on_dialog)
        seed(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v18.3 or later", float(version[1:]) >= 18.3, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        at = page.evaluate("CHANGELOG.findIndex(e => e.version === 'v18.3')")
        check("Updates lists v18.3", at >= 0)
        entry = page.evaluate(f"CHANGELOG[{max(at, 0)}]")
        text = " ".join(entry["changes"])
        for word in ["camera", "offline", "Undo", "time zone", "reload"]:
            check(f"v18.3 entry mentions {word!r}", word in text)
        check("v18.2 is listed straight below v18.3", page.evaluate(f"CHANGELOG[{at + 1}].version") == "v18.2")
        check("README says © 2026 George Atter-Dimery. All rights reserved.",
              "© 2026 George Atter-Dimery. All rights reserved." in readme, readme)
        check("README credits the label reader's Apache licence", "Apache License 2.0" in readme)
        check("CNAME file is still there", os.path.exists(os.path.join(ROOT, "CNAME")) and "minifolio.app" in read("CNAME"))
        for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes", "shades-of-grey-photos"]:
            check(f"storage name {key!r} unchanged", f'"{key}"' in html)
        check("sw.js cache names unchanged", '"shades-of-grey-" + VERSION' in sw and '"shades-of-grey-label-reader"' in sw)
        check("no world-time dates left (toISOString().slice(0, 10))", "toISOString().slice(0, 10)" not in html)

        # ---------- 2. Camera ----------
        print("\n--- 2. Camera ---")
        context.grant_permissions(["camera"], origin=BASE.rstrip("/"))
        # Keep a list of every camera stream the page opens, so we can see which are still live.
        context.add_init_script("""
          window.__streams = [];
          const real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
          navigator.mediaDevices.getUserMedia = async (c) => {
            if (window.__slowCamera) await new Promise(r => setTimeout(r, 600));
            const s = await real(c); window.__streams.push(s); return s; };
          window.__live = () => window.__streams.filter(s => s.getTracks().some(t => t.readyState === 'live')).length;
        """)
        seed(page)
        page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
        page.click("#scan-button")
        scan = page.locator("#scan-panel button", has_text="Scan a label")
        scan.click()
        scan.click(force=True)
        page.wait_for_selector("#scan-camera video", timeout=5000)
        page.wait_for_timeout(500)
        check("double tap opens only one camera view", page.locator("#scan-camera").count() == 1)
        check("double tap opens only one camera stream", page.evaluate("window.__streams.length") == 1,
              page.evaluate("window.__streams.length"))
        page.click("#cam-cancel")
        page.wait_for_timeout(200)
        check("Cancel: no camera left running", page.evaluate("window.__live()") == 0 and page.locator("#scan-camera").count() == 0)

        hide = "Object.defineProperty(document, 'hidden', { get: () => true, configurable: true }); document.dispatchEvent(new Event('visibilitychange'))"
        show = "delete document.hidden"
        scan.click()
        page.wait_for_selector("#scan-camera video", timeout=5000)
        page.evaluate(hide)
        page.wait_for_timeout(200)
        check("leaving the app switches the camera off", page.evaluate("window.__live()") == 0 and page.locator("#scan-camera").count() == 0,
              page.evaluate("window.__live()"))
        page.evaluate(show)

        scan.click()
        page.wait_for_selector("#scan-camera video", timeout=5000)
        page.evaluate("window.dispatchEvent(new Event('pagehide'))")
        page.wait_for_timeout(200)
        check("closing the page (pagehide) switches the camera off", page.evaluate("window.__live()") == 0)

        page.evaluate("window.__slowCamera = true")
        scan.click()
        page.wait_for_timeout(100)   # still starting
        page.evaluate(hide)
        page.wait_for_timeout(1000)
        check("leaving while the camera is still starting: it's switched off when it arrives",
              page.evaluate("window.__live()") == 0 and page.locator("#scan-camera").count() == 0,
              (page.evaluate("window.__live()"), page.locator("#scan-camera").count()))
        page.evaluate(show)
        page.evaluate("window.__slowCamera = false")
        scan.click()
        page.wait_for_selector("#scan-camera video", timeout=5000)
        check("the camera still opens normally afterwards", page.evaluate("window.__live()") == 1)
        page.click("#cam-cancel")
        page.wait_for_timeout(200)
        page.evaluate("window.__slowCamera = true")
        scan.click()
        page.wait_for_timeout(100)
        page.click("#scan-button")   # close the scan panel while the camera is starting
        page.wait_for_timeout(1000)
        check("closing the scan panel while starting: no camera left on", page.evaluate("window.__live()") == 0
              and page.locator("#scan-camera").count() == 0)
        context.close()

        # ---------- 3. Dates in your time zone ----------
        print("\n--- 3. Dates ---")
        context = browser.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/London", accept_downloads=True)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        # 23:30 world time on 15 July = 00:30 on 16 July in UK summer time.
        page.clock.install(time=datetime.datetime(2026, 7, 15, 23, 30, tzinfo=datetime.timezone.utc))
        seed(page)
        check("todayISO() gives the UK date", page.evaluate("todayISO()") == "2026-07-16", page.evaluate("todayISO()"))
        page.click("nav button[data-tab='settings']")
        with page.expect_download() as d:
            page.click("#export-button")
        name = d.value.suggested_filename
        check("backup file is named with the UK date", name == "minifolio-backup-2026-07-16.json", name)
        check("'last backup' is saved with the UK date", stored(page, "shades-of-grey-settings").get("lastBackup") == "2026-07-16")
        since = page.evaluate("daysSince('2026-07-16')")
        check("daysSince(today) is between 0 and 1 (reads dates as UK midnight)", 0 <= since < 1, since)
        since = page.evaluate("daysSince('2026-07-09')")
        check("daysSince(a week ago) is 7 and a bit", 7 <= since < 8, since)
        context.close()

        # ---------- 4. Recipes-only restore: Undo and Recover ----------
        print("\n--- 4. Recipes-only restore ---")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialogs = []
        page.on("dialog", on_dialog)
        seed(page, OLD_BOOK)
        ronly = {"app": "Minifolio", "version": 6, "models": [], "recipes": BACKUP_BOOK}
        page.click("nav button[data-tab='settings']")
        page.set_input_files("#restore-file", files=[{"name": "r.json", "mimeType": "application/json", "buffer": json.dumps(ronly).encode()}])
        page.wait_for_timeout(500)
        check("recipes-only restore replaces the recipes", recipe_names(page) == ["Backup armour", "Backup eyes"], recipe_names(page))
        check("its message has an Undo button", "Recipes restored" in page.inner_text("#toast-text")
              and page.is_visible("#toast-undo") and page.inner_text("#toast-undo") == "Undo")
        copy = stored(page, "shades-of-grey-recipes-before-recipes-restore")
        check("a copy of the old recipes is kept, dated", copy and copy["book"]["recipes"][0]["name"] == "Old armour"
              and re.match(r"\d{4}-\d{2}-\d{2}$", copy.get("date", "")), copy)
        check("the full-restore copy names are left alone", stored(page, "shades-of-grey-recipes-before-restore") is None)
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("Undo puts the old recipes back (and saves them)", recipe_names(page) == ["Old armour"], recipe_names(page))
        page.reload()
        page.wait_for_timeout(300)
        check("...still there after a reload", recipe_names(page) == ["Old armour"])
        # Restore again, then bring the old recipes back from Recover earlier data instead.
        page.click("nav button[data-tab='settings']")
        page.set_input_files("#restore-file", files=[{"name": "r.json", "mimeType": "application/json", "buffer": json.dumps(ronly).encode()}])
        page.wait_for_timeout(500)
        page.evaluate("renderRecover()")
        item = page.locator("#recover-list li", has_text="recipes only")
        check("Recover earlier data lists 'Before Restore backup (recipes only): 1 recipe'",
              item.count() == 1 and "1 recipe" in item.inner_text() and page.is_visible("#recover-card"),
              page.inner_text("#recover-list") if page.locator("#recover-list").count() else "")
        units_before = stored(page, "mini-tracker-models")
        item.locator("button").click()
        page.wait_for_timeout(300)
        check("Recover brings the old recipes back, units untouched",
              recipe_names(page) == ["Old armour"] and stored(page, "mini-tracker-models") == units_before, recipe_names(page))
        check("Recover has Undo too", page.inner_text("#toast-undo") == "Undo" and page.is_visible("#toast-undo"))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        check("...which swaps back", recipe_names(page) == ["Backup armour", "Backup eyes"], recipe_names(page))
        # An old copy (over 30 days) is cleared at start-up.
        page.evaluate("localStorage.setItem('shades-of-grey-recipes-before-recipes-restore', JSON.stringify({date: '2020-01-01', book: {recipes: []}}))")
        page.reload()
        page.wait_for_timeout(300)
        check("a recipes copy over 30 days old is removed at start-up",
              stored(page, "shades-of-grey-recipes-before-recipes-restore") is None)
        context.close()

        # ---------- 5. Data version number ----------
        print("\n--- 5. Data version number ---")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialogs = []
        page.on("dialog", on_dialog)
        seed(page)
        page.evaluate("save()")
        dv = page.evaluate("DATA_VERSION")
        check("DATA_VERSION is a whole number of 1 or more", isinstance(dv, int) and dv >= 1, dv)
        check("saved settings carry the data version", stored(page, "shades-of-grey-settings").get("dataVersion") == dv)
        check("backups carry the data version", page.evaluate("backupData().dataVersion") == dv)
        check("no banner normally", not page.is_visible("#save-banner"))

        # Another, NEWER copy of the app saves in a second window.
        page2 = context.new_page()
        page2.goto(URL)
        page2.wait_for_timeout(300)
        page2.evaluate("""() => { const s = JSON.parse(localStorage.getItem('shades-of-grey-settings'));
                           s.dataVersion = 99; localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""")
        page.wait_for_timeout(600)
        check("this older window shows the 'Please reload' banner", page.is_visible("#save-banner")
              and "newer version" in page.inner_text("#save-banner") and page.inner_text("#banner-retry") == "Reload",
              page.inner_text("#save-banner"))
        units_text = page.evaluate("localStorage.getItem('mini-tracker-models')")
        ok = page.evaluate("(models.push({id: 999, name: 'Test', hobby: '', faction: '', stage: 0, count: 1}), saveAll())")
        check("...and refuses to save over the newer data", ok is False
              and page.evaluate("localStorage.getItem('mini-tracker-models')") == units_text
              and stored(page, "shades-of-grey-settings")["dataVersion"] == 99)
        page2.close()

        # Opening the app when newer data is already saved.
        page.reload()
        page.wait_for_timeout(400)
        check("opening with newer data saved: banner shows at once", page.is_visible("#save-banner")
              and "newer version" in page.inner_text("#save-banner"))
        check("the data version on the device is left at 99", stored(page, "shades-of-grey-settings")["dataVersion"] == 99)
        dialogs.clear()
        page.evaluate("showNotSaved()")
        check("'Not saved' messages say to reload, not that storage is full",
              "newer version" in page.inner_text("#toast-text") and page.inner_text("#toast-undo") == "Reload")

        # A backup from a newer version.
        seed(page)
        page.evaluate("save()")
        newer = {"app": "Minifolio", "version": 6, "dataVersion": 99,
                 "models": [{"id": 1, "name": "Future unit", "hobby": "", "faction": "", "stage": 0, "count": 1}]}
        page.click("nav button[data-tab='settings']")
        dialogs.clear()
        page.set_input_files("#restore-file", files=[{"name": "n.json", "mimeType": "application/json", "buffer": json.dumps(newer).encode()}])
        page.wait_for_timeout(400)
        check("a backup from a newer version is refused with a clear message",
              any("newer version of Minifolio" in d for d in dialogs) and stored(page, "mini-tracker-models") == [], dialogs)
        older = dict(newer, dataVersion=1)
        dialogs.clear()
        page.set_input_files("#restore-file", files=[{"name": "o.json", "mimeType": "application/json", "buffer": json.dumps(older).encode()}])
        page.wait_for_timeout(400)
        check("a backup from this version still restores", [m["name"] for m in stored(page, "mini-tracker-models")] == ["Future unit"],
              (dialogs, stored(page, "mini-tracker-models")))
        context.close()

        # ---------- 6. Label reader from the app's own folder ----------
        print("\n--- 6. Label reader ---")
        check("index.html no longer loads the reader from a CDN", "cdn.jsdelivr.net/npm/tesseract" not in html)
        check("sw.js no longer lists outside reader hosts", "jsdelivr" not in sw and "projectnaptha" not in sw)
        check("sw.js keeps ocr-worker.js with the app files", '"./ocr/ocr-worker.js"' in sw)
        for f in ["ocr-worker.js", "tesseract-core-simd-lstm.js", "tesseract-core-simd-lstm.wasm",
                  "tesseract-core-lstm.js", "tesseract-core-lstm.wasm", "eng.traineddata", "LICENSE-tesseract.txt", "README.md"]:
            check(f"ocr/{f} is in the repo", os.path.exists(os.path.join(ROOT, "ocr", f)))
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        outside = []
        context.on("request", lambda r: outside.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") and not r.url.startswith("blob:") else None)
        seed(page)
        page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller", timeout=10000)
        draw = """async (word) => {
          const c = document.createElement('canvas'); c.width = 700; c.height = 140;
          const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, 700, 140);
          g.fillStyle = '#000'; g.font = 'bold 64px Arial'; g.fillText(word, 30, 95);
          const w = await getOcrWorker(); const { data } = await w.recognize(c); return data.text; }"""
        text = page.evaluate(draw, "MACRAGGE BLUE")
        check("the self-hosted reader reads printed text", "MACRAGGE" in text.upper(), text)
        check("no request went to any outside website", not outside, outside[:5])
        cached = page.evaluate("""async () => { const c = await caches.open('shades-of-grey-label-reader');
                                    return (await c.keys()).map(r => new URL(r.url).pathname); }""")
        check("the engine and English data are saved for offline use",
              any(x.endswith("/ocr/eng.traineddata") for x in cached) and any(x.endswith(".wasm") for x in cached), cached)
        context.set_offline(True)
        page.evaluate("ocrWorker = null")   # start a fresh reader, as after reopening the app
        try:
            text = page.evaluate(draw, "NULN OIL")
        except Exception as error:
            text = str(error)
        check("with the internet off, a scan still reads", "NULN" in text.upper(), text)
        context.set_offline(False)
        page.click("nav button[data-tab='help']")
        page.evaluate("document.getElementById('about').open = true")
        about = page.inner_text("#about")
        check("About no longer says the scan downloads a tool from the web",
              "text-reading tool" not in about and "from the web" not in about, about)
        check("About still says your data stays on this device", "Your data stays on this device" in about)
        page.set_viewport_size({"width": 360, "height": 740})
        page.click("nav button[data-tab='recipes']")
        page.wait_for_timeout(150)
        check("no sideways scroll at 360px", page.evaluate("document.documentElement.scrollWidth <= 360"),
              page.evaluate("document.documentElement.scrollWidth"))
        context.close()

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
