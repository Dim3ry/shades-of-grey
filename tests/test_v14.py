"""v14 tests for Shades of Grey (100 checks at phone and desktop size). Serve the repo folder with
`python3 -m http.server 8765`, then run: python3 tests/test_v14.py <folder for screenshots>."""
import json, sys, time, base64, datetime
from playwright.sync_api import sync_playwright
import os as _os
PORT = _os.environ.get("SOG_PORT", "8765")

URL = f"http://localhost:{PORT}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else "."
DEFAULT = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
           "Battle ready", "Painted with issues", "Parade ready"]

# Fake "storage full": when window.__quota is set, setItem throws once the total would pass it.
INIT = """
(() => {
  const realSet = Storage.prototype.setItem;
  window.__writes = 0;
  Storage.prototype.setItem = function (k, v) {
    window.__writes++;
    if (window.__quota != null) {
      let total = 0;
      for (let i = 0; i < this.length; i++) { const key = this.key(i); if (key !== k) total += key.length + this.getItem(key).length; }
      total += k.length + String(v).length;
      if (total > window.__quota) throw new DOMException("full", "QuotaExceededError");
    }
    return realSet.call(this, k, v);
  };
})();
"""

results, errors = [], []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def days_ago(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()

def units(n, stage, **extra):
    return [{"id": i + 1, "name": f"Unit {i+1}", "hobby": "40K", "faction": "Orks", "stage": stage, "count": 5,
             "log": [["2026-10-01", 0], ["2026-10-02", stage]], **extra} for i in range(n)]

def run(viewport, label):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=viewport)
        ctx.add_init_script(INIT)
        dialogs = []

        def new_page():
            page = ctx.new_page()
            page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
            page.on("pageerror", lambda e: errors.append(f"{label} pageerror: {e}"))
            page.on("console", lambda m: m.type == "error" and errors.append(f"{label} console: {m.text}"))
            return page

        page = new_page()

        def seed(data, settings=None, extra=None):
            # Same web address but no app running, so nothing can save over the seeded data.
            page.goto(f"http://localhost:{PORT}/manifest.json")
            page.evaluate("""([d, s, x]) => { localStorage.clear();
              localStorage.setItem('mini-tracker-models', JSON.stringify(d));
              if (s !== null) localStorage.setItem('shades-of-grey-settings', typeof s === 'string' ? s : JSON.stringify(s));
              for (const [k, v] of Object.entries(x || {})) localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v)); }""",
                          [data, settings, extra])
            page.goto(URL)
            page.wait_for_timeout(300)

        def stored(key="mini-tracker-models"):
            return page.evaluate("k => JSON.parse(localStorage.getItem(k) || 'null')", key)

        def fill_storage():   # quota = what's used now + a little, so any growth fails
            page.evaluate("""() => { let t = 0; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); t += k.length + localStorage.getItem(k).length; } window.__quota = t + 5; }""")

        base_settings = {"stages": DEFAULT, "doneFrom": 5, "palette": "ice", "tab": "settings", "lastBackup": days_ago(1),
                         "lastFullBackup": days_ago(1), "firstRealUse": days_ago(30), "lastReminder": days_ago(1)}

        # ---------- 1. CRITICAL: storage full during a stage edit ----------
        big = units(303, 7)
        seed(big, base_settings)
        fill_storage()
        dialogs.clear()
        page.evaluate("() => { draft.push({ name: 'Varnished', from: null }); renderStageEditor(); }")
        page.click("#save-stages")
        page.wait_for_timeout(200)
        check(f"{label} 1a stage edit with full storage shows a message", any("full" in d for d in dialogs), dialogs)
        s = stored("shades-of-grey-settings")
        check(f"{label} 1b stage list in storage unchanged", s["stages"] == DEFAULT, s["stages"])
        check(f"{label} 1c screen kept the old stages", page.evaluate("STAGES.length") == 8)
        page.reload(); page.wait_for_timeout(300)
        m = stored()
        check(f"{label} 1d after reopening, all 303 units still Parade ready",
              len(m) == 303 and all(u["stage"] == 7 for u in m) and all(len(u["log"]) == 2 for u in m))

        # Restore with full storage: a backup with DIFFERENT stages
        backup = {"app": "Shades of Grey", "version": 6, "stages": ["Grey", "Done"], "doneFrom": 1,
                  "models": units(400, 1, note="a longer note so this backup is bigger than what's stored"), "recipes": {"recipes": []}}
        fill_storage()
        dialogs.clear()
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_timeout(500)
        page.reload(); page.wait_for_timeout(300)
        m = stored(); s = stored("shades-of-grey-settings")
        check(f"{label} 1e restore with full storage changes nothing", len(m) == 303 and s["stages"] == DEFAULT and all(u["stage"] == 7 for u in m),
              (len(m), s["stages"]))
        check(f"{label} 1f restore with full storage explained", any("full" in d for d in dialogs), dialogs)

        # ---------- 8. Photo stage labels follow a stage edit (no quota) ----------
        seed([{"id": 1, "name": "Captain", "hobby": "40K", "faction": "Ultramarines", "stage": 5, "count": 1,
               "log": [["2026-10-01", 5]], "photos": [{"id": "p1", "stage": 3, "date": "2026-10-01"}, {"id": "p2", "stage": 5}]}], base_settings)
        page.evaluate("""async () => { const b = new Blob(['x'], { type: 'image/jpeg' });
          await putPhoto({ id: 'p1', full: b, thumb: b }); await putPhoto({ id: 'p2', full: b, thumb: b }); }""")
        page.evaluate("""() => { const u = JSON.parse(localStorage.getItem('mini-tracker-models'));
          u[0].photos = [{ id: 'p1', stage: 3, date: '2026-10-01' }, { id: 'p2', stage: 5 }];
          localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""")
        page.reload(); page.wait_for_timeout(400)
        dialogs.clear()
        page.evaluate("() => { draft.splice(1, 1); renderStageEditor(); }")   # remove "Part assembled"
        page.click("#save-stages")
        page.wait_for_timeout(200)
        m = stored()
        check(f"{label} 8 photo stages remapped (3->2, 5->4)", [p.get("stage") for p in m[0]["photos"]] == [2, 4] and m[0]["stage"] == 4,
              m[0])

        # ---------- 4. Banner stays while saving fails ----------
        seed(units(3, 0), base_settings)
        fill_storage()
        page.evaluate("() => { addModel({ name: 'Extra one', hobby: '40K', faction: 'Orks' }); render(); }")
        check(f"{label} 4a red banner shows when a save fails", page.is_visible("#save-banner"))
        page.evaluate("() => { addModel({ name: 'Extra two', hobby: '40K', faction: 'Orks' }); render(); }")
        check(f"{label} 4b banner still showing after another failed save", page.is_visible("#save-banner"))
        page.screenshot(path=f"{SHOTS}/{label}-banner.png")
        page.evaluate("() => { window.__quota = null; }")
        page.click("#banner-retry")
        page.wait_for_timeout(100)
        check(f"{label} 4c Try again saves and hides the banner", not page.is_visible("#save-banner") and len(stored()) == 5, (page.is_visible("#save-banner"), len(stored()), dialogs[-2:]))

        # ---------- 3. Delete all ----------
        seed(units(4, 2), base_settings)
        fill_storage()
        dialogs.clear()
        page.click("#delete-all")
        page.wait_for_timeout(100)
        check(f"{label} 3a Delete all stops when no room for a safety copy",
              len(stored()) == 4 and page.evaluate("models.length") == 4 and any("nothing has been deleted" in d for d in dialogs), dialogs)
        page.evaluate("() => { window.__quota = null; }")
        page.click("#delete-all")
        page.wait_for_timeout(100)
        check(f"{label} 3b Delete all deletes and shows Undo", len(stored()) == 0 and page.is_visible("#toast-undo")
              and "Deleted 4 units" in page.inner_text("#toast-text"))
        page.click("#toast-undo")
        check(f"{label} 3c Undo brings all 4 back", len(stored()) == 4)
        page.click("#delete-all"); page.wait_for_timeout(100)
        copy = stored("mini-tracker-models-before-delete-all")
        check(f"{label} 3d safety copy holds date and stages", copy.get("date") and copy.get("stages") == DEFAULT and len(copy["models"]) == 4)
        page.evaluate("renderSettings()")
        check(f"{label} 3e Recover earlier data lists the copy", page.is_visible("#recover-card") and "Before Delete all units: 4 units" in page.inner_text("#recover-list"))
        page.locator("#recover-card").scroll_into_view_if_needed()
        page.screenshot(path=f"{SHOTS}/{label}-recover.png")
        page.click("#recover-list button")
        page.wait_for_timeout(200)
        check(f"{label} 3f Recover brings the 4 units back", len(stored()) == 4 and page.evaluate("models.length") == 4)
        # Expiry: a copy 40 days old goes; an old-style (list) copy gets dated
        old_copy = {"date": days_ago(40), "stages": DEFAULT, "doneFrom": 5, "models": units(2, 1)}
        seed(units(1, 0), base_settings, {"mini-tracker-models-before-delete-all": old_copy, "mini-tracker-models-before-replace": units(3, 1)})
        check(f"{label} 3g 40-day-old copy removed at start-up", stored("mini-tracker-models-before-delete-all") is None)
        rc = stored("mini-tracker-models-before-replace")
        check(f"{label} 3h pre-v14 copy kept and given today's date", isinstance(rc, dict) and rc.get("date") == datetime.date.today().isoformat() and len(rc["models"]) == 3, rc)

        # ---------- 2. Two windows ----------
        seed(units(2, 0), base_settings)
        page2 = new_page()
        page2.goto(URL); page2.wait_for_timeout(300)
        page.evaluate("() => { addModel({ name: 'From window A', hobby: '40K', faction: 'Orks' }); render(); }")
        page2.wait_for_timeout(600)
        check(f"{label} 2a other window shows the new unit without reloading",
              page2.evaluate("models.some(m => m.name === 'From window A')") and "another window" in page2.inner_text("#toast-text"))
        page2.evaluate("() => { addModel({ name: 'From window B', hobby: '40K', faction: 'Orks' }); render(); }")
        page.wait_for_timeout(600)
        names = [u["name"] for u in stored()]
        check(f"{label} 2b both windows' units kept", "From window A" in names and "From window B" in names and len(names) == 4, names)
        page.evaluate("window.__writes = 0"); page2.evaluate("window.__writes = 0")
        page.wait_for_timeout(1500)
        check(f"{label} 2c windows settle (no saving back and forth)", page.evaluate("window.__writes") + page2.evaluate("window.__writes") == 0)
        # switching tab in one window doesn't reload the other
        page2.evaluate("() => { document.getElementById('toast').classList.add('hidden'); }")
        page.click('nav button[data-tab="units"]'); page2.wait_for_timeout(500)
        check(f"{label} 2d a tab switch in one window doesn't disturb the other", not page2.is_visible("#toast"))
        page2.close()
        # Clean up reads the saved list, so a photo just added elsewhere isn't "spare"
        orphan = page.evaluate("""async () => {
          const blob = new Blob(['x'], { type: 'image/jpeg' });
          await putPhoto({ id: 'other-window-photo', full: blob, thumb: blob });
          await putPhoto({ id: 'real-orphan', full: blob, thumb: blob });
          const saved = JSON.parse(localStorage.getItem('mini-tracker-models'));
          saved[0].photos = [{ id: 'other-window-photo' }];
          Storage.prototype.setItem.call(localStorage, 'mini-tracker-models', JSON.stringify(saved));
          const r = await photoStoreReport();
          return r.orphans; }""")
        check(f"{label} 2e clean-up keeps a photo another window just added", "real-orphan" in orphan and "other-window-photo" not in orphan, orphan)

        # ---------- 6. Special faction names and huge counts ----------
        weird = ["constructor", "toString", "__proto__", "hasOwnProperty", "valueOf"]
        seed([{"id": i + 1, "name": f"Squad {i}", "hobby": "40K", "faction": f, "stage": 1, "count": 3} for i, f in enumerate(weird)]
             + [{"id": 9, "name": "Horde", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 150000}],
             {**base_settings, "tab": "units"})
        cards = page.locator("#units-list > *").count() if page.locator("#units-list").count() else -1
        names_shown = page.inner_text("#view-units")
        check(f"{label} 6a units list shows all special-faction units",
              all(f"Squad {i}" in names_shown for i in range(5)) and "Horde" in names_shown, names_shown[:200])
        check(f"{label} 6b 150,000 models capped to 999", page.evaluate("models.find(m => m.name === 'Horde').count") == 999)
        page.evaluate("() => { setFactionColour('constructor', '#ff0000'); setFactionColour('__proto__', '#00ff00'); }")
        page.reload(); page.wait_for_timeout(300)
        shown = page.inner_text("#view-units")
        check(f"{label} 6c colours on special names survive a reopen",
              page.evaluate("factionColour('constructor')") == "#ff0000" and page.evaluate("factionColour('__proto__')") == "#00ff00"
              and page.evaluate("factionColour('toString')") == "" and "Squad 2" in shown)
        page.screenshot(path=f"{SHOTS}/{label}-special-factions.png")
        # restoring a backup with such colours
        bk = {"app": "Shades of Grey", "version": 6, "stages": DEFAULT, "doneFrom": 5, "models": units(1, 1, faction="constructor"),
              "factionColours": {"constructor": "#123456", "toString": "not a colour"}}
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(bk).encode()}])
        page.wait_for_timeout(500)
        check(f"{label} 6d backup with special faction restores", page.evaluate("factionColour('constructor')") == "#123456" and len(stored()) == 1)
        page.evaluate("() => { const m = models[0]; setEach(m, true); }")
        dialogs.clear()
        page.evaluate("() => { const m = models[0]; delete m.each; delete m.stages; m.count = 150; setEach(m, true); }")
        check(f"{label} 6e track-each refused above 100 models", any("up to 100" in d for d in dialogs) and not page.evaluate("models[0].each"))

        # ---------- 7. Unreadable settings ----------
        seed(units(3, 7), "{this is not json")
        check(f"{label} 7a unreadable settings copied aside", page.evaluate("localStorage.getItem('shades-of-grey-settings-unreadable')") == "{this is not json")
        check(f"{label} 7b units keep stage 7 (8 stages chosen)", page.evaluate("STAGES.length") == 8 and all(u["stage"] == 7 for u in stored()) and all(len(u["log"]) == 2 for u in stored()))
        check(f"{label} 7c message shown", "settings couldn't be read" in page.inner_text("#toast-text"))
        seed(units(3, 9), None)   # no settings at all, units on stage 10
        check(f"{label} 7d no settings: stage list grows to fit stage 10", page.evaluate("STAGES.length") == 10 and all(u["stage"] == 9 for u in stored()))
        seed(units(3, 3), None)   # very old data: original 5 stages
        check(f"{label} 7e very old data still gets the original 5 stages", page.evaluate("STAGES.join()") == "Unbuilt,Built,Primed,In progress,Painted")

        # ---------- 5 / 10. Restore checks ----------
        seed(units(2, 1), base_settings)
        tiny_png = "data:image/png;base64," + base64.b64encode(bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360f8cf000000030101006ad1c5b20000000049454e44ae426082")).decode()
        full = {"app": "Shades of Grey", "version": 6, "stages": DEFAULT, "doneFrom": 5,
                "models": [{"id": 1, "name": "Pics", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 1,
                            "photos": [{"id": "good"}, {"id": "bad"}]}],
                "photoFiles": {"good": {"full": tiny_png, "thumb": tiny_png}, "bad": {"full": "data:image/jpeg;base64,!!!!", "thumb": "x"}}}
        dialogs.clear()
        page.set_input_files("#restore-file", files=[{"name": "f.json", "mimeType": "application/json", "buffer": json.dumps(full).encode()}])
        page.wait_for_timeout(1500)
        check(f"{label} 5 restore warns 1 of 2 photos couldn't be loaded", any("1 of 2 photos couldn't be loaded" in d for d in dialogs), dialogs)
        # recipes-only
        seed(units(2, 1), base_settings)
        ronly = {"app": "Shades of Grey", "version": 6, "models": [],
                 "recipes": {"paints": [{"id": 1, "name": "Blue", "brand": "", "colour": "#0000ff"}],
                             "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "steps": [{"technique": "Base coat", "coats": 1, "paints": [{"paint": 1, "mix": None}]}]}]}}
        page.set_input_files("#restore-file", files=[{"name": "r.json", "mimeType": "application/json", "buffer": json.dumps(ronly).encode()}])
        page.wait_for_timeout(500)
        rb = stored("shades-of-grey-recipes")
        check(f"{label} 10a recipes-only backup restores recipes, units untouched",
              len(stored()) == 2 and [r["name"] for r in rb["recipes"]] == ["Blue armour"] and "Recipes restored" in page.inner_text("#toast-text"),
              (len(stored()), rb, page.inner_text("#toast-text"), dialogs[-2:]))
        for name, stages in [("duplicate", ["A", "a", "B"]), ("43 stages", [f"S{i}" for i in range(43)]), ("null", None), ("object", {}), ("blank", ["A", " "])]:
            dialogs.clear()
            bad = {"app": "Shades of Grey", "version": 6, "stages": stages, "doneFrom": 1, "models": units(7, 0)}
            page.set_input_files("#restore-file", files=[{"name": "x.json", "mimeType": "application/json", "buffer": json.dumps(bad).encode()}])
            page.wait_for_timeout(300)
            check(f"{label} 10b broken stages ({name}) refused", len(stored()) == 2 and any("damaged" in d for d in dialogs), dialogs)
        dialogs.clear()
        page.set_input_files("#restore-file", files=[{"name": "x.json", "mimeType": "application/json", "buffer": b'{"hello": 1}'}])
        page.wait_for_timeout(300)
        check(f"{label} 10c a random file is refused", any("doesn't look like" in d for d in dialogs) and len(stored()) == 2)

        # ---------- 9. Backup messages, reminder, iPhone card ----------
        seed(units(12, 1), base_settings)
        with page.expect_download():
            page.click("#export-button")
        check(f"{label} 9a Save backup shows a message", "Backup saved" in page.inner_text("#toast-text"))
        withphotos = units(12, 1); withphotos[0]["photos"] = [{"id": "zz"}]
        seed(withphotos, {**base_settings, "tab": "dashboard", "lastBackup": days_ago(1), "lastFullBackup": days_ago(9), "lastReminder": days_ago(5)})
        page.evaluate("() => { thumbUrls.set('zz', 'data:,'); maybeRemindToBackUp(); }")
        check(f"{label} 9b reminder is about photos when the photo backup is old", "with photos" in page.inner_text("#toast-text"), page.inner_text("#toast-text"))
        check(f"{label} 9c iPhone card hidden on a normal browser", not page.is_visible("#iphone-warning"))

        # ---------- 11. Fan-tool basics ----------
        seed(units(1, 0), base_settings)
        check(f"{label} 11a import button says Paste an army list", page.inner_text("#wh-button") == "Paste an army list")
        page.click('nav button[data-tab="help"]')
        page.click("#about summary")
        about = page.inner_text("#about")
        check(f"{label} 11b About has the fan-tool notice and contact", "Unofficial fan-made" in about and "not affiliated with or endorsed by Games Workshop" in about and "Contact" in about)
        page.locator("#about").scroll_into_view_if_needed()
        page.screenshot(path=f"{SHOTS}/{label}-about.png")
        page.click('nav button[data-tab="settings"]')
        page.click("#wh-button")
        army = ("Test list (500 points)\n\nOrks\nStrike Force (2000 points)\n\nWarboss (75 points)\n  • 1x Big choppa\n\n"
                "Boyz (170 points)\n  • 1x Boss Nob\n    • 1x Slugga\n  • 19x Boy\n    • 19x Choppa\n\nExported with App Version: v1.0")
        page.fill("#wh-text", army)
        page.click("#wh-read")
        page.click("#review-go")
        page.wait_for_timeout(200)
        raw = page.evaluate("localStorage.getItem('mini-tracker-models')")
        boyz = [u for u in json.loads(raw) if u["name"] == "Boyz"]
        check(f"{label} 11c army list imported (Boyz x20, Warboss)", boyz and boyz[0]["count"] == 20 and "Warboss" in raw)
        check(f"{label} 11d no points stored anywhere", "points" not in raw.lower() and "170" not in raw and "75" not in raw.replace("2026", ""))

        page.close()
        # iPhone: a context pretending to be Safari on iPhone
        ictx = browser.new_context(viewport=viewport, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        ip = ictx.new_page()
        ip.on("pageerror", lambda e: errors.append(f"{label} iphone pageerror: {e}"))
        ip.goto(URL); ip.wait_for_timeout(300)
        check(f"{label} 9d iPhone in Safari sees the Home Screen card", ip.is_visible("#iphone-warning"))
        ip.screenshot(path=f"{SHOTS}/{label}-iphone.png")
        ip.click("#iphone-warning-ok")
        ip.reload(); ip.wait_for_timeout(300)
        check(f"{label} 9e Got it hides the card", not ip.is_visible("#iphone-warning"))
        ictx.close()
        browser.close()

run({"width": 390, "height": 844}, "phone")
run({"width": 1300, "height": 900}, "desktop")
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)} of {len(results)} passed")
real_errors = [e for e in errors if "favicon" not in e]
print("Console/page errors:", real_errors or "none")
sys.exit(0 if not fails and not real_errors else 1)
