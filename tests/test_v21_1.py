"""v21.1 tests for Minifolio: bulk "Move to stage" (select mode), the "Ultramarines armour" paste
quirk, and status-pill width on Your Palette.

Checks:
1. Version numbers (plain numbers), sw.js matches, the Updates entry, CNAME and the ocr folder kept,
   storage names and the data version unchanged (still 1).
2. Select mode: Select puts a tick box on every card you can see; tapping a card ticks it (it doesn't
   open, and the ▲ step aside); the bar counts the ticks; the Move menu is off until something is
   ticked; Select all shown / Untick all; only units the filters show can be ticked.
3. Moving: the ticked units all go to the chosen stage (every model of a model-by-model unit, a diary
   entry each), untouched units stay put, select mode closes, it survives a reload. One Undo puts
   every unit back EXACTLY (stage, each model's stage, diary), and that survives a reload too.
   Units already at that stage are skipped.
4. Closing select mode: Cancel, the phone's Back button (then Back again goes to the Dashboard as
   before), leaving the tab, and + Add unit.
5. The paste reader: "Ultramarines armour" and similar first lines are a scheme + part, never a step
   using "Ultramarines Blue" (known answers); real paint names still read as paints.
6. Status pills on Your Palette are only as wide as their text.
7. Help, nothing scrolls sideways at 360 px, light mode, screenshots, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
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

STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 0, "count": 5,
     "log": [["2026-09-01", 0]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 1, "count": 4, "each": True,
     "stages": [1, 1, 2, 3], "log": [["2026-09-01", 1], ["2026-09-02", 2, 2]]},
    {"id": 3, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 10,
     "log": [["2026-09-01", 2]]},
    {"id": 4, "name": "Liberators", "hobby": "Age of Sigmar", "faction": "Stormcast Eternals", "stage": 4, "count": 5,
     "log": [["2026-09-01", 4]]},
]

def seed(page, units=UNITS, settings=None, book=None):
    page.goto(URL)
    page.evaluate("""([u, s, b]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", [units, settings, book])
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

def by_id(found, uid):
    return next((u for u in found if u["id"] == uid), None)

def toast(page):
    return page.inner_text("#toast-text") if page.is_visible("#toast") else ""

def card(uid):
    return f'#view-units li.unit[data-id="{uid}"]'

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def selecting(page):
    return page.evaluate("selectMode") and page.is_visible("#select-bar")

def ticks(page):
    return page.locator('#view-units .unit-tick input').count()

def move_to(page, stage_index):
    page.select_option("#select-move", str(stage_index))
    page.wait_for_timeout(150)

def keep(u):
    """The parts of a unit that a move (and its Undo) can touch."""
    return {"stage": u.get("stage"), "stages": u.get("stages"), "log": u.get("log")}

SUMMARY_JS = """text => parseRecipeText(text).schemes.map(s => ({
  name: s.name,
  parts: s.parts.map(p => ({ name: p.name, steps: p.steps.map(st => st.paints.map(m => m.paint ? m.paint.name : m.typed)) })),
}))"""

PASTE_CASES = [
    {"text": "Ultramarines armour\nMacragge Blue\nNuln Oil",
     "scheme": "Ultramarines", "parts": {"Armour": [["Macragge Blue"], ["Nuln Oil"]]}},
    {"text": "Ultramarines Armour\n\nMacragge Blue",
     "scheme": "Ultramarines", "parts": {"Armour": [["Macragge Blue"]]}},
    {"text": "Dark Angels armor\nCaliban Green",
     "scheme": "Dark Angels", "parts": {"Armor": [["Caliban Green"]]}},
    {"text": "Death Guard cloak and trim\nAgrax Earthshade",
     "scheme": "Death Guard", "parts": {"Cloak and trim": [["Agrax Earthshade"]]}},
    {"text": "Blood Angels recipes\nMephiston Red",
     "scheme": "Blood Angels", "parts": {"Whole model": [["Mephiston Red"]]}},
    {"text": "Space Wolves armour\nFenrisian Grey\n\nSpace Wolves trim\nRetributor Armour",
     "scheme": "Space Wolves", "parts": {"Armour": [["Fenrisian Grey"]], "Trim": [["Retributor Armour"]]}},
]

def main():
    sw = read("sw.js")
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 360, "height": 800})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        DialogAnswers(page)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page, settings=full_settings())
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21.1 or later", float(version[1:]) >= 21.1, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        entry = [i for i, h in enumerate(heads) if h.startswith("v21.1")]
        check("the Updates tab has a v21.1 entry", bool(entry), heads[:3])
        if entry:
            text = page.locator("#changelog .release").nth(entry[0]).inner_text()
            check("the v21.1 entry mentions Select, Ultramarines armour and the status labels",
                  all(w in text for w in ["Select", "Ultramarines armour", "status labels"]), text[:300])
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("the ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm", "README.md"]))
        check("the data version is still 1", page.evaluate("DATA_VERSION") == 1)
        check("storage names unchanged", all(k in html for k in
              ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes", "shades-of-grey-photos"]))

        # ---------- 2. Select mode ----------
        print("--- 2. Select mode ---")
        seed(page, settings=full_settings())
        tab(page, "units")
        check("a Select button is on the Units tab", page.is_visible("#toggle-select"))
        check("no tick boxes and no bar before Select", ticks(page) == 0 and not page.is_visible("#select-bar"))
        page.click("#toggle-select")
        page.wait_for_timeout(80)
        check("Select shows the bar", selecting(page))
        check("every shown unit gets a tick box", ticks(page) == 4, ticks(page))
        check("the ▲ buttons step aside while selecting", page.locator("#view-units .up-button").count() == 0)
        check("the Select button shows it's on", page.get_attribute("#toggle-select", "aria-pressed") == "true")
        check("the bar starts at 0 ticked", page.inner_text("#select-count").startswith("0 of 4"), page.inner_text("#select-count"))
        check("the Move menu is off until something is ticked", page.is_disabled("#select-move"))
        page.click(card(1) + " .info")
        page.wait_for_timeout(80)
        check("tapping a card ticks it", page.is_checked(card(1) + " .unit-tick input"))
        check("...and doesn't open its details", page.locator(card(1) + " .panel").count() == 0)
        check("the bar counts it", page.inner_text("#select-count").startswith("1 of 4"), page.inner_text("#select-count"))
        page.click(card(2) + " .unit-tick input")
        page.wait_for_timeout(80)
        check("the tick box itself works too", page.is_checked(card(2) + " .unit-tick input"))
        first = page.evaluate("document.getElementById('select-move').options[0].text")
        check("the menu says 'Move 2 to stage…'", first == "Move 2 to stage…", first)
        check("the Move menu is on with something ticked", not page.is_disabled("#select-move"))
        check("the Move menu lists every stage", page.evaluate(
            "[...document.getElementById('select-move').options].slice(1).map(o => o.text)") == STAGES)
        page.click(card(2) + " .info")
        page.wait_for_timeout(80)
        check("tapping a ticked card unticks it", not page.is_checked(card(2) + " .unit-tick input"))
        page.click("#select-all")
        page.wait_for_timeout(80)
        check("Select all shown ticks every shown unit", page.inner_text("#select-count").startswith("4 of 4"))
        check("...and becomes Untick all", page.inner_text("#select-all") == "Untick all")
        page.click("#select-all")
        page.wait_for_timeout(80)
        check("Untick all clears the ticks", page.inner_text("#select-count").startswith("0 of 4"))
        # Filters: only shown units can be ticked.
        page.click("#select-all")
        page.wait_for_timeout(50)
        page.evaluate("filters.faction = 'Tyranids'; render();")
        page.wait_for_timeout(80)
        check("a filter unticks units it hides", sorted(page.evaluate("[...ticked]")) == [2, 3], page.evaluate("[...ticked]"))
        check("only shown units have tick boxes", ticks(page) == 2, ticks(page))
        page.click("#select-all")      # all shown are ticked -> Untick all
        page.click("#select-all")      # -> Select all shown
        page.wait_for_timeout(80)
        check("Select all shown only ticks what the filters show", sorted(page.evaluate("[...ticked]")) == [2, 3])
        page.evaluate("clearFilters(); render();")
        page.wait_for_timeout(50)
        check("no sideways scroll at 360 px in select mode", no_sideways(page))
        page.click(card(1) + " .info")
        page.wait_for_timeout(80)
        shot(page, "v21-1-select-mode.png")
        bar = page.evaluate("(() => { const r = document.getElementById('select-bar').getBoundingClientRect(); return [r.left, r.right, r.bottom]; })()")
        tabs_top = page.evaluate("document.querySelector('.tabs').getBoundingClientRect().top")
        check("the bar fits on screen above the tab bar", bar[0] >= 0 and bar[1] <= 360 and bar[2] <= tabs_top + 1, [bar, tabs_top])
        sizes = page.evaluate("""() => ['#select-all', '#select-cancel', '#select-move', '#toggle-select']
            .map(s => document.querySelector(s).getBoundingClientRect().height)""")
        check("the bar's buttons and menu are at least 44 px tall", all(h >= 44 for h in sizes), sizes)
        tick_box = page.evaluate("(() => { const r = document.querySelector('#view-units .unit-tick').getBoundingClientRect(); return [r.width, r.height]; })()")
        check("each tick box is a 44 px target", tick_box[0] >= 44 and tick_box[1] >= 44, tick_box)
        # Bottom of the list isn't hidden behind the bar.
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(80)
        last = page.evaluate(f"document.querySelector('{card(4)}').getBoundingClientRect().bottom")
        bar_top = page.evaluate("document.getElementById('select-bar').getBoundingClientRect().top")
        check("the last unit can scroll clear of the bar", last <= bar_top + 1, [last, bar_top])
        shot(page, "v21-1-move-bar.png")

        # ---------- 3. Moving and Undo ----------
        print("--- 3. Moving and Undo ---")
        seed(page, settings=full_settings())
        before = {u["id"]: keep(u) for u in units(page)}
        tab(page, "units")
        page.click("#toggle-select")
        for uid in (1, 2, 3):
            page.click(card(uid) + " .info")
            page.wait_for_timeout(40)
        move_to(page, 5)   # Battle ready
        after = units(page)
        check("every ticked unit moved to Battle ready", all(by_id(after, i)["stage"] == 5 for i in (1, 2, 3)),
              [by_id(after, i)["stage"] for i in (1, 2, 3)])
        check("all models of the model-by-model unit moved", by_id(after, 2)["stages"] == [5, 5, 5, 5], by_id(after, 2).get("stages"))
        check("each moved unit got a diary entry at Battle ready",
              all(by_id(after, i)["log"][-1][1] == 5 and len(by_id(after, i)["log"]) == len(before[i]["log"]) + 1 for i in (1, 2, 3)),
              [by_id(after, i)["log"] for i in (1, 2, 3)])
        check("the unticked unit didn't change", keep(by_id(after, 4)) == before[4])
        check("select mode closes after a move", not selecting(page) and ticks(page) == 0)
        msg = toast(page)
        check("the message says how many moved, with Undo", "3 units → Battle ready" in msg and page.is_visible("#toast-undo"), msg)
        shot(page, "v21-1-moved.png")
        page.reload()
        page.wait_for_timeout(300)
        after = units(page)
        check("the move survives a reload", all(by_id(after, i)["stage"] == 5 for i in (1, 2, 3)) and by_id(after, 2)["stages"] == [5] * 4)
        # Undo (do it again, then Undo straight away).
        seed(page, settings=full_settings())
        tab(page, "units")
        page.click("#toggle-select")
        page.click("#select-all")
        move_to(page, 7)
        check("Move works with Select all shown", all(u["stage"] == 7 for u in units(page)))
        page.click("#toast-undo")
        page.wait_for_timeout(150)
        undone = {u["id"]: keep(u) for u in units(page)}
        check("one Undo puts every unit back exactly (stage, each model's stage, diary)", undone == before,
              json.dumps(undone)[:400])
        shot(page, "v21-1-undo.png")
        page.reload()
        page.wait_for_timeout(300)
        check("the Undo survives a reload", {u["id"]: keep(u) for u in units(page)} == before)
        # Units already at the stage are skipped.
        tab(page, "units")
        page.click("#toggle-select")
        page.click(card(1) + " .info")
        page.click(card(3) + " .info")
        page.wait_for_timeout(50)
        move_to(page, 2)   # Hormagaunts are already Assembled
        after = units(page)
        check("a unit already at that stage gets no new diary entry", keep(by_id(after, 3)) == before[3])
        check("...the other still moves", by_id(after, 1)["stage"] == 2)
        check("...and the message says one was already there", "already there" in toast(page), toast(page))
        page.click("#toast-undo")
        page.wait_for_timeout(120)
        check("...and Undo puts it back", {u["id"]: keep(u) for u in units(page)} == before)

        # ---------- 4. Closing select mode ----------
        print("--- 4. Closing select mode ---")
        tab(page, "units")
        page.click("#toggle-select")
        page.click(card(1) + " .info")
        page.click("#select-cancel")
        page.wait_for_timeout(80)
        check("Cancel closes select mode", not selecting(page) and ticks(page) == 0)
        check("Cancel changes nothing", {u["id"]: keep(u) for u in units(page)} == before)
        check("the ▲ buttons are back", page.locator("#view-units .up-button").count() == 4)
        page.click("#toggle-select")
        page.click(card(1) + " .info")
        page.wait_for_timeout(120)
        check("backTarget() sees select mode", page.evaluate("backTarget() === closeSelect"))
        page.go_back()
        page.wait_for_timeout(250)
        check("the phone's Back button closes select mode", not selecting(page))
        check("...and stays on the Units tab", page.evaluate("settings.tab") == "units")
        check("...without moving anything", {u["id"]: keep(u) for u in units(page)} == before)
        page.go_back()
        page.wait_for_timeout(250)
        check("Back again goes to the Dashboard, as before", page.evaluate("settings.tab") == "dashboard")
        tab(page, "units")
        page.click("#toggle-select")
        tab(page, "recipes")
        tab(page, "units")
        check("leaving the tab ends select mode", not selecting(page))
        page.click("#toggle-select")
        page.click("#toggle-add")
        page.wait_for_timeout(80)
        check("+ Add unit ends select mode", not selecting(page) and page.is_visible("#add-form"))
        page.click("#toggle-add")
        page.click("#toggle-select")
        page.wait_for_timeout(50)
        check("Select closes the Add form", not page.is_visible("#add-form"))
        page.click("#toggle-select")
        page.wait_for_timeout(50)
        check("tapping Select again stops selecting", not selecting(page))
        check("select mode isn't saved", "selectMode" not in json.dumps(page.evaluate(
            "JSON.parse(localStorage.getItem('shades-of-grey-settings'))")))
        seed(page, units=[], settings=full_settings(tab="units"))
        check("no Select button with no units", not page.is_visible("#toggle-select"))

        # ---------- 5. The paste reader ----------
        print("--- 5. Paste: faction followed by a part ---")
        seed(page, units=[], settings=full_settings())
        for case in PASTE_CASES:
            got = page.evaluate(SUMMARY_JS, case["text"])
            first_line = case["text"].splitlines()[0]
            all_paints = [p for s in got for part in s["parts"] for st in part["steps"] for p in st]
            check(f"'{first_line}' is the {case['scheme']} scheme",
                  len(got) == 1 and got[0]["name"] == case["scheme"], got)
            parts = {part["name"]: part["steps"] for s in got for part in s["parts"]}
            check(f"'{first_line}' gives the right part(s) and steps", parts == case["parts"], parts)
            check(f"'{first_line}' is never a paint step",
                  not any(p.startswith(case["scheme"]) for p in all_paints), all_paints)
        got = page.evaluate(SUMMARY_JS, "Ultramarines Blue\nNuln Oil")
        steps = [st for s in got for part in s["parts"] for st in part["steps"]]
        check("a real paint name ('Ultramarines Blue') is still a paint", steps and steps[0] == ["Ultramarines Blue"], got)
        got = page.evaluate(SUMMARY_JS, "Ultramarines\n\nArmour:\nMacragge Blue")
        check("a bare faction name still works as before (v18)",
              got and got[0]["name"] == "Ultramarines" and got[0]["parts"][0]["name"] == "Armour", got)
        got = page.evaluate(SUMMARY_JS, "Death Guard Green\nAgrax Earthshade")
        check("'Death Guard Green' (a paint) isn't taken for a scheme",
              any(st == ["Death Guard Green"] for s in got for part in s["parts"] for st in part["steps"]), got)

        # ---------- 6. Status pills ----------
        print("--- 6. Status pills ---")
        book = {"paints": [
            {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3c6e", "status": "owned"},
            {"id": 2, "brand": "Citadel", "name": "A paint with a much longer name to stretch the row", "colour": "#3b5b7a", "status": "wishlist"},
            {"id": 3, "brand": "Vallejo", "name": "Ivory", "colour": "#eae0c8", "status": "low", "spare": True},
            {"id": 4, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "empty"}],
            "recipes": [], "schemes": [], "v15": True}
        seed(page, units=[], settings=full_settings(), book=book)
        page.evaluate("settings.recipeView = 'palette'; showTab('recipes'); render();")
        page.wait_for_timeout(150)
        pills = page.evaluate("""() => [...document.querySelectorAll('.paint-text .status-pill')].map(p => {
            const range = document.createRange(); range.selectNodeContents(p);
            return [p.getBoundingClientRect().width, range.getBoundingClientRect().width, p.closest('.paint-head').getBoundingClientRect().width, p.textContent]; })""")
        check("every paint with a status shows a pill", len(pills) == 4, pills)
        check("each pill is only as wide as its text (plus a little padding)",
              pills and all(w <= t + 20 for w, t, _, _ in pills), pills)
        check("pills no longer stretch across the paint's row", pills and all(w < row * 0.8 for w, _, row, _ in pills), pills)
        check("no sideways scroll on Your Palette at 360 px", no_sideways(page))
        shot(page, "v21-1-palette-pills.png")
        page.evaluate("settings.appearance = 'light'; applyPalette(); render();")
        page.wait_for_timeout(100)
        shot(page, "v21-1-palette-pills-light.png")
        page.evaluate("settings.appearance = 'dark'; applyPalette(); render();")

        # ---------- 7. Help, light mode, errors ----------
        print("--- 7. Help, light mode, errors ---")
        seed(page, settings=full_settings())
        help_text = page.evaluate("document.getElementById('view-help').textContent")
        check("Help explains moving several units at once",
              "Move several units at once" in help_text and "Select all shown" in help_text)
        check("Help explains a faction followed by a part", "Blue Army armour" in help_text)
        page.evaluate("settings.appearance = 'light'; applyPalette(); render();")
        tab(page, "units")
        page.click("#toggle-select")
        page.click(card(2) + " .info")
        page.wait_for_timeout(100)
        check("no sideways scroll in light mode while selecting", no_sideways(page))
        shot(page, "v21-1-select-mode-light.png")
        page.click("#select-cancel")
        page.set_viewport_size({"width": 1280, "height": 900})
        page.evaluate("settings.appearance = 'dark'; applyPalette(); render();")
        page.click("#toggle-select")
        page.wait_for_timeout(100)
        b = page.evaluate("document.getElementById('select-bar').getBoundingClientRect().bottom")
        check("on a wide screen the bar sits at the bottom of the window", 800 < b <= 900, b)
        shot(page, "v21-1-select-mode-wide.png")
        page.click("#select-cancel")
        check("no page errors", not errors, errors[:3])
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
