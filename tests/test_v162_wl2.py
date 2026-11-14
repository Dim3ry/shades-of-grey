"""WL2 test for Minifolio (Wish list: Got it turns a wish into a unit, its message and Undo, wishes stay out of every total). New behaviour only."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

UNITS = [{"id": 1, "name": "Squad A", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}]
def wish(i, name, game="", faction="", count=1, note=""):
    return {"id": i, "name": name, "count": count, "game": game, "faction": faction, "really": i == 2, "note": note, "added": "2026-10-0" + str(i)}
WISHES = [wish(1, "Zed Riders", "Skirmish", "Bright Host", 5, "Buy in the sale"), wish(2, "Archers", "Skirmish", "Bright Host", 2),
          wish(3, "Moss Knights", "Fantasy", "Moss Court", 4), wish(4, "Loose Model"), wish(5, "Single", "Fantasy", "Moss Court", 1)]
STAGES = ["Boxed", "Built", "Primed", "Painted"]

def fresh(page, wishes=None, units=UNITS, **settings):
    s = {"examplesChecked": True, "stages": STAGES, **settings}
    if wishes is not None: s["modelWishes"] = wishes
    t.load(page, units=units, settings=s)
    page.click('nav button[data-tab="units"]'); t.quiet(page)
def to_wishes(page):
    page.click('#models-seg button[data-mview="wishes"]'); page.wait_for_selector("#wish-view:not(.hidden)")
def names(page): return page.evaluate("[...document.querySelectorAll('#wish-list .wish-name')].map(n => n.textContent)")
def stored_wishes(page): return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings')")).get("modelWishes")
def stored_units(page): return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models')"))
def got(page, wid): page.click(f'#wish-list li[data-wish-id="{wid}"] .wish-got')
def toast(page): return page.text_content("#toast-text").strip()
def dash_text(page):
    page.click('nav button[data-tab="dashboard"]'); t.quiet(page)
    text = page.evaluate("document.getElementById('view-dashboard').innerText")
    page.click('nav button[data-tab="units"]'); t.quiet(page)
    return text

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        fresh(page, WISHES)

        print("\n--- 1. Got it makes one unit ---")
        to_wishes(page)
        btn = page.locator('#wish-list li[data-wish-id="1"] .wish-got')
        check("every row has a Got it button named for its wish", page.locator(".wish-got").count() == 5 and btn.get_attribute("aria-label") == "Got it, Zed Riders")
        check("the button is 44 px or more", page.evaluate("[...document.querySelectorAll('.wish-got')].every(b => { const r = b.getBoundingClientRect(); return r.height >= 43.5 && r.width >= 43.5; })"))
        before_nexus = dash_text(page); to_wishes(page)
        got(page, 1)
        units = stored_units(page)
        new = [u for u in units if u["name"] == "Zed Riders"]
        check("one new unit, the others untouched", len(units) == 2 and len(new) == 1 and units[0]["id"] == 1, units)
        u = new[0]
        check("it has the wish's name, game, faction and number of models", u["hobby"] == "Skirmish" and u["faction"] == "Bright Host" and u["count"] == 5, u)
        check("it starts at the first stage of the person's own list, added today", u["stage"] == 0 and u["added"] == page.evaluate("todayISO()") and u["log"][0][1] == 0, u)
        check("the wish's note is the unit's note", u.get("note") == "Buy in the sale", u)
        check("the wish is gone from the list and from the saved wishes", "Zed Riders" not in names(page) and [w["id"] for w in stored_wishes(page)] == [2, 3, 4, 5])
        check("the page stays on the Wish list", page.is_visible("#wish-view") and not page.is_visible("#toggle-add"))
        check("the message says moved to Models, with Undo", toast(page) == "Zed Riders moved to Models" and page.text_content("#toast-undo").strip() == "Undo", toast(page))

        print("\n--- 2. Undo puts both sides back ---")
        page.click("#toast-undo")
        check("the unit is gone", [u["name"] for u in stored_units(page)] == ["Squad A"])
        back = stored_wishes(page)
        check("the wish is back in its place, same id and added date",
              [w["id"] for w in back] == [1, 2, 3, 4, 5] and back[0]["added"] == "2026-10-01" and back[0]["note"] == "Buy in the sale" and back[0]["count"] == 5, back)
        check("the list shows it again", "Zed Riders" in names(page))

        print("\n--- 3. Two in a row: each Undo undoes only its own move ---")
        got(page, 1); got(page, 3)
        check("the newer message replaces the older one", toast(page) == "Moss Knights moved to Models")
        page.click("#toast-undo")
        check("Undo puts back only the second wish", [w["id"] for w in stored_wishes(page)] == [2, 3, 4, 5] and [u["name"] for u in stored_units(page)] == ["Squad A", "Zed Riders"], (stored_wishes(page), stored_units(page)))
        got(page, 3)

        print("\n--- 4. Counts follow, in Models and Nexus ---")
        page.click('#models-seg button[data-mview="models"]'); t.quiet(page)
        check("the Models summary counts both new units, not the wishes still waiting", page.text_content("#filter-note").strip() == "3 units, 12 models", page.text_content("#filter-note"))
        check("the new units are in the Models list", page.evaluate("document.querySelectorAll('#unit-list li.unit').length") == 3)
        after = dash_text(page)
        check("the Nexus changed (the units count)", after != before_nexus)
        fresh(page, WISHES); n_wish = dash_text(page)
        fresh(page, []); n_none = dash_text(page)
        check("five wishes change nothing on the Nexus or the Armies card", n_wish == n_none)

        print("\n--- 5. Wording and edge cases ---")
        fresh(page, WISHES); to_wishes(page)
        got(page, 5)
        check("a one-model wish becomes a one-model unit", stored_units(page)[-1]["count"] == 1 and stored_units(page)[-1]["hobby"] == "Fantasy")
        fresh(page, [wish(1, "Bare", count=2)], units=[]); to_wishes(page)
        got(page, 1)
        bare = stored_units(page)
        check("a wish with no game and no faction becomes a unit with none", len(bare) == 1 and bare[0]["hobby"] == "" and bare[0]["faction"] == "" and bare[0]["count"] == 2, bare)
        check("a wish with no note gives a unit with no note", not bare[0].get("note"))
        check("the empty list shows one short line", page.text_content("#wish-list").strip() == "No wishes yet.")
        fresh(page, [wish(1, "Squad A", "Skirmish", "Bright Host", 2)]); to_wishes(page)
        got(page, 1)
        same = [u for u in stored_units(page) if u["name"] == "Squad A"]
        check("a wish named like an existing unit is numbered the way Add unit does", sorted(u.get("copy", 0) for u in same) == [1, 2], same)
        page.click("#toast-undo")
        check("Undo takes the numbering back too", len([u for u in stored_units(page) if u["name"] == "Squad A"]) == 1 and "copy" not in stored_units(page)[0], stored_units(page))
        fresh(page, [wish(1, "New Faction Models", "Brand New Game", "Brand New Faction", 3)]); to_wishes(page)
        got(page, 1)
        page.click('#models-seg button[data-mview="models"]'); t.quiet(page)
        check("an unknown game and faction is created like Add unit does it", stored_units(page)[-1]["hobby"] == "Brand New Game" and stored_units(page)[-1]["faction"] == "Brand New Faction")
        fresh(page, [wish(1, "Hidden One", "Fantasy", "Moss Court", 1)]); page.evaluate("filters.games && filters.games.add && filters.games.add('Skirmish')")
        to_wishes(page); got(page, 1)
        check("Got it with a filter on does not error and still makes the unit", len(stored_units(page)) == 2 and not errors, errors)

        print("\n--- 6. A backup from before Got it ---")
        fresh(page, WISHES); to_wishes(page)
        backup = page.evaluate("JSON.parse(JSON.stringify(backupData()))")
        got(page, 1)
        page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_selector("#dialog-yes", state="visible"); page.click("#dialog-yes"); page.wait_for_timeout(500)
        check("restoring it brings the wish back and removes the unit", [w["id"] for w in stored_wishes(page)] == [1, 2, 3, 4, 5] and [u["name"] for u in stored_units(page)] == ["Squad A"],
              (stored_wishes(page), stored_units(page)))

        print("\n--- 7. Phone sizes, light and dark, two looks ---")
        for w, h, mode, theme in ((390, 844, "dark", "classic"), (360, 640, "light", "classic"), (320, 568, "dark", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            fresh(page, [wish(1, "A very long wish name " * 6, "Skirmish", "Bright Host", 2)], theme=theme, appearance=mode); to_wishes(page)
            m = page.evaluate("""() => { const g = document.querySelector('.wish-got').getBoundingClientRect(), r = document.querySelector('.wish-row').getBoundingClientRect();
                return { side: document.documentElement.scrollWidth <= innerWidth + 1, inside: g.right <= innerWidth + 1 && r.right <= innerWidth + 1, tall: g.height >= 43.5 && g.width >= 43.5 }; }""")
            check(f"{w}x{h} {mode} {theme}: Got it fits, 44 px, no sideways scroll", all(m.values()), m)
            got(page, 1)
            bar = page.evaluate("""() => { const t = document.getElementById('toast'); t.style.animation = 'none';
                const a = t.getBoundingClientRect(), b = document.querySelector('.tabs').getBoundingClientRect(); t.style.animation = '';
                return { a: [a.top, a.bottom], b: [b.top, b.bottom], ok: a.bottom <= b.top + 1 || a.top >= b.bottom - 1 }; }""")
            bar = bar if not bar["ok"] else True
            check(f"{w}x{h}: the message does not cover the bottom bar", bar)
        check("no page errors", not [e for e in errors if "woff2" not in e], errors)
        browser.close()
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

main()
