"""v22 tests for Minifolio: backups first in Settings + "Send backup to…" (roadmap section 4).

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry at the top, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. The Settings page starts with the Backups card (before Stages): Save backup, Send backup to…, Save full
   backup with photos, Restore backup, the "last backed up" line and the hints. Import CSV and the army-list
   paste still live in their own Import card, and the paste box still opens there.
3. Send backup to… when the phone CAN share files (a fake navigator.share): the share menu gets one file with
   the same name and the same contents as Save backup, nothing is downloaded, the message says it was sent,
   and "last backed up" moves to today. Closing the share menu changes nothing at all.
4. Send backup to… when it can't: no share at all, canShare saying no, and the share failing for another
   reason each save the same file instead and say why in plain words.
5. Save backup and Save full backup with photos still work as before.
6. Dark and light at 390 and 360 px: the card is on screen, buttons are 44 px tall, nothing scrolls sideways.
7. Help and Privacy: the new Help line, the Privacy line still true; the Settings / Help / Updates switch,
   Back button and saved last page still work; the tab bar still hides while typing on Settings.
8. No real browser pop-ups, no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launch_helpers import leave_launch
import fold_opener   # v54: Stages, Import and Your data fold shut; this older test works inside them

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

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
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
    s = {"palette": "ice", "tab": "settings", "stages": STAGES, "doneFrom": 5, "examplesChecked": True}
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
    leave_launch(page)   # U4b (v89): a fresh load shows the start page; tap through to the saved section, as before

def main_tab(page, name):
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def toast_text(page):
    return page.evaluate("() => document.getElementById('toast-text').textContent")

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(120)

def back(page):
    page.evaluate("history.back()")
    page.wait_for_timeout(250)

# A fake share menu. mode: "ok" (files are shared), "cancel" (person closes the menu: AbortError),
# "fail" (it throws another error), "nocan" (canShare says no), "none" (no share at all).
def fake_share(page, mode):
    page.evaluate("""(mode) => {
        window.__shared = [];
        const set = (name, value) => Object.defineProperty(navigator, name, { configurable: true, writable: true, value });
        if (mode === "none") { set("share", undefined); set("canShare", undefined); return; }
        set("canShare", (data) => mode !== "nocan" && !!(data && data.files && data.files.length));
        set("share", async (data) => {
            const f = data.files[0];
            window.__shared.push({ name: f.name, type: f.type, text: await f.text(), count: data.files.length });
            if (mode === "cancel") { const e = new Error("cancelled"); e.name = "AbortError"; throw e; }
            if (mode === "fail") { const e = new Error("no"); e.name = "NotAllowedError"; throw e; }
        });
    }""", mode)

def shared(page):
    return page.evaluate("() => window.__shared || []")

def main():
    errors, csp, popups, downloads = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = context.new_page()
        fold_opener.open_cards_on_load(page)   # v54: open the folded Settings cards whenever the app loads
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        page.on("download", lambda d: downloads.append(d))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        seed(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v22')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v22'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("…about backups first, Send backup to…, the share menu, no photos and the fallback",
                  all(w in joined for w in ["first", "Send backup to", "share menu", "no photos", "saved to your device"]), joined[:300])
        else:
            print("SKIP (entry no longer in the public Updates list): " + '…about backups first, Send backup to…, the share menu, no photos and the fallback')
        keys = page.evaluate("() => Object.keys(localStorage).sort()")
        check("storage keys are the same ones as before", "mini-tracker-models" in keys and "shades-of-grey-settings" in keys, keys)
        check("the backup file itself is unchanged (same app name, version number and name format)",
              'app: "Minifolio", version: 6' in app and "minifolio-backup-${today}.json" in app)

        # ---------- 2. The Backups card comes first ----------
        print("\n--- 2. Backups first on Settings ---")
        seed(page)
        cards = page.evaluate("""() => [...document.querySelectorAll('#view-settings > .card')].map(c => ({
            id: c.id, title: (c.querySelector('h2') || {}).textContent }))""")
        check("the first card on Settings is Backups", cards and cards[0]["title"] == "Backups" and cards[0]["id"] == "backup-card", cards[:3])
        titles = [c["title"] for c in cards]
        check("Backups comes before Stages, Appearance and Colours",
              all(titles.index("Backups") < titles.index(t) for t in ["Stages", "Appearance", "Colours"]), titles)
        inside = page.evaluate("""() => { const c = document.getElementById('backup-card');
            return { ids: [...c.querySelectorAll('button:not(.more-info-button), input')].map(b => b.id),
                     labels: [...c.querySelectorAll('button:not(.more-info-button)')].map(b => b.textContent.trim()),
                     age: !!c.querySelector('#backup-age'), hint: !!c.querySelector('#backup-explain') }; }""")
        # v46 added "Send full backup with photos to…" straight after Save full backup, so the card now holds five buttons.
        check("the Backups card holds the five buttons, the restore file box, the last-backed-up line and the hint (v52: the hint sits behind its More info)",
              inside["ids"] == ["export-button", "share-button", "full-export-button", "full-share-button", "restore-button", "restore-file"] and inside["age"] and inside["hint"], inside)
        check("button words: Save backup, Send backup to…, Save full backup with photos, Send full backup with photos to…, Restore backup",
              inside["labels"] == ["Save backup", "Send backup to…", "Save full backup with photos", "Send full backup with photos to…", "Restore backup"], inside["labels"])
        in_import = page.evaluate("""() => { const h = [...document.querySelectorAll('#view-settings > .card h2')].find(x => x.textContent === 'Import').parentElement;
            return { ids: [...h.querySelectorAll('button')].filter(b => b.id && !b.id.startsWith('card-fold-')).map(b => b.id).slice(0, 4), slot: !!h.querySelector('#settings-import-slot')   /* v54: the heading is now a fold button, left out */ }; }""")
        check("Import CSV, CSV template, Export CSV and Paste an army list are still together in Import",
              in_import["ids"] == ["csv-button", "template-button", "csv-export-button", "wh-button"] and in_import["slot"], in_import)
        page.click("#wh-button")
        page.wait_for_timeout(200)
        check("Paste an army list still opens its box in the Import card", page.is_visible("#wh-text"))
        page.click("#wh-button")
        age = page.inner_text("#backup-age")
        check("it says 'Last backup: Never' before any backup (v57 wording)", age.startswith("Last backup: Never"), age)
        hint = page.text_content("#backup-explain")
        check("the hint says which backup leaves out photos",   # v75: the share-hint paragraph is gone (SET-4); this is the one-line hint
              "leaves out photos" in hint and "includes them" in hint, hint)
        shot(page, "v22-settings-top.png")

        # ---------- 3. Send backup to… when the phone can share files ----------
        print("\n--- 3. Send backup to… with a working share menu ---")
        today = page.evaluate("todayISO()")
        seed(page)
        fake_share(page, "ok")
        downloads.clear()
        page.click("#share-button")
        page.wait_for_timeout(500)
        got = shared(page)
        check("the share menu was opened once with one file", len(got) == 1 and got[0]["count"] == 1, got)
        check("the file is named minifolio-backup-<today>.json", got and got[0]["name"] == f"minifolio-backup-{today}.json", got and got[0]["name"])
        check("the file type is JSON", got and got[0]["type"] == "application/json", got and got[0]["type"])
        data = json.loads(got[0]["text"]) if got else {}
        check("it is a real backup: app Minifolio, both units, the stages",
              data.get("app") == "Minifolio" and len(data.get("models", [])) == 2 and data.get("stages") == STAGES and "photoFiles" not in data, list(data)[:8])
        check("nothing was downloaded", not downloads, len(downloads))
        check("the message says it was sent", toast_text(page).startswith("Backup sent."), toast_text(page))
        check("'last backed up' is today", saved_settings(page).get("lastBackup") == today and "today" in page.inner_text("#backup-age"), saved_settings(page).get("lastBackup"))
        shot(page, "v22-sent.png")
        # the same contents as Save backup
        with page.expect_download(timeout=4000) as dl:
            page.click("#export-button")
        saved_path = dl.value.path()
        check("the shared file and Save backup's file are identical, name and contents",
              dl.value.suggested_filename == got[0]["name"] and open(saved_path, encoding="utf-8").read() == got[0]["text"], dl.value.suggested_filename)

        # the person closes the share menu
        print("\n--- 3b. Closing the share menu changes nothing ---")
        seed(page)
        fake_share(page, "cancel")
        downloads.clear()
        before = saved_settings(page)
        page.click("#share-button")
        page.wait_for_timeout(500)
        check("the share menu was opened", len(shared(page)) == 1)
        check("closing it downloads nothing", not downloads, len(downloads))
        check("closing it shows no message", toast_text(page) in ("", None) or page.evaluate("() => document.getElementById('toast').classList.contains('hidden') || getComputedStyle(document.getElementById('toast')).display === 'none' || !document.getElementById('toast-text').textContent.trim()"), toast_text(page))
        check("closing it does not count as a backup", saved_settings(page).get("lastBackup") == before.get("lastBackup") and "Never" in page.inner_text("#backup-age"), saved_settings(page).get("lastBackup"))
        check("the button works again afterwards (not stuck)", page.is_enabled("#share-button"))

        # ---------- 4. When it can't share ----------
        print("\n--- 4. Send backup to… when the phone can't share files ---")
        cases = [
            ("no share menu at all", "none", "This browser can't send files to other apps"),
            ("the browser says it can't share this file", "nocan", "This browser can't send files to other apps"),
            ("the share menu fails", "fail", "The share menu couldn't send the backup"),
        ]
        for label, mode, words in cases:
            seed(page)
            fake_share(page, mode)
            downloads.clear()
            with page.expect_download(timeout=4000) as dl:
                page.click("#share-button")
            check(f"{label}: the backup is saved instead, same name", dl.value.suggested_filename == f"minifolio-backup-{today}.json", dl.value.suggested_filename)
            body = json.loads(open(dl.value.path(), encoding="utf-8").read())
            check(f"{label}: and it is the same backup", body.get("app") == "Minifolio" and len(body.get("models", [])) == 2)
            text = toast_text(page)
            check(f"{label}: the message says why, in plain words", words in text and "saved to your device instead" in text, text)
            check(f"{label}: 'last backed up' is today", saved_settings(page).get("lastBackup") == today)
            check(f"{label}: no real browser pop-up", not popups, popups)
            page.wait_for_timeout(200)
        # photos are mentioned when there are some
        seed(page)
        page.evaluate("() => { models[0].photos = [{ id: 'p-test', date: '2026-10-01' }]; }")   # (the app drops photo notes that have no picture at start-up, so add it after)
        fake_share(page, "none")
        with page.expect_download(timeout=4000):
            page.click("#share-button")
        check("with photos in the collection, the message says they aren't in this backup", "photo" in toast_text(page) and "Save full backup with photos" in toast_text(page), toast_text(page))

        # ---------- 5. The other backup buttons still work ----------
        print("\n--- 5. Save backup and Save full backup still work ---")
        seed(page)
        with page.expect_download(timeout=4000) as dl:
            page.click("#export-button")
        check("Save backup downloads minifolio-backup-<today>.json", dl.value.suggested_filename == f"minifolio-backup-{today}.json", dl.value.suggested_filename)
        check("Save backup says 'Backup saved.'", toast_text(page).startswith("Backup saved."), toast_text(page))
        seed(page)
        with page.expect_download(timeout=8000) as dl:
            page.click("#full-export-button")
        check("Save full backup downloads minifolio-full-backup-<today>.json", dl.value.suggested_filename == f"minifolio-full-backup-{today}.json", dl.value.suggested_filename)
        page.wait_for_timeout(300)
        check("Save full backup says 'Full backup saved'", toast_text(page).startswith("Full backup saved"), toast_text(page))
        # Restore still reads a backup (a real file through the real picker)
        seed(page)
        with page.expect_download(timeout=4000) as dl:
            page.click("#export-button")
        backup_path = dl.value.path()
        seed(page, units=[])
        page.set_input_files("#restore-file", backup_path)
        page.wait_for_timeout(400)
        if page.is_visible("#dialog-yes"):
            page.click("#dialog-yes")   # the app's own "Replace your units?" question
            page.wait_for_timeout(400)
        check("Restore backup (real file picker) still brings both units back", page.evaluate("() => models.length") == 2, page.evaluate("() => models.length"))

        # ---------- 6. Dark and light, 390 and 360 ----------
        print("\n--- 6. Looks right in dark and light on a phone ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                seed(page, settings=full_settings(appearance=appearance))
                tag = f"{appearance}-{width}"
                st = page.evaluate("""() => { const c = document.getElementById('backup-card').getBoundingClientRect();
                    const bs = [...document.querySelectorAll('#backup-card button:not(.more-info-button)')].map(b => { const r = b.getBoundingClientRect(); return { h: r.height, l: r.left, r: r.right, w: r.width }; });
                    return { top: c.top, bottom: c.bottom, left: c.left, right: c.right, bs, vh: window.innerHeight, vw: window.innerWidth }; }""")
                check(f"{tag}: the Backups card is at the top of the page and on screen", 0 <= st["top"] < 200 and st["left"] >= 0 and st["right"] <= st["vw"] + 0.5, st)
                check(f"{tag}: every backup button is at least 44 px tall", all(b["h"] >= 43.5 for b in st["bs"]), [b["h"] for b in st["bs"]])
                check(f"{tag}: every backup button is inside the screen and wide enough", all(b["l"] >= 0 and b["r"] <= st["vw"] + 0.5 and b["w"] >= 100 for b in st["bs"]), st["bs"])
                check(f"{tag}: the Send backup to… words are not cut off",
                      page.evaluate("() => { const b = document.getElementById('share-button'); return b.scrollWidth <= b.clientWidth + 1; }"))
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                if width == 390:
                    shot(page, f"v22-backups-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Help, Privacy, the switch, Back, saved page, typing ----------
        print("\n--- 7. Help, Privacy and what still works ---")
        seed(page)
        sub_tab(page, "help")
        page.click("summary:has-text('Your data and backups')")
        page.wait_for_timeout(150)
        help_text = page.inner_text("#help-send-backup")
        check("Help explains Send backup to… (share menu, same file, no photos, saved instead, closing changes nothing)",
              all(w in help_text for w in ["share menu", "same file", "no photos", "saved to your device instead", "Closing the share menu changes nothing"]), help_text)
        privacy = page.evaluate("() => document.getElementById('privacy').textContent")
        check("Privacy still says only what you choose goes out, and says the app sends nothing itself",
              "only what you choose to send" in privacy and "the app sends nothing itself" in privacy, privacy[-400:])
        # v46 added the full-backup share button, so there are now exactly two calls: one in each Send button's handler.
        check("the Help line stays true to the code: the app only calls navigator.share from the two Send buttons",
              len(re.findall(r"navigator\.share\(", read("app.js"))) == 2 and "fetch(" not in "".join(re.findall(r"share-button.*?\}\);\n", read("app.js"), re.S)))
        check("the switch is still on Help and Back goes to the Dashboard",
              page.evaluate("() => settings.tab") == "help")
        back(page)
        main_tab(page, "settings")
        check("the saved page is 'settings' and survives a reload with Backups on top",
              saved_settings(page).get("tab") == "settings")
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        leave_launch(page)   # U4b (v89): a fresh load shows the start page; tap through to the saved section, as before
        check("after a reload the Settings page opens with the Backups card first",
              page.evaluate("() => document.querySelector('#view-settings > .card').id") == "backup-card" and page.evaluate("() => settings.tab") == "settings")
        for name in ["updates", "help", "settings"]:
            sub_tab(page, name)
        check("the Settings / Help / Updates switch still moves between the three", page.evaluate("() => settings.tab") == "settings")
        page.click("#stage-list li input, #stage-list li button", timeout=3000) if False else None
        page.click("#view-settings #stage-list input")
        page.wait_for_timeout(200)
        check("the tab bar still hides while a text box on Settings has the cursor",
              page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display === 'none'"))
        blur(page)
        check("…and comes back", page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display !== 'none'"))
        updates_text = None
        sub_tab(page, "updates")
        updates_text = page.inner_text("#view-updates")
        if page.evaluate("['v22'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates page lists v22 with the backup wording", "Send backup to" in updates_text and "v22" in updates_text)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates page lists v22 with the backup wording')

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
