"""v21 tests for Minifolio: the "These are examples" card, jump to stage, starting stage, tap targets.

Checks:
1. Version numbers, the Updates entry, CNAME and the ocr folder kept, storage names and the data
   version unchanged (still 1).
2. Examples card: a first visit gets 3 marked example units and the card on the Dashboard and Units.
   Clear examples removes ONLY those (your own units stay), with Undo that puts them back in place;
   it all survives a reload. Keep them unmarks them for good. Example units saved before v21 are
   recognised once (not ones you've changed). Renaming an example makes it yours.
3. Jump to stage: the Stage menu in a unit's details moves it straight there, with Undo (diary
   included); survives a reload. Units tracked model by model: each model's own menu, and "Move all
   models to stage" (shows "Mixed stages" while they differ). Starting stage in the Add form.
4. Tap targets at phone width (390 and 360 px): per-model ◀ ▲ and menus, the stage editor's ↑ ↓ ✕,
   "+ Mix in another paint", Help topic titles and the new menus/buttons: all ≥ 44 px.
5. Help, Back button unchanged (no new overlays), no sideways scroll, screenshots, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
import fold_opener   # v54: Stages, Import and Your data fold shut; this older test works inside them
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

STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
OLD_EXAMPLES = [  # how the 3 example units were saved before v21 (no "example" mark)
    {"id": 1, "name": "Captain", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 1},
    {"id": 2, "name": "Boyz", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 10},
    {"id": 3, "name": "Liberators", "hobby": "Age of Sigmar", "faction": "Stormcast Eternals", "stage": 6, "count": 5},
]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 0, "count": 5,
     "log": [["2026-09-01", 0]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 1, "count": 4, "each": True,
     "stages": [1, 1, 2, 3], "log": [["2026-09-01", 1]]},
]

def seed(page, units=UNITS, settings=None, fresh=False):
    page.goto(URL)
    page.evaluate("""([u, s, fresh]) => { localStorage.clear();
        if (!fresh) localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings, fresh])
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
    page.wait_for_timeout(80)

def units(page):
    return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))

