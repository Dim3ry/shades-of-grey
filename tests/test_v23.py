"""v23 tests for Minifolio: unit panel order (roadmap section 4).

Checks:
1. Version numbers (plain numbers, "v23 or later"), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. The order in a unit's details: stage, (each model's stage), photos, recipes, paint notes, then the closed
   "Edit details" section, then the buttons. Same for a unit tracked model by model.
3. The fold: closed to start with; holds name, game, faction, nickname, models, repaint, track-each (and nothing
   else); opening it shows real boxes; real edits are saved; it stays open while you edit (every change redraws);
   closing the unit puts it away; each unit has its own; opening it saves nothing differently.
4. What still works: stage menu, back a stage, per-model stage, paint notes, Delete with Undo, Track each model
   on and off, Select mode, the tab bar hiding while typing in a folded box, the phone's Back button, the saved
   last tab, the Settings / Help / Updates switch.
5. Dark and light at 390 and 360 px: the heading is a 44 px target, text is readable, everything is on screen,
   nothing scrolls sideways.
6. Help and Updates wording.
7. No real browser pop-ups, no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

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
     "note": "blue armour", "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 4,
     "each": True, "stages": [4, 1, 3, 2], "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
    {"id": 3, "name": "Lieutenant", "hobby": "40K", "faction": "Ultramarines", "stage": 2, "count": 1,
     "log": [["2026-09-02", 2]]},
]
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
# v61: the "Track each model separately" tick left the fold. It is now a button under the stage
# (Track models separately / Track as one batch), so the fold has one label fewer.
FOLDED = ["Unit name", "Game", "Faction", "Nickname (optional)", "Models in unit", "Repaint project"]

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

def main_tab(page, name):
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def saved_unit(page, uid):
    return next(u for u in saved_units(page) if u["id"] == uid)

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(150)

def back(page):
    page.evaluate("history.back()")
    page.wait_for_timeout(250)

def card(uid):
    return f'#view-units li.unit[data-id="{uid}"]'

def open_unit(page, uid):
    info = f'{card(uid)} .info'
    # A3: open or shut now shows on the Details button (the name area is no longer a button with aria-expanded).
    if page.get_attribute(info.replace(" .info", " .details-toggle"), "aria-expanded") != "true":
        page.click(info)
        page.wait_for_timeout(250)

def fold(uid):
    return f'{card(uid)} .panel details.edit-details'

def fold_open(page, uid):
    return page.evaluate("(sel) => document.querySelector(sel).open", fold(uid))

def open_fold(page, uid):
    if not fold_open(page, uid):
        page.click(f'{fold(uid)} > summary')
        page.wait_for_timeout(200)

def order(page, uid):
    return page.evaluate("""(sel) => [...document.querySelector(sel).children].map(c =>
        c.matches('label') && c.querySelector('select.jump-stage') ? 'stage'
        : c.classList.contains('each-list') ? 'each'
        : c.classList.contains('gallery') ? 'photos'
        : c.classList.contains('panel-field') ? 'recipes'
        : c.matches('label') && c.querySelector('textarea') ? 'notes'
        : c.matches('details.edit-details') ? 'edit'
        : c.classList.contains('track-each') ? 'track'
        : c.classList.contains('panel-buttons') ? 'buttons' : '?')""", f"{card(uid)} .panel")

def folded_labels(page, uid):
    return page.evaluate("""(sel) => [...document.querySelector(sel).querySelectorAll('.edit-details-body label')]
        .map(l => l.firstChild.textContent.trim() || l.textContent.trim())""", f"{card(uid)} .panel")

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

def main():
    errors, csp, popups = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        seed(page)
        sw = read("sw.js")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        keys = page.evaluate("() => Object.keys(localStorage).sort()")

        # ---------- 2. The order ----------
        print("\n--- 2. The order of a unit's details ---")
        seed(page)
        open_unit(page, 1)
        check("batch unit: stage, photos, recipes, paint notes, Edit details, then the buttons",
              order(page, 1) == ["stage", "track", "photos", "recipes", "notes", "edit", "buttons"], order(page, 1))
        open_unit(page, 2)
        check("model-by-model unit: stage, each model's stage, photos, recipes, notes, Edit details, buttons",
              order(page, 2) == ["stage", "track", "each", "photos", "recipes", "notes", "edit", "buttons"], order(page, 2))
        open_unit(page, 3)
        check("a one-model unit has the same order as a batch unit, without the v61 Track button",
              order(page, 3) == ["stage", "photos", "recipes", "notes", "edit", "buttons"], order(page, 3))
        check("the fold holds the same boxes for a one-model unit (v61: no Track tick in it)", folded_labels(page, 3) == FOLDED, folded_labels(page, 3))
        top = page.evaluate("""(sel) => { const p = document.querySelector(sel);
            const y = (q) => p.querySelector(q).getBoundingClientRect().top;
            return [y('select.jump-stage'), y('.gallery'), y('.panel-field:not(.gallery)'), y('textarea'), y('details.edit-details')]; }""",
                            f"{card(1)} .panel")
        check("on screen they really run top to bottom in that order", top == sorted(top) and len(set(top)) == 5, top)

        # ---------- 3. The fold ----------
        print("\n--- 3. The Edit details fold ---")
        seed(page)
        before = json.dumps(saved_units(page), sort_keys=True)
        open_unit(page, 1)
        check("Edit details is closed to start with", not fold_open(page, 1))
        summary_text = page.inner_text(f"{fold(1)} > summary")
        check("it is clearly labelled 'Edit details'", summary_text.strip().startswith("Edit details"), summary_text)
        check("it holds name, game, faction, nickname, models, repaint and track-each, and nothing else",
              folded_labels(page, 1) == FOLDED, folded_labels(page, 1))
        check("stage menu, photos, recipes and paint notes are NOT inside the fold",
              page.evaluate("""(sel) => !document.querySelector(sel).querySelector('select.jump-stage, .gallery, textarea, .panel-field')""",
                            f"{fold(1)} .edit-details-body"))
        check("closed: the name box can't be seen",
              not page.locator(f'{fold(1)} .edit-details-body input').first.is_visible())
        page.click(f'{fold(1)} > summary')
        page.wait_for_timeout(200)
        check("one tap opens it", fold_open(page, 1))
        check("open: the name box shows 'Intercessors'",
              page.locator(f'{fold(1)} .edit-details-body input').first.is_visible()
              and page.locator(f'{fold(1)} .edit-details-body input').first.input_value() == "Intercessors")
        check("just opening and looking saved nothing differently", json.dumps(saved_units(page), sort_keys=True) == before)
        # Real edits.
        name_box = page.locator(f'{fold(1)} .edit-details-body input').first
        name_box.fill("Primaris Intercessors")
        page.keyboard.press("Tab")
        page.wait_for_timeout(250)
        check("renaming in the fold is saved", saved_unit(page, 1)["name"] == "Primaris Intercessors", saved_unit(page, 1))
        check("…and the fold is still open after the screen redrew", fold_open(page, 1))
        nick = page.locator(f'{fold(1)} label:has-text("Nickname") input')
        nick.fill("The Gold Squad")
        page.wait_for_timeout(150)
        check("a nickname is saved as you type", saved_unit(page, 1).get("nickname") == "The Gold Squad")
        page.keyboard.press("Tab")
        page.wait_for_timeout(250)
        check("…and the fold is still open after the nickname redraw", fold_open(page, 1))
        count = page.locator(f'{fold(1)} label:has-text("Models in unit") input')
        count.fill("6")
        page.keyboard.press("Tab")
        page.wait_for_timeout(250)
        check("the number of models is saved", saved_unit(page, 1)["count"] == 6, saved_unit(page, 1))
        page.locator(f'{fold(1)} label:has-text("Repaint project") input').click()
        page.wait_for_timeout(250)
        check("the repaint tick is saved and the fold stays open", saved_unit(page, 1).get("repaint") is True and fold_open(page, 1))
        game = page.locator(f'{fold(1)} label:has-text("Game") input')
        game.fill("Age of Sigmar")
        page.keyboard.press("Tab")
        page.wait_for_timeout(250)
        check("game is saved", saved_unit(page, 1)["hobby"] == "Age of Sigmar", saved_unit(page, 1)["hobby"])
        # One tap on the heading shuts it again; the unit's own tap puts it away.
        page.click(f'{fold(1)} > summary')
        page.wait_for_timeout(200)
        check("a tap on the heading shuts it", not fold_open(page, 1))
        page.click(f'{fold(1)} > summary')
        page.wait_for_timeout(200)
        open_unit(page, 2)
        check("each unit has its own fold: unit 2's is still closed", not fold_open(page, 2))
        page.click(f'{card(1)} .info')   # close unit 1
        page.wait_for_timeout(250)
        page.click(f'{card(1)} .info')   # open it again
        page.wait_for_timeout(250)
        check("closing a unit and opening it again finds the fold shut", not fold_open(page, 1))
        # Keyboard: Enter and Space on the heading.
        page.focus(f'{fold(1)} > summary')
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        check("Enter on the heading opens it", fold_open(page, 1))
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        check("Space on the heading shuts it", not fold_open(page, 1))

        # ---------- 4. What still works ----------
        print("\n--- 4. What still works ---")
        seed(page)
        open_unit(page, 1)
        page.select_option(f"{card(1)} select.jump-stage", "5")
        page.wait_for_timeout(250)
        check("jump to stage still works from the new top spot", saved_unit(page, 1)["stage"] == 5, saved_unit(page, 1)["stage"])
        open_unit(page, 1)
        # A3: the old "Back a stage" button at the bottom of the details is gone; the stepper's back arrow does this.
        page.click(f'{card(1)} .step-back')
        page.wait_for_timeout(250)
        open_unit(page, 1)
        check("the stepper's back arrow still moves a unit back a stage", saved_unit(page, 1)["stage"] == 4, saved_unit(page, 1)["stage"])
        note = page.locator(f"{card(1)} .panel textarea")
        check("the paint notes show what was saved", note.input_value() == "blue armour")
        note.fill("blue armour, gold trim")
        page.wait_for_timeout(800)
        check("paint notes still save as you type", saved_unit(page, 1)["note"] == "blue armour, gold trim")
        blur(page)
        open_unit(page, 2)
        first_before = saved_unit(page, 2)["stages"][0]
        page.locator(f"{card(2)} .each-list .each-up").nth(0).click()   # M2: the per-row menu is gone; the row's up button moves one model
        page.wait_for_timeout(250)
        open_unit(page, 2)
        check("a single model's own up button still works", saved_unit(page, 2)["stages"][0] == first_before + 1, saved_unit(page, 2)["stages"])
        check("the recipe menu is on show (no fold to open)",
              page.locator(f'{card(2)} .panel select[aria-label^="Link a recipe"]').is_visible())
        # Track each model on and off with real taps (v61: the button under the stage, not a tick in the fold).
        open_unit(page, 1)
        page.locator(f'{card(1)} .panel button.track-each').click()
        page.wait_for_timeout(300)
        open_unit(page, 1)
        check("Track each model separately switches on (each-list appears right under the stage)",
              saved_unit(page, 1).get("each") is True and order(page, 1)[:3] == ["stage", "track", "each"], order(page, 1))
        # The question only comes when the models are at different stages, so move one model up first.
        page.locator(f'{card(1)} .each-list .each-up').first.click()
        page.wait_for_timeout(300)
        open_unit(page, 1)
        page.locator(f'{card(1)} .panel button.track-each').click()
        page.wait_for_timeout(300)
        check("switching it off asks first (the app's own box)", page.is_visible("#dialog-backdrop:not(.hidden)") or page.locator("#dialog-yes").is_visible())
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("…and Yes puts the unit back to one stage", saved_unit(page, 1).get("each") in (False, None))
        # Delete with Undo.
        open_unit(page, 3)
        page.click(f'{card(3)} .panel-buttons .danger-button')
        page.wait_for_timeout(250)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        check("Delete still asks, and Yes removes the unit", all(u["id"] != 3 for u in saved_units(page)))
        check("the message has an Undo button", "Undo" in page.inner_text("#toast"), page.inner_text("#toast"))
        page.click("#toast button")
        page.wait_for_timeout(300)
        check("Undo brings the unit back", any(u["id"] == 3 for u in saved_units(page)))
        # Typing in a folded box hides the tab bar; Back; saved tab; the switch; Select.
        open_unit(page, 1)
        open_fold(page, 1)
        page.locator(f'{fold(1)} .edit-details-body input').first.click()
        page.wait_for_timeout(200)
        check("the tab bar hides while the cursor is in a folded box",
              page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display === 'none'"))
        blur(page)
        check("…and comes back when you tap away",
              page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display !== 'none'"))
        back(page)
        check("the phone's Back button still goes to the Dashboard", page.evaluate("() => settings.tab") == "dashboard",
              page.evaluate("() => settings.tab"))
        main_tab(page, "units")
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        check("the last tab used is still remembered", saved_settings(page).get("tab") == "units"
              and page.evaluate("() => settings.tab") == "units")
        main_tab(page, "settings")
        for name in ["updates", "help", "settings"]:
            sub_tab(page, name)
        check("the Settings / Help / Updates switch still works", page.evaluate("() => settings.tab") == "settings")
        main_tab(page, "units")
        page.click("#toggle-select")
        page.wait_for_timeout(250)
        check("Select mode still works: no panels, tick boxes instead",
              page.locator("#view-units .panel").count() == 0 and page.locator("#view-units .unit-tick").count() >= 3)
        page.click("#select-cancel")
        page.wait_for_timeout(200)

        # ---------- 5. Dark and light, 390 and 360 ----------
        print("\n--- 5. Dark and light at 390 and 360 px ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                seed(page, settings=full_settings(appearance=appearance))
                tag = f"{appearance}-{width}"
                open_unit(page, 2)
                st = page.evaluate("""(sel) => { const d = document.querySelector(sel + ' details.edit-details');
                    const s = d.querySelector('summary'), h = d.querySelector('.edit-details-hint');
                    const r = s.getBoundingClientRect(), cs = getComputedStyle(s), hc = getComputedStyle(h);
                    const bg = getComputedStyle(document.querySelector(sel)).backgroundColor;
                    return { h: r.height, l: r.left, r: r.right, vw: window.innerWidth, col: cs.color, hint: hc.color, bg,
                             hintFits: h.getBoundingClientRect().right <= r.right + 0.5 && h.getBoundingClientRect().left >= r.left - 0.5 }; }""",
                                 card(2))
                check(f"{tag}: the Edit details heading is at least 44 px tall", st["h"] >= 43.5, st["h"])
                check(f"{tag}: the heading is inside the screen", st["l"] >= 0 and st["r"] <= st["vw"] + 0.5, st)
                check(f"{tag}: the little hint fits inside the heading row", st["hintFits"], st)
                check(f"{tag}: heading text is easy to read (contrast 4.5 or more)", contrast(rgb(st["col"]), rgb(st["bg"])) >= 4.5,
                      (st["col"], st["bg"]))
                check(f"{tag}: hint text is easy to read (contrast 4.5 or more)", contrast(rgb(st["hint"]), rgb(st["bg"])) >= 4.5,
                      (st["hint"], st["bg"]))
                check(f"{tag}: closed, nothing scrolls sideways", no_sideways(page))
                if width == 390:
                    shot(page, f"v23-panel-closed-{appearance}-{width}.png")
                open_fold(page, 2)
                boxes = page.evaluate("""(sel) => [...document.querySelectorAll(sel + ' .edit-details-body input, ' + sel + ' .edit-details-body label')]
                    .map(e => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, h: r.height }; })""", fold(2))
                vw = page.evaluate("() => window.innerWidth")
                check(f"{tag}: open, every edit box is inside the screen", boxes and all(b["l"] >= 0 and b["r"] <= vw + 0.5 for b in boxes), boxes[:3])
                check(f"{tag}: open, text boxes are at least 40 px tall (as before)",
                      all(b["h"] >= 40 for b in page.evaluate("""(sel) => [...document.querySelectorAll(sel + ' .edit-details-body input:not([type=checkbox])')]
                          .map(e => ({ h: e.getBoundingClientRect().height }))""", fold(2))))
                check(f"{tag}: open, nothing scrolls sideways", no_sideways(page))
                if width == 390:
                    page.locator(f"{card(2)}").scroll_into_view_if_needed()
                    shot(page, f"v23-panel-open-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 6. Help and Updates ----------
        print("\n--- 6. Help and Updates wording ---")
        seed(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        page.click("summary:has-text('Adding and updating units')")
        page.wait_for_timeout(150)
        help_edit = page.inner_text("#help-edit-details")
        check("Help explains Edit details (what's in it, where it is, that it stays open while you edit)",
              all(w in help_edit for w in ["Edit details", "name", "faction", "nickname", "stays open"]), help_edit)   # v61: the Track tick left Edit details
        topic = page.evaluate("() => document.getElementById('help-edit-details').parentElement.textContent")
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
