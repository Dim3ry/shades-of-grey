"""Chunk RS5 tests for Minifolio: the scheme form and the same-faction warning. New behaviour only.

1. Layout: name, Faction row (Change), Search recipes, recipes grouped by part ("No part" last), the note, then Save.
   Rows 52 px or more, tick boxes about 24 px with a 44 px tap area, Select all and Change 44 px.
2. Faction filled in: from the ticked recipes when they agree ("From the recipes you picked"), otherwise the last faction
   used, otherwise blank. Blank + Save asks on the Faction row (in view, box focused) and saves nothing.
3. Select all and Clear per group; Search recipes filters the groups; Save reads "Save scheme (N recipes)" live.
4. Same-faction warning: shows with another scheme in the faction that attaches to new units, not with a different faction,
   in New and Edit. Unticked: saved, does not attach. Ticked: this one attaches, the other stops (kept, units untouched).
5. Settings, Recipe preferences, "Ask for a faction on schemes": on by default; off hides the Faction row, a scheme saved
   with no faction attaches to no new unit and can still be applied by hand from a unit's Link a recipe menu.
6. An older backup (schemes with no "auto") loads as today: every scheme attaches.
7. 390x844, 360x640 and 320x640, dark and light, 22 recipes and three schemes: no sideways scroll, tap targets 44 px.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Made-up factions and recipes (nothing here names a real army). 22 recipes over four parts and "No part".
PARTS = [("Armour", 8), ("Trim", 5), ("Eyes", 4), ("Base", 3), ("", 2)]
RECIPES = []
for part, n in PARTS:
    for i in range(n):
        rid = 100 + len(RECIPES) + 1
        RECIPES.append(t.rec(rid, f"{part or 'Loose'} recipe {i + 1}", part, [1 + (rid % 4)]))
ARMOUR1, ARMOUR2, TRIM1 = 101, 102, 109
EYES = [r["id"] for r in RECIPES if r["part"] == "Eyes"]
TRIM = [r["id"] for r in RECIPES if r["part"] == "Trim"]
UNITS = [t.unit(1, "Troop A", "Gloom Legion", [ARMOUR1]), t.unit(2, "Troop B", "Gloom Legion", [ARMOUR1, ARMOUR2]),
         t.unit(3, "Rider", "Other Host", [TRIM1])]
SCHEMES = [{"id": 1, "name": "Gloom main", "faction": "Gloom Legion", "auto": True, "recipes": [ARMOUR1, ARMOUR2]},
           {"id": 2, "name": "Other look", "faction": "Other Host", "auto": True, "recipes": [TRIM1]},
           {"id": 3, "name": "Gloom spare", "faction": "Gloom Legion", "auto": False, "recipes": [EYES[0]]}]
SMALL = """(sel) => [...document.querySelectorAll(sel + ' button, ' + sel + ' select, ' + sel + ' textarea, ' + sel + ' input:not([type=checkbox])')]
    .filter(e => e.getBoundingClientRect().width && e.getBoundingClientRect().height < 43.5).map(e => e.textContent.trim().slice(0, 15))"""

def start(page, settings=None):
    s = {"tab": "recipes", "recipeView": "schemes", "examplesChecked": True, "recipeExamplesChecked": True}
    s.update(settings or {})
    t.load(page, recipes=RECIPES, units=UNITS, settings=s)
    page.evaluate("(s) => { book.parts = ['Whole model', 'Armour', 'Trim', 'Eyes', 'Base']; book.schemes = s; render(); }", SCHEMES)
    quiet(page)

def new_scheme(page):
    t.blur(page)
    page.click("#new-scheme")
    quiet(page)

def tick(page, rid):
    page.evaluate("(id) => { const r = recipeById(id); const box = [...document.querySelectorAll('#scheme-page .scheme-pick-row')]"
                  ".find(l => l.textContent.includes(r.name)).querySelector('input'); box.click(); }", rid)

def group_button(page, name):
    return page.locator(f"#scheme-page .scheme-group-all[aria-label$=' {name}']")

def faction_text(page):
    return page.evaluate("() => (document.querySelector('#scheme-page .scheme-faction-value') || {}).textContent || ''")

def from_line(page):
    return page.locator("#scheme-page .scheme-faction .hint", has_text="From the recipes you picked").count() == 1

def save_label(page):
    return page.evaluate("() => document.querySelector('#scheme-page .scheme-save').textContent")

def set_faction(page, name):
    page.click("#scheme-page .scheme-faction-row button")   # Change
    page.fill("#scheme-page .scheme-faction input", name)
    page.click("#scheme-page .scheme-faction-row button")   # Done

def save(page, name):
    page.fill("#scheme-page .scheme-form > label input", name)
    page.click("#scheme-page .scheme-save")
    quiet(page)

def scheme(page, name):
    return page.evaluate("(n) => { const s = book.schemes.find(x => x.name === n); return s ? { auto: s.auto, faction: s.faction, recipes: s.recipes } : null; }", name)

def new_unit_recipes(page, faction):
    return page.evaluate("(f) => { const m = addModel({ name: 'Fresh ' + Math.random(), hobby: 'Test game', faction: f }); render(); return m.recipes || []; }", faction)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Layout ---")
        start(page)
        new_scheme(page)
        order = page.evaluate("""() => { const q = (s) => document.querySelector('#scheme-page ' + s);
            const list = [q('.scheme-form > label input'), q('.scheme-faction'), q('.scheme-recipe-search'), q('.scheme-group'), q('.scheme-save')];
            return list.every(Boolean) && list.every((e, i) => !i || (list[i - 1].compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING)); }""")
        check("name, Faction row, Search recipes, groups, Save in that order", order)
        check("the search box is labelled Search recipes", page.get_attribute("#scheme-page .scheme-recipe-search", "aria-label") == "Search recipes")
        heads = page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-group h3')].map(h => h.textContent)")
        check("groups by part, in the parts order, with No part last", heads == ["Armour", "Trim", "Eyes", "Base", "No part"], heads)
        sizes = page.evaluate("""() => [...document.querySelectorAll('#scheme-page .scheme-pick-row')].map(l => {
            const r = l.getBoundingClientRect(), b = l.querySelector('input').getBoundingClientRect(); return [r.height, r.width, b.width, b.height]; })""")
        check("all 22 recipes listed", len(sizes) == 22, len(sizes))
        check("every row is 52 px or more and its tap area at least 44 px wide", all(h >= 51.5 and w >= 44 for h, w, _, _ in sizes), sizes[:3])
        check("the tick box itself is about 24 px", all(22 <= bw <= 26 and 22 <= bh <= 26 for _, _, bw, bh in sizes), sizes[:3])
        tall = page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-group-all, #scheme-page .scheme-faction-row button')].map(b => [b.getBoundingClientRect().height, b.getBoundingClientRect().width])")
        check("Select all and Change are 44 px tap targets", tall and all(h >= 43.5 and w >= 43.5 for h, w in tall), tall)

        print("\n--- 2. Faction filled in ---")
        check("no faction anywhere yet: the row says None", faction_text(page) == "None" and not from_line(page), faction_text(page))
        tick(page, ARMOUR1)
        check("ticking a recipe used in one faction fills that faction in", faction_text(page) == "Gloom Legion", faction_text(page))
        check("...with the line From the recipes you picked", from_line(page))
        tick(page, TRIM1)
        check("a recipe from another faction as well: they disagree, so it goes back to blank", faction_text(page) == "None" and not from_line(page), faction_text(page))
        tick(page, TRIM1)
        tick(page, ARMOUR1)
        page.evaluate("() => closeScheme(false)")
        page.evaluate("() => { settings.lastFaction = 'Lonely Host'; }")
        new_scheme(page)
        check("nothing ticked: the last faction used is filled in, without the recipes line", faction_text(page) == "Lonely Host" and not from_line(page), faction_text(page))
        page.evaluate("() => closeScheme(false)")
        page.evaluate("() => { settings.lastFaction = ''; startScheme(null, '', [%d]); }" % ARMOUR1)
        quiet(page)
        check("opened from a recipe's New scheme: that recipe starts ticked and fills the faction",
              page.evaluate("() => schemeDraft.recipes.join()") == str(ARMOUR1) and faction_text(page) == "Gloom Legion" and from_line(page))
        page.evaluate("() => closeScheme(false)")
        new_scheme(page)
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        before = page.evaluate("() => book.schemes.length")
        save(page, "No faction yet")
        state = page.evaluate("""() => { const w = document.querySelector('#scheme-page .scheme-faction'); const r = w.getBoundingClientRect();
            return { error: (w.querySelector('.scheme-faction-error') || {}).textContent || '', inView: r.top >= 0 && r.bottom <= innerHeight,
                     focused: document.activeElement === w.querySelector('input'), open: !!schemeDraft }; }""")
        check("blank faction + Save asks on the Faction row, scrolled into view, with its box focused",
              state["error"] == "Pick the faction this scheme is for." and state["inView"] and state["focused"], state)
        check("...and nothing is saved", state["open"] and page.evaluate("() => book.schemes.length") == before)
        page.fill("#scheme-page .scheme-faction input", "Lonely Host")
        page.click("#scheme-page .scheme-faction-row button")
        tick(page, ARMOUR1)
        check("a faction you chose is kept when you tick recipes", faction_text(page) == "Lonely Host" and not from_line(page), faction_text(page))
        tick(page, ARMOUR1)

        print("\n--- 3. Select all, Clear, search, Save count ---")
        check("Save reads Save scheme (0 recipes)", save_label(page) == "Save scheme (0 recipes)", save_label(page))
        group_button(page, "Trim").click()
        ticked = page.evaluate("() => schemeDraft.recipes.slice().sort()")
        check("Select all ticks every recipe in that group only", ticked == sorted(TRIM), ticked)
        check("...the button turns into Clear", group_button(page, "Trim").text_content() == "Clear")
        check("...and Save counts them live", save_label(page) == "Save scheme (5 recipes)", save_label(page))
        group_button(page, "Trim").click()
        check("Clear unticks the group and goes back to Select all",
              page.evaluate("() => schemeDraft.recipes.length") == 0 and group_button(page, "Trim").text_content() == "Select all")
        tick(page, EYES[0])
        check("one recipe: Save scheme (1 recipe)", save_label(page) == "Save scheme (1 recipe)", save_label(page))
        page.fill("#scheme-page .scheme-recipe-search", "eyes recipe 2")
        vis = page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-pick-row')].filter(l => l.offsetParent).map(l => l.textContent)")
        groups = page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-group')].filter(g => g.offsetParent).map(g => g.querySelector('h3').textContent)")
        check("typing filters the list as you type", vis == ["Eyes recipe 2"] and groups == ["Eyes"], (vis, groups))
        group_button(page, "Eyes").click()
        check("Select all with a search ticks only what is shown", sorted(page.evaluate("() => schemeDraft.recipes")) == sorted([EYES[0], EYES[1]]))
        page.fill("#scheme-page .scheme-recipe-search", "zzz")
        check("no match: one short line", page.locator("#scheme-page .hint", has_text="No recipes match.").is_visible()
              and page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-group')].every(g => !g.offsetParent)"))
        page.fill("#scheme-page .scheme-recipe-search", "")
        check("clearing the search shows all 22 again", page.evaluate("() => [...document.querySelectorAll('#scheme-page .scheme-pick-row')].filter(l => l.offsetParent).length") == 22)
        page.evaluate("() => closeScheme(false)")

        print("\n--- 4. Same-faction warning ---")
        new_scheme(page)
        tick(page, EYES[2])
        set_faction(page, "Lonely Host")
        check("schemes only in other factions: no warning", page.locator("#scheme-page .scheme-clash").count() == 0)
        set_faction(page, "gloom legion")
        note = page.locator("#scheme-page .scheme-clash")
        check("two schemes in one faction: the note names the other one",
              note.count() == 1 and note.locator("p").text_content() == "Gloom main already applies to new Gloom Legion units.", note.inner_text() if note.count() else "")
        check("...with the tick box Use this scheme for new units instead, unticked",
              note.locator("label").text_content().strip() == "Use this scheme for new units instead" and not note.locator("input").is_checked())
        geo = page.evaluate("""() => { const n = document.querySelector('#scheme-page .scheme-clash'), s = document.querySelector('#scheme-page .scheme-save');
            const l = n.querySelector('label').getBoundingClientRect(); const cs = getComputedStyle(n);
            return { above: n.getBoundingClientRect().bottom <= s.getBoundingClientRect().top, tap: l.height, border: cs.borderTopStyle }; }""")
        check("the note sits above Save, outlined, with a 44 px tick box", geo["above"] and geo["tap"] >= 43.5 and geo["border"] == "solid", geo)
        check("the outline is the amber caution colour", page.evaluate("""() => { const n = document.querySelector('#scheme-page .scheme-clash');
            const probe = document.createElement('i'); probe.style.color = 'var(--caution)'; n.appendChild(probe);
            const ok = getComputedStyle(probe).color === getComputedStyle(n).borderTopColor; probe.remove(); return ok; }"""))
        links_before = page.evaluate("() => models.map(m => (m.recipes || []).slice())")
        save(page, "Gloom second")
        check("unticked: the scheme is saved but does not attach", scheme(page, "Gloom second")["auto"] is False and scheme(page, "Gloom main")["auto"] is True)
        got = new_unit_recipes(page, "Gloom Legion")
        check("...a new unit gets the other scheme's recipes, not this one's", EYES[2] not in got and ARMOUR1 in got, got)
        page.evaluate("() => startScheme(book.schemes.find(s => s.name === 'Gloom second'))")
        quiet(page)
        check("the warning shows in Edit too", page.locator("#scheme-page .scheme-clash").count() == 1)
        page.check("#scheme-page .scheme-clash input")
        save(page, "Gloom second")
        check("ticked: this scheme attaches and the other one stops",
              scheme(page, "Gloom second")["auto"] is True and scheme(page, "Gloom main")["auto"] is False)
        check("...the other scheme is kept, and no unit changed",
              scheme(page, "Gloom main") is not None and page.evaluate("() => models.slice(0, 3).map(m => (m.recipes || []).slice())") == links_before)
        got = new_unit_recipes(page, "Gloom Legion")
        check("...a new unit now gets this scheme's recipes only", EYES[2] in got and ARMOUR2 not in got, got)
        check("the other scheme can still be applied by hand (its Apply button)",
              page.locator("#scheme-list .scheme-item", has_text="Gloom main").locator("button.primary-button").count() == 1)

        print("\n--- 5. Ask for a faction on schemes ---")
        start(page)
        page.evaluate("() => { showTab('settings'); openCardFold('recipe-prefs'); }")
        quiet(page)
        box = page.locator("#recipe-prefs-card #ask-scheme-faction")
        check("Recipe preferences has the switch Ask for a faction on schemes, on by default",
              box.is_checked() and "Ask for a faction on schemes" in page.locator("#recipe-prefs-card .scheme-faction-switch").text_content())
        check("its tap area is 44 px", page.evaluate("() => document.querySelector('#recipe-prefs-card .scheme-faction-switch').getBoundingClientRect().height") >= 43.5)
        box.click()
        check("turning it off is saved", page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).schemeFactionOff") is True)
        page.evaluate("() => { settings.lastFaction = 'Gloom Legion'; showTab('recipes'); }")
        new_scheme(page)
        check("off: the Faction row is hidden", page.locator("#scheme-page .scheme-faction").count() == 0)
        tick(page, EYES[3])
        save(page, "Any unit look")
        sc = scheme(page, "Any unit look")
        check("off: a scheme saves with no faction", sc is not None and sc["faction"] == "", sc)
        got = new_unit_recipes(page, "Gloom Legion") + new_unit_recipes(page, "")
        check("...and attaches to no new unit", EYES[3] not in got, got)
        check("...its card shows no empty faction words", "No  units" not in page.locator("#scheme-list").inner_text()
              and "new units get it" not in page.locator("#scheme-list .scheme-item", has_text="Any unit look").inner_text())
        page.evaluate("() => { openIds.add(3); showTab('units'); render(); }")
        quiet(page)
        opts = page.evaluate("() => [...document.querySelector('select[aria-label^=\"Link a recipe to\"]').options].map(o => o.textContent)")
        check("...and can be applied by hand from a unit's Link a recipe menu", "Apply scheme: Any unit look" in opts, opts)
        page.evaluate("() => { showTab('settings'); openCardFold('recipe-prefs'); }")
        quiet(page)
        page.locator("#recipe-prefs-card #ask-scheme-faction").click()
        page.evaluate("() => showTab('recipes')")
        new_scheme(page)
        check("on again: the Faction row is back", page.locator("#scheme-page .scheme-faction").count() == 1)
        page.evaluate("() => closeScheme(false)")

        print("\n--- 6. An older backup ---")
        old = page.evaluate("""(r) => { const b = cleanRecipeBook({ parts: ['Armour'], techniques: ['Layer'], paints: [{ id: 1, name: 'Grey', colour: '#888888' }],
              recipes: [{ id: 1, name: 'A', part: 'Armour', steps: [] }, { id: 2, name: 'B', part: 'Armour', steps: [] }],
              schemes: [{ id: 1, name: 'First', faction: 'Old Host', recipes: [1] }, { id: 2, name: 'Second', faction: 'Old Host', recipes: [2] }] });
            book = b; const m = addModel({ name: 'Old style', hobby: 'Test game', faction: 'Old Host' }); render();
            return { auto: b.schemes.map(s => s.auto), linked: (m.recipes || []).slice().sort() }; }""", None)
        check("schemes with no auto setting load as attaching", old["auto"] == [True, True], old)
        check("...so a new unit gets both, as today", old["linked"] == [1, 2], old)

        ctx.close()

        print("\n--- 7. Fit at three widths, dark and light ---")
        for mode in ("dark", "light"):
            c = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", color_scheme=mode)
            pg = c.new_page()
            pg.on("pageerror", lambda x: errors.append(str(x)))
            start(pg)
            pg.evaluate("() => startScheme(book.schemes.find(s => s.name === 'Gloom spare'))")
            for width, height in ((390, 844), (360, 640), (320, 640)):
                pg.set_viewport_size({"width": width, "height": height})
                quiet(pg)
                small = pg.evaluate(SMALL, "#scheme-page")
                check(f"{width}x{height} {mode}: no sideways scroll, tap targets 44 px, warning showing",
                      t.no_sideways(pg) and not small and pg.locator("#scheme-page .scheme-clash").count() == 1, small)
            c.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
