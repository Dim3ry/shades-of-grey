"""SF2 tests for Minifolio (Models page: "Build my own order" in the Sort models sheet). New behaviour only:
1. The last row, "Build my own order…", opens "Your order" in the same sheet (back arrow, three levels).
2. Menus: fields, no repeats across levels, None only on levels 2 and 3; the direction button text follows the field.
3. Apply sorts (Name A to Z is the last tie-break), Reset to default, Back leaves the order alone.
4. Headings only when the first level is Game or Faction.
5. The Sort button label, the ticks, saving, reload, a field that no longer exists.
6. 44 px menus and buttons at 390, 360 and 320 px, dark and light; the keyboard reaches the menus.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, name, game, faction, stage, count, last, added="2026-09-01"):
    u = {"id": i, "name": name, "stage": stage, "count": count, "added": added, "log": [[added, 0], [last, stage]]}
    if game: u["hobby"] = game
    if faction: u["faction"] = faction
    return u

UNITS = [
    unit(1, "Zealots", "Alpha", "Reds", 2, 10, "2026-10-05"),
    unit(2, "Brutes", "Alpha", "Reds", 4, 5, "2026-09-20"),
    unit(3, "Archers", "Alpha", "Blues", 2, 20, "2026-09-02"),
    unit(4, "Cavalry", "Beta", "Greens", 3, 3, "2026-11-01"),
    unit(5, "Drifters", "", "", 1, 5, "2026-08-01", "2026-08-01"),
]
BASE = {"examplesChecked": True, "recipeExamplesChecked": True, "feedbackShown": True, "backupNudgeDone": True}
LIST = """() => [...document.querySelectorAll('#unit-list > li')].map(li => li.classList.contains('unit-head')
    ? 'H:' + li.textContent.replace(/\\s+/g, ' ').trim() : 'U:' + li.dataset.id)"""

def ids(page): return [x[2:] for x in page.evaluate(LIST) if x.startswith("U:")]
def heads(page): return [x[2:] for x in page.evaluate(LIST) if x.startswith("H:")]

def start(page, **kw):
    t.load(page, units=UNITS, settings={**BASE, **kw})
    page.click('nav button[data-tab="units"]')
    page.wait_for_selector("#unit-list li.unit")

def open_custom(page):
    page.click("#toggle-sort")
    page.wait_for_selector(".sort-sheet-box .sort-row")
    page.click(".sort-row-custom")
    page.wait_for_selector(".sort-level")

def level(page, i, field=None, rev=False):
    if field is not None: page.select_option(f'select[data-level="{i}"]', field)
    if rev: page.click(f'.sort-level button[data-level="{i}"]')

def options(page, i): return page.eval_on_selector_all(f'select[data-level="{i}"] option', "os => os.map(o => o.textContent)")
def dirtext(page, i): return page.locator(f'.sort-level button[data-level="{i}"]').text_content()

def apply(page):
    page.click("#dialog-yes")
    page.wait_for_timeout(200)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. The last row and the view ---")
        start(page)
        page.click("#toggle-sort"); page.wait_for_selector(".sort-sheet-box .sort-row")
        rows = page.locator(".sort-row")
        last = rows.nth(rows.count() - 1)
        check("the last row says Build my own order… with a chevron and a second line",
              rows.count() == 5 and last.locator(".sort-row-title").inner_text() == "Build my own order…" and last.locator(".sort-chev").count() == 1
              and last.locator(".sort-row-sub").inner_text() == "Pick up to three levels", rows.all_inner_texts())
        last.click()
        page.wait_for_selector(".sort-level")
        check("the view is titled Your order with a back arrow, three levels and Apply",
              page.locator("#dialog-message").inner_text() == "Your order" and page.locator(".sort-back").is_visible() and page.locator(".sort-level").count() == 3
              and page.locator("#dialog-yes").inner_text() == "Apply" and page.locator(".sort-reset").inner_text() == "Reset to default")
        check("the levels are called Sort by, Then by, Then by", page.locator(".sort-level-label").all_text_contents() == ["Sort by", "Then by", "Then by"])
        page.click(".sort-back")
        check("the back arrow returns to the list without changing the order",
              page.locator("#dialog-message").inner_text() == "Sort models" and page.locator(".sort-row").count() == 5
              and page.locator("#toggle-sort .sort-order").inner_text() == "Game › Faction › A–Z")
        page.keyboard.press("Escape")

        print("\n--- 2. Menus and direction buttons ---")
        open_custom(page)
        check("it starts from the order in use (Game, Faction, Name)", page.eval_on_selector_all(".sort-level select", "s => s.map(x => x.value)") == ["game", "faction", "name"])
        check("a field in use elsewhere is left out of a menu", "Game" not in options(page, 1) and "Faction" not in options(page, 0) and "Name" not in options(page, 0), (options(page, 0), options(page, 1)))
        check("levels 2 and 3 can be None", options(page, 1)[0] == "None" and options(page, 2)[0] == "None")
        level(page, 1, "")
        check("level 1 then has all six fields and no None", options(page, 0) == ["Game", "Faction", "Stage", "Name", "Recently updated", "Number of models"], options(page, 0))
        level(page, 0, "stage")
        check("direction text for Stage", dirtext(page, 0) == "Furthest first")
        page.click('.sort-level button[data-level="0"]')
        check("the direction button flips it", dirtext(page, 0) == "Least first")
        for field, want in [("recent", ["Newest first", "Oldest first"]), ("size", ["Most first", "Fewest first"]), ("game", ["A → Z", "Z → A"]), ("name", ["A → Z", "Z → A"]), ("faction", ["A → Z", "Z → A"])]:
            level(page, 0, field)
            first = dirtext(page, 0)
            page.click('.sort-level button[data-level="0"]')
            check(f"direction text for {field}", [first, dirtext(page, 0)] == want, [first, dirtext(page, 0)])
        level(page, 0, "stage"); level(page, 1, "");
        check("None on level 2 leaves level 3 with nothing to do (greyed, None)", page.locator('select[data-level="2"]').is_disabled()
              and page.eval_on_selector('select[data-level="2"]', "s => s.value") == "" and page.locator('.sort-level button[data-level="1"]').is_disabled())
        page.click(".sort-x")

        print("\n--- 3. Apply, tie-break, Reset ---")
        open_custom(page)
        level(page, 0, "stage", rev=False); level(page, 1, "size"); level(page, 2, "")
        apply(page)
        # stage furthest first: Brutes(4), Cavalry(3), then stage 2: Archers(20) before Zealots(10) by most models, then Drifters(1)
        check("Apply closes the sheet and sorts (Stage, then Number of models)", not page.locator("#dialog-backdrop").is_visible() and ids(page) == ["2", "4", "3", "1", "5"], ids(page))
        level_sav = page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).unitSort")
        check("saved with the sort choice", level_sav["mode"] == "custom" and [l["f"] for l in level_sav["levels"]] == ["stage", "size"], level_sav)
        open_custom(page)
        level(page, 1, ""); level(page, 0, "size", rev=True)
        apply(page)
        # fewest models first: Cavalry 3, then Brutes 5 and Drifters 5 tie -> Name A to Z: Brutes, Drifters; Zealots 10; Archers 20
        check("a tie ends with Name A to Z even though it was not chosen", ids(page) == ["4", "2", "5", "1", "3"], ids(page))
        open_custom(page)
        level(page, 0, "name"); level(page, 1, "game", rev=True)
        page.click(".sort-reset")
        check("Reset to default puts Game, Faction, Name back in the three menus",
              page.eval_on_selector_all(".sort-level select", "s => s.map(x => x.value)") == ["game", "faction", "name"] and dirtext(page, 0) == "A → Z")
        apply(page)
        check("…and Apply sorts by it (and shows the default's tick)", ids(page) == ["3", "2", "1", "4", "5"] and page.locator("#toggle-sort .sort-order").inner_text() == "Game › Faction › A–Z", ids(page))
        open_custom(page)
        level(page, 0, "game", rev=True)
        page.click(".sort-x")
        check("closing with the X leaves the order as it was", ids(page) == ["3", "2", "1", "4", "5"])

        print("\n--- 4. Headings ---")
        def set_order(first, second=None, third=None):
            open_custom(page); level(page, 1, ""); level(page, 0, first)   # clearing level 2 first frees every field for level 1
            if second: level(page, 1, second)
            if third: level(page, 2, third)
            apply(page)
        set_order("game", "faction")
        check("Game then Faction: game headings and faction headings", any(h.startswith("Alpha") for h in heads(page)) and any(h.startswith("Reds") for h in heads(page)), heads(page))
        set_order("game", "stage")
        check("Game then something else: game headings only", heads(page) == ["Alpha", "Beta", "No game"], heads(page))
        set_order("faction", "stage")
        check("Faction first: faction headings only", heads(page) and all(("unit" in h) for h in heads(page)) and not any(h in ("Alpha", "Beta") for h in heads(page)), heads(page))
        set_order("stage", "faction")
        check("Stage first: a flat list", heads(page) == [])
        set_order("name")
        check("Name only: a flat list", heads(page) == [] and ids(page) == ["3", "2", "4", "5", "1"], ids(page))

        print("\n--- 5. Button label, ticks, saving ---")
        set_order("faction", "stage", "name")
        check("the button joins the levels, Name as A–Z", page.locator("#toggle-sort .sort-order").inner_text() == "Faction › Stage › A–Z")
        page.click("#toggle-sort"); page.wait_for_selector(".sort-sheet-box .sort-row")
        ticks = page.eval_on_selector_all(".sort-row", "rs => rs.map(r => r.getAttribute('aria-checked'))")
        check("no preset is ticked while a custom order is active, the custom row is", ticks == ["false", "false", "false", "false", "true"], ticks)
        page.keyboard.press("Escape")
        page.reload(); t.app_ready(page); t.leave_launch(page)
        page.click('nav button[data-tab="units"]'); page.wait_for_selector("#unit-list li.unit"); page.wait_for_timeout(500)
        check("the custom order survives a reload", page.locator("#toggle-sort .sort-order").inner_text() == "Faction › Stage › A–Z")
        check("and travels in a backup", page.evaluate("() => backupData().unitSort.mode") == "custom")
        set_order("name")   # Name only equals the A-Z preset
        page.click("#toggle-sort"); page.wait_for_selector(".sort-sheet-box .sort-row")
        check("an order that equals a preset shows that preset's tick", page.locator('.sort-row[data-sort-mode="az"]').get_attribute("aria-checked") == "true")
        page.keyboard.press("Escape")
        t.load(page, units=UNITS, settings={**BASE, "unitSort": {"mode": "custom", "levels": [{"f": "colour", "rev": False}]}})
        page.click('nav button[data-tab="units"]'); page.wait_for_selector("#unit-list li.unit")
        check("a saved field that no longer exists falls back to the default", page.locator("#toggle-sort .sort-order").inner_text() == "Game › Faction › A–Z" and ids(page)[0] == "3")
        t.load(page, units=UNITS, settings={**BASE, "unitSort": {"mode": "custom", "levels": [{"f": "game"}, {"f": "game"}]}})
        page.click('nav button[data-tab="units"]'); page.wait_for_selector("#unit-list li.unit")
        check("so does a level used twice", page.locator("#toggle-sort .sort-order").inner_text() == "Game › Faction › A–Z")

        print("\n--- 6. Sizes and the keyboard ---")
        start(page)
        open_custom(page)
        page.focus(".sort-back")
        seen = []
        for _ in range(9):
            page.keyboard.press("Tab")
            seen.append(page.evaluate("() => { const a = document.activeElement; return a.tagName + ':' + (a.dataset.level || a.id || a.className); }"))
        check("Tab reaches the menus and direction buttons and stays inside the sheet", any(x.startswith("SELECT") for x in seen) and any(x.startswith("BUTTON:") and ":0" in x or ":1" in x for x in seen)
              and page.evaluate("() => document.getElementById('dialog').contains(document.activeElement)"), seen)
        page.keyboard.press("Escape")
        for w, hgt in [(390, 844), (360, 640), (320, 568)]:
            for scheme in ["dark", "light"]:
                c2 = browser.new_context(viewport={"width": w, "height": hgt}, service_workers="block", color_scheme=scheme, reduced_motion="reduce")
                pg = c2.new_page()
                start(pg, appearance=scheme)
                open_custom(pg)
                m = pg.evaluate("""() => { const box = document.getElementById('dialog').getBoundingClientRect(), q = s => [...document.querySelectorAll(s)].map(e => e.getBoundingClientRect());
                    return { small: [...q('.sort-level select'), ...q('.sort-level button'), ...q('.sort-reset'), ...q('.sort-back'), ...q('#dialog-yes')].filter(r => r.height < 43.5 || r.width < 43.5).length,
                             inside: box.left >= -1 && box.right <= window.innerWidth + 1, wide: document.documentElement.scrollWidth > window.innerWidth + 1 }; }""")
                check(f"{w}px {scheme}: menus, direction buttons, Reset, Back and Apply are 44 px, nothing sideways", m["small"] == 0 and m["inside"] and not m["wide"], m)
                c2.close()
        check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