def saved_settings(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings') || '{}'"))

def toast(page):
    return page.inner_text("#toast-text") if page.is_visible("#toast") else ""

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(120)

def open_unit(page, unit_id):
    page.click(f'#view-units li.unit[data-id="{unit_id}"] .info')
    page.wait_for_timeout(100)

def card(page, unit_id):
    return f'#view-units li.unit[data-id="{unit_id}"]'

def shot(page, name, full=True):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def sizes(page, selector):
    """Width and height of every VISIBLE element matching the selector."""
    return page.evaluate("""(sel) => [...document.querySelectorAll(sel)]
        .filter(e => e.offsetParent !== null)
        .map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10, (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 30)]; })""", selector)

def all_big(found, need_width=True):
    return bool(found) and all(h >= 44 and (w >= 44 or not need_width) for w, h, _ in found)

def shown(page, element_id):
    """True if the element isn't hidden (works whichever tab is open)."""
    return page.evaluate("(id) => !document.getElementById(id).classList.contains('hidden')", element_id)

def no_sideways(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def main():
    sw = read("sw.js")
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        fold_opener.open_cards_on_load(page)   # v54: open the folded Settings cards whenever the app loads
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        DialogAnswers(page)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page, settings=full_settings())
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21 or later", float(version[1:]) >= 21, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        entry = [i for i, h in enumerate(heads) if h.startswith("v21") and not h.startswith("v21.")]
        if page.evaluate("['v21'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab has a v21 entry", bool(entry), heads[:3])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab has a v21 entry')
        if entry:
            text = page.locator("#changelog .release").nth(entry[0]).inner_text()
            check("the v21 entry mentions examples, jump to a stage, Starting stage and 44 pixels",
                  all(w in text for w in ["Clear examples", "jump straight to a stage", "Starting stage", "44 pixels"]), text[:300])
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("the ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm", "README.md"]))
        check("the data version is still 1", page.evaluate("DATA_VERSION") == 1)
        check("storage names unchanged", all(k in html for k in
              ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes", "shades-of-grey-photos"]))

        # ---------- 2. Examples card ----------
        print("--- 2. Examples card ---")
        seed(page, fresh=True)   # a first ever visit: nothing saved
        saved = units(page)
        check("a first visit saves the 3 example units, each marked as an example",
              [u["name"] for u in saved] == ["Captain", "Brutes", "Guardians"] and all(u.get("example") is True for u in saved), saved)
        check("the examples card shows on the Dashboard", page.is_visible("#examples-card-dash"))
        dash_text = page.locator("#examples-card-dash").text_content()   # v52: the names sit behind More info
        check("…saying they're examples and naming them", "These are examples" in dash_text and
              all(n in dash_text for n in ["Captain", "Brutes", "Guardians"]), dash_text)
        check("…with Clear examples and Keep them", page.is_visible("#examples-card-dash .clear-examples")
              and page.inner_text("#examples-card-dash .keep-examples") == "Keep them")
        shot(page, "v21-examples-card-dashboard.png")
        tab(page, "units")
        check("the examples card shows on the Units tab too", page.is_visible("#examples-card"))
        shot(page, "v21-examples-card-units.png")
        check("examplesChecked is saved, so old-style recognition only runs once", saved_settings(page).get("examplesChecked") is True)

        # Add one of your own, then clear the examples: only the examples go.
        page.click("#toggle-add")
        page.fill("#name-input", "Hormagaunts")
        page.fill("#hobby-input", "40K")
        page.fill("#faction-input", "Tyranids")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(150)
        page.click("#toggle-add")
        check("the card stays while examples are still there", page.is_visible("#examples-card"))
        page.click("#examples-card .clear-examples")
        page.wait_for_timeout(150)
        after = units(page)
        check("Clear examples removes only the 3 examples; your own unit stays",
              [u["name"] for u in after] == ["Hormagaunts"], [u["name"] for u in after])
        check("…the card goes from both tabs", not page.is_visible("#examples-card") and
              page.evaluate("document.getElementById('examples-card-dash').classList.contains('hidden')"))
        check("…the message says so, with Undo", "Cleared 3 example units" in toast(page) and page.is_visible("#toast-undo"), toast(page))
        undo(page)
        back = units(page)
        check("Undo puts the 3 examples back, in their old places, still marked",
              [u["name"] for u in back] == ["Captain", "Brutes", "Guardians", "Hormagaunts"] and
              all(u.get("example") is True for u in back[:3]) and "example" not in back[3], [u["name"] for u in back])
        check("…and the card is back", page.is_visible("#examples-card"))
        page.reload(); page.wait_for_timeout(300)
        check("after a reload the examples and the card are still there",
              len(units(page)) == 4 and shown(page, "examples-card-dash"))
        tab(page, "dashboard")
        page.click("#examples-card-dash .clear-examples")
        page.wait_for_timeout(150)
        page.reload(); page.wait_for_timeout(300)
        check("a clear survives a reload (and the examples don't come back)",
              [u["name"] for u in units(page)] == ["Hormagaunts"] and not page.is_visible("#examples-card-dash"))

        # Keep them.
        seed(page, fresh=True)
        page.click("#examples-card-dash .keep-examples")
        page.wait_for_timeout(150)
        check("Keep them unmarks all 3 and hides the card", all("example" not in u for u in units(page))
              and len(units(page)) == 3 and not page.is_visible("#examples-card-dash"))
        check("…with a message and Undo", "Kept" in toast(page) and page.is_visible("#toast-undo"), toast(page))
        undo(page)
        check("Undo marks them as examples again", all(u.get("example") is True for u in units(page)) and page.is_visible("#examples-card-dash"))
        page.click("#examples-card-dash .keep-examples")
        page.wait_for_timeout(150)
        page.reload(); page.wait_for_timeout(300)
        check("kept examples stay unmarked after a reload (not recognised again)",
              all("example" not in u for u in units(page)) and not page.is_visible("#examples-card-dash"))

        # Examples saved before v21 (no mark).
        changed = [dict(OLD_EXAMPLES[0]), dict(OLD_EXAMPLES[1], nickname="Da Boyz"), dict(OLD_EXAMPLES[2], recipes=[])]
        seed(page, units=OLD_EXAMPLES, settings=full_settings())
        check("examples saved before v21 are recognised and marked", all(u.get("example") is True for u in units(page))
              and page.is_visible("#examples-card-dash"))
        seed(page, units=[dict(OLD_EXAMPLES[0], name="Chapter Master")] + changed[1:], settings=full_settings())
        marks = [u.get("example") is True for u in units(page)]
        check("…but not ones you've renamed or given a nickname", marks[:2] == [False, False], marks)
        seed(page, units=OLD_EXAMPLES, settings=full_settings(examplesChecked=True))
        check("…and only once (examplesChecked already set: no marks)", not any(u.get("example") for u in units(page)))
        seed(page, units=[dict(OLD_EXAMPLES[0], example="yes")], settings=full_settings(examplesChecked=True))
        check("an 'example' value that isn't a real true is dropped", "example" not in units(page)[0])

        # Renaming an example makes it yours.
        seed(page, fresh=True)
        tab(page, "units")
        open_unit(page, 1)
        # v23: the edit boxes are folded under "Edit details"; open it first, like a real user.
        page.locator(f'{card(page, 1)} .panel details.edit-details > summary').click()
        name_box = page.locator(f'{card(page, 1)} .panel .edit-details-body input').first
        name_box.fill("Lieutenant")
        name_box.dispatch_event("change")
        page.wait_for_timeout(150)
        saved = {u["id"]: u for u in units(page)}
        check("renaming an example makes it yours (unmarked); the others stay examples",
              "example" not in saved[1] and saved[2].get("example") and saved[3].get("example"))
        check("…and the card now lists 2", "2 example units" in page.locator("#examples-card").text_content(), page.locator("#examples-card").text_content())

        # ---------- 3. Jump to stage ----------
        print("--- 3. Jump to stage ---")
        seed(page, settings=full_settings())
        tab(page, "units")
        open_unit(page, 1)
        menu = f"{card(page, 1)} select.jump-stage"
        options = page.locator(f"{menu} option").all_inner_texts()
        check("a unit's details have a Stage menu listing every stage", options == STAGES, options)
        check("…showing its current stage", page.input_value(menu) == "0")
        log_before = units(page)[0]["log"]
        page.select_option(menu, "5")
        page.wait_for_timeout(150)
        u = units(page)[0]
        check("picking Battle ready moves it straight there (one step, not five taps)", u["stage"] == 5, u)
        check("…the diary notes it", u["log"][-1][1] == 5, u["log"])
        check("…the card shows the new stage", "Battle ready" in page.inner_text(f"{card(page, 1)} .stage"))
        check("…and the message says so, with Undo", "Intercessors → Battle ready" in toast(page) and page.is_visible("#toast-undo"), toast(page))
        shot(page, "v21-jump-to-stage.png")
        undo(page)
        u = units(page)[0]
        check("Undo puts the stage AND the diary back exactly", u["stage"] == 0 and u["log"] == log_before, u)
        page.select_option(f"{card(page, 1)} select.jump-stage", "3")
        page.wait_for_timeout(150)
        page.select_option(f"{card(page, 1)} select.jump-stage", "1")   # jumping backwards works too
        page.wait_for_timeout(150)
        check("jumping backwards works too", units(page)[0]["stage"] == 1)
        page.reload(); page.wait_for_timeout(300)
        check("the jumped stage survives a reload", units(page)[0]["stage"] == 1)

        # Each model tracked separately.
        tab(page, "units")
        open_unit(page, 2)
        all_menu = f"{card(page, 2)} select.jump-stage"
        check("a model-by-model unit's menu says Mixed stages while they differ",
              page.evaluate(f"document.querySelector('{all_menu}').selectedOptions[0].textContent") == "Mixed stages")
        each_menus = page.locator(f"{card(page, 2)} .each-list select")
        check("each model has its own stage menu", each_menus.count() == 4 and
              [each_menus.nth(i).input_value() for i in range(4)] == ["1", "1", "2", "3"])
        each_menus.nth(1).select_option("6")
        page.wait_for_timeout(150)
        u = units(page)[1]
        check("one model jumps on its own; the unit's stage is still the furthest behind",
              u["stages"] == [1, 6, 2, 3] and u["stage"] == 1, u)
        check("…message names the model", "model 2 → Painted with issues" in toast(page), toast(page))
        undo(page)
        check("…Undo puts that model back", units(page)[1]["stages"] == [1, 1, 2, 3])
        page.select_option(f"{card(page, 2)} select.jump-stage", "4")
        page.wait_for_timeout(150)
        u = units(page)[1]
        check("Move all models to stage moves every model", u["stages"] == [4, 4, 4, 4] and u["stage"] == 4, u)
        check("…and the menu then shows that stage", page.input_value(f"{card(page, 2)} select.jump-stage") == "4")
        shot(page, "v21-jump-each-model.png")
        undo(page)
        check("…Undo puts every model back where it was", units(page)[1]["stages"] == [1, 1, 2, 3])
        page.reload(); page.wait_for_timeout(300)
        check("model stages survive a reload", units(page)[1]["stages"] == [1, 1, 2, 3])

        # Starting stage in the Add form.
        tab(page, "units")
        page.click("#toggle-add")
        start_opts = page.locator("#stage-input option").all_inner_texts()
        check("the Add form has a Starting stage menu with every stage, first stage picked",
              start_opts == STAGES and page.input_value("#stage-input") == "0", start_opts)
        page.fill("#name-input", "Hive Tyrant")
        page.fill("#hobby-input", "40K")
        page.fill("#faction-input", "Tyranids")
        page.select_option("#stage-input", "3")
        shot(page, "v21-starting-stage.png")
        page.click("#add-form button[type=submit]")
        page.wait_for_timeout(150)
        new = [x for x in units(page) if x["name"] == "Hive Tyrant"]
        check("the new unit starts at the picked stage (Primed)", new and new[0]["stage"] == 3, new)
        check("…and its diary starts there", new and new[0]["log"] == [[new[0]["added"], 3]], new and new[0].get("log"))
        check("the Starting stage stays picked for the next unit", page.input_value("#stage-input") == "3")
        page.reload(); page.wait_for_timeout(300)
        check("the new unit's stage survives a reload", [x["stage"] for x in units(page) if x["name"] == "Hive Tyrant"] == [3])
        # Fewer stages: the menu follows Settings.
        seed(page, settings=full_settings(stages=STAGES[:4], doneFrom=3))
        tab(page, "units")
        check("the Starting stage menu follows your stages", page.locator("#stage-input option").count() == 4)

        # ---------- 4. Tap targets ----------
        print("--- 4. Tap targets ---")
        for width in [390, 360]:
            page.set_viewport_size({"width": width, "height": 800})
            seed(page, settings=full_settings())
            tab(page, "units")
            open_unit(page, 2)
            buttons = sizes(page, f"{card(page, 2)} .each-list button")
            check(f"[{width}px] per-model ◀ ▲ are at least 44 × 44", len(buttons) == 8 and all_big(buttons), buttons)
            menus = sizes(page, f"{card(page, 2)} .each-list select") + sizes(page, f"{card(page, 2)} select.jump-stage")
            check(f"[{width}px] the stage menus are at least 44 tall", len(menus) == 5 and all_big(menus, need_width=False), menus)
            check(f"[{width}px] no sideways scroll with a unit open", no_sideways(page))
            if width == 360: shot(page, "v21-tap-targets-units-360.png")
            page.click("#toggle-add")
            check(f"[{width}px] the Starting stage menu is at least 44 tall", all_big(sizes(page, "#stage-input"), need_width=False))
            # v21.8: the Add form's name box has the cursor, so the tab bar is out of the way; tap away first.
            page.evaluate("() => document.activeElement && document.activeElement.blur()")
            page.wait_for_timeout(100)
            tab(page, "settings")
            icons = sizes(page, "#stage-list .icon-button")
            check(f"[{width}px] the stage editor's ↑ ↓ ✕ are at least 44 × 44", len(icons) == 3 * len(STAGES) and all_big(icons), icons[:3])
            check(f"[{width}px] no sideways scroll in Settings", no_sideways(page))
            if width == 360:
                page.locator("#stage-list").scroll_into_view_if_needed()
                shot(page, "v21-tap-targets-stage-editor-360.png", full=False)
            tab(page, "recipes")
            page.click("#new-recipe")
            page.wait_for_timeout(120)
            # A new recipe starts with one empty paint, so the button already says "Mix in another paint".
            mix = [x for x in sizes(page, "#recipe-page button.link-button") if x[2].startswith("+ Mix in another paint")]
            check(f"[{width}px] + Mix in another paint is at least 44 tall", all_big(mix, need_width=False), mix)
            page.evaluate("recipeDraft = null")   # leave the half-made recipe without the Discard question
            # v21.8: the recipe's name box has the cursor, so the tab bar is out of the way; tap away first.
            page.evaluate("() => document.activeElement && document.activeElement.blur()")
            page.wait_for_timeout(100)
            tab(page, "help")
            rows = sizes(page, ".help summary")
            check(f"[{width}px] every Help topic title is at least 44 tall", len(rows) >= 10 and all_big(rows, need_width=False),
                  [r for r in rows if r[1] < 44][:3])
            check(f"[{width}px] no sideways scroll in Help", no_sideways(page))
            if width == 360: shot(page, "v21-tap-targets-help-360.png", full=False)
            seed(page, fresh=True)
            card_buttons = sizes(page, "#examples-card-dash button:not(.more-info-button)")   # v52: More info is checked in test_v52
            check(f"[{width}px] the examples card's buttons are at least 44 tall", len(card_buttons) == 2 and all_big(card_buttons), card_buttons)
            check(f"[{width}px] no sideways scroll on the Dashboard with the examples card", no_sideways(page))
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 5. Help, Back, light mode, errors ----------
        print("--- 5. Help, Back, light mode ---")
        seed(page, settings=full_settings())
        tab(page, "help")
        jump = page.text_content("#help-jump-stage") or ""
        check("Help explains jumping to a stage and its Undo", "Stage" in jump and "Undo" in jump and "Move all models to stage" in jump, jump)
        started = page.text_content("#view-help") or ""
        check("Help explains Starting stage and the examples card",
              "Starting stage" in started and "Clear examples" in started and "Keep them" in started)
        check("Help no longer points to Delete all units for the examples", "Clear them in" not in started)
        # Opening a unit's menus adds no new overlay, so Back from Units still goes to the Dashboard.
        tab(page, "units")
        open_unit(page, 1)
        target = page.evaluate("backTarget() !== null")
        page.go_back(); page.wait_for_timeout(200)
        check("Back from the Units tab (unit open) still goes to the Dashboard", target and
              page.evaluate("settings.tab") == "dashboard")
        seed(page, settings=full_settings(appearance="light"), fresh=True)
        page.evaluate("localStorage.setItem('shades-of-grey-settings', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('shades-of-grey-settings')), {appearance: 'light'})))")
        page.reload(); page.wait_for_timeout(300)
        check("the examples card shows in light mode too", page.is_visible("#examples-card-dash"))
        shot(page, "v21-examples-card-light.png")
        check("v21 screenshots saved", all(os.path.exists(os.path.join(SHOTS, f)) for f in [
            "v21-examples-card-dashboard.png", "v21-examples-card-units.png", "v21-jump-to-stage.png",
            "v21-jump-each-model.png", "v21-starting-stage.png", "v21-tap-targets-units-360.png",
            "v21-tap-targets-stage-editor-360.png", "v21-tap-targets-help-360.png"]))
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
