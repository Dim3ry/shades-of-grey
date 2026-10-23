"""v56 tests for Minifolio (chunk 1.1: one-step Clear examples).

What changed:
 Before v56 the "These are examples" card on the Dashboard and Units tab cleared or kept only the example units, and the card on the
 Recipes tab (also over Your Palette) only the example recipes, schemes and paints. Testers had to clear two or three times, and after
 Keep them on the Dashboard the card was still on the Recipes tab.
 Now every card is the same card: Clear examples removes all the examples at once (units, recipes, schemes and paints), the message says
 what was cleared, and one Undo brings all of it back. Keep them keeps all of them as your own, so the card goes away on every tab.

Checks:
1. Versions, the v56 Updates entry.
2. Clear examples on the Dashboard clears everything; the message says what; no card on any tab, also after a reload.
3. Undo brings back everything, with the links between units, recipes and schemes as they were.
4. Clear from the Recipes tab and from Your Palette does the same.
5. Keep them (Dashboard and Recipes tab) keeps everything; no card on any tab; Undo marks them as examples again.
6. What you made yourself is never touched; Restore in Settings still brings the card back.
7. The code and Help: one Clear and one Keep, the old per-card functions gone, Help says it.
8. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import fold_opener   # Your data (Restore example recipes) folds shut since v54
import test_v31 as t
import test_v44 as e   # fresh, existing, main_tab, recipe_view, toast, snap, restore_in_settings, own_recipe, and the example names

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = ["Captain", "Brutes", "Guardians"]
EVERYTHING = "3 example units, 5 example recipes, 2 example schemes and 16 example paints"
CARDS = {"dashboard": "#examples-card-dash", "units": "#examples-card", "recipes": "#examples-card-recipes"}

def counts(page):
    return page.evaluate("""() => ({ units: models.filter(m => m.example === true).length,
        recipes: book.recipes.filter(r => r.example === true).length, schemes: book.schemes.filter(s => s.example === true).length,
        paints: book.paints.filter(p => p.example === true).length })""")

def cards_seen(page):
    """Which tabs show the examples card (Your Palette counts as its own place)."""
    seen = []
    for name, sel in CARDS.items():
        e.main_tab(page, name)
        if page.locator(sel).is_visible(): seen.append(name)
    e.main_tab(page, "recipes")
    e.recipe_view(page, "palette")
    if page.locator(CARDS["recipes"]).is_visible(): seen.append("palette")
    e.recipe_view(page, "recipes")
    return seen

def tap(page, selector):
    page.locator(selector).scroll_into_view_if_needed()
    page.click(selector)
    page.wait_for_timeout(300)

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(300)

def links(page):
    """Each unit's linked recipe names, and each scheme's recipe names, by name (ids can change on Undo)."""
    return page.evaluate("""() => ({
        units: Object.fromEntries(models.map(m => [m.name, (m.recipes || []).map(id => (book.recipes.find(r => r.id === id) || {}).name)])),
        schemes: Object.fromEntries(book.schemes.map(s => [s.name, s.recipes.map(id => (book.recipes.find(r => r.id === id) || {}).name)])) })""")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)
        fold_opener.open_cards_on_load(page)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        e.fresh(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v56 or later", float(version[1:]) >= 56, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v56')")
        check("the v56 Updates entry exists and is the newest while v56 is current", bool(entry) and (version != "v56" or page.evaluate("CHANGELOG[0].version") == "v56"))
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry says Clear clears everything with one Undo, and Keep keeps everything on every tab",
              all(w in joined for w in ("Clear examples", "units, recipes, schemes and paints", "Undo", "Keep them", "Your Palette")), joined)
        check("no em dash in the v56 Updates entry", "—" not in app[app.index('{ version: "v56"'):app.index('{ version: "v55"')])

        # ---------- 2. Clear on the Dashboard ----------
        print("\n--- 2. Clear examples on the Dashboard clears everything ---")
        e.fresh(page)
        start = counts(page)
        check("a brand-new start has 3 example units, 5 recipes, 2 schemes and 16 paints",
              start == {"units": 3, "recipes": 5, "schemes": 2, "paints": 16}, start)
        check("before: the card is on the Dashboard, Units, Recipes and Your Palette",
              cards_seen(page) == ["dashboard", "units", "recipes", "palette"], cards_seen(page))
        e.main_tab(page, "dashboard")
        page.click("#examples-card-dash .more-info-button")
        info = page.text_content("#examples-card-dash .more-info-panel") or ""
        check("the explanation counts every kind and names the units", EVERYTHING in info and all(n in info for n in UNITS), info)
        before = links(page)
        tap(page, "#examples-card-dash .clear-examples")
        msg = e.toast(page)
        check("one tap: the message says everything that was cleared, with Undo",
              msg["text"] == f"Cleared {EVERYTHING}" and msg["shown"] and msg["undo"], msg)
        check("every example is gone: no units, recipes, schemes or paints left",
              page.evaluate("() => [models.length, book.recipes.length, book.schemes.length, book.paints.length]") == [0, 0, 0, 0],
              page.evaluate("() => [models.length, book.recipes.length, book.schemes.length, book.paints.length]"))
        check("the card is gone on every tab (Dashboard, Units, Recipes, Your Palette)", cards_seen(page) == [], cards_seen(page))
        e.main_tab(page, "recipes")
        e.recipe_view(page, "shopping")
        check("the shopping list has nothing from the examples", "Example" not in page.inner_text("#shop-panel"), page.inner_text("#shop-panel")[:200])
        e.recipe_view(page, "recipes")
        e.reload(page)
        check("still gone after a reload", cards_seen(page) == [] and counts(page) == {"units": 0, "recipes": 0, "schemes": 0, "paints": 0}, counts(page))
        check("…and the start-up seeding does not add them back", page.evaluate("() => book.recipes.length + models.length") == 0)

        # ---------- 3. Undo ----------
        print("\n--- 3. Undo brings everything back ---")
        e.fresh(page)
        before_snap, before = e.snap(page), links(page)
        e.main_tab(page, "dashboard")
        tap(page, "#examples-card-dash .clear-examples")
        undo(page)
        check("Undo brings back all 3 units, 5 recipes, 2 schemes and 16 paints", counts(page) == start, counts(page))
        check("…with every unit linked to the same recipes and every scheme holding the same recipes", links(page) == before, (links(page), before))
        check("…and the saved data is exactly as it was", e.snap(page) == before_snap)
        check("…and the unit order is as before", page.evaluate("() => models.map(m => m.name)") == UNITS, page.evaluate("() => models.map(m => m.name)"))
        check("the card is back on every tab", cards_seen(page) == ["dashboard", "units", "recipes", "palette"], cards_seen(page))

        # ---------- 4. Clear from the Recipes tab and Your Palette ----------
        print("\n--- 4. Clear from Recipes and Your Palette does the same ---")
        for view in ("recipes", "palette"):
            e.fresh(page)
            e.main_tab(page, "recipes")
            e.recipe_view(page, view)
            tap(page, "#examples-card-recipes .clear-recipe-examples")
            check(f"from {view}: the message says everything, units too", e.toast(page)["text"] == f"Cleared {EVERYTHING}", e.toast(page))
            check(f"from {view}: the example units are gone too, and the card is on no tab",
                  page.evaluate("() => models.length") == 0 and cards_seen(page) == [], cards_seen(page))
            undo(page)
            check(f"from {view}: Undo brings it all back", counts(page) == start, counts(page))
        e.fresh(page)
        e.main_tab(page, "units")
        tap(page, "#examples-card .clear-examples")
        check("from the Units tab: everything goes in one tap", counts(page) == {"units": 0, "recipes": 0, "schemes": 0, "paints": 0} and cards_seen(page) == [], counts(page))

        # ---------- 5. Keep them ----------
        print("\n--- 5. Keep them keeps everything ---")
        for where, sel in (("Dashboard", "#examples-card-dash .keep-examples"), ("Recipes tab", "#examples-card-recipes .keep-recipe-examples")):
            e.fresh(page)
            e.main_tab(page, "dashboard" if where == "Dashboard" else "recipes")
            tap(page, sel)
            msg = e.toast(page)
            check(f"Keep them on the {where}: the message says what was kept", msg["text"] == f"Kept {EVERYTHING} as your own", msg)
            check(f"Keep them on the {where}: nothing is marked as an example any more",
                  counts(page) == {"units": 0, "recipes": 0, "schemes": 0, "paints": 0}, counts(page))
            check(f"Keep them on the {where}: everything is still there", page.evaluate("() => [models.length, book.recipes.length, book.schemes.length, book.paints.length]") == [3, 5, 2, 16])
            check(f"Keep them on the {where}: the card is gone on every tab, Your Palette too", cards_seen(page) == [], cards_seen(page))
            e.reload(page)
            check(f"Keep them on the {where}: still gone after a reload", cards_seen(page) == [])
        e.fresh(page)
        e.main_tab(page, "dashboard")
        tap(page, "#examples-card-dash .keep-examples")
        undo(page)
        check("Undo after Keep them marks everything as an example again", counts(page) == start, counts(page))
        check("…and the card is back on every tab", cards_seen(page) == ["dashboard", "units", "recipes", "palette"], cards_seen(page))

        # ---------- 6. Yours is never touched; Restore ----------
        print("\n--- 6. What you made stays; Restore ---")
        e.fresh(page)
        e.own_recipe(page)
        page.evaluate("() => { models.push(...cleanModels([{ id: 50, name: 'My squad', hobby: 'Sci-fi', faction: 'Red army', stage: 0, count: 5 }])); render(); }")
        e.main_tab(page, "dashboard")
        tap(page, "#examples-card-dash .clear-examples")
        check("Clear leaves your own unit, recipe and paint",
              page.evaluate("() => [models.map(m => m.name), book.recipes.map(r => r.name), book.paints.map(p => p.name)]") == [["My squad"], ["My recipe"], ["My own paint"]],
              page.evaluate("() => [models.map(m => m.name), book.recipes.map(r => r.name), book.paints.map(p => p.name)]"))
        check("…and the card is gone everywhere", cards_seen(page) == [])
        e.restore_in_settings(page)
        check("Restore in Settings brings the example recipes back", counts(page)["recipes"] == 5, counts(page))
        msg_restore = e.toast(page)["text"]
        check("…and says what it added", msg_restore.startswith("Added 5 example recipes, 2 example schemes and 16 example paints"), msg_restore)
        check("…and the card shows again (units are not restored, so it counts only recipes, schemes and paints)",
              "recipes" in cards_seen(page) and "dashboard" in cards_seen(page), cards_seen(page))
        e.main_tab(page, "recipes")
        tap(page, "#examples-card-recipes .clear-recipe-examples")
        check("Clear after Restore: the message names only what there was", e.toast(page)["text"] == "Cleared 5 example recipes, 2 example schemes and 16 example paints", e.toast(page))
        e.fresh(page)
        page.evaluate("() => { const m = models[0]; delete m.example; render(); }")
        check("with one unit already yours, the card still counts the other two", "2 example units" in (page.text_content("#examples-card-dash") or ""),
              page.text_content("#examples-card-dash"))
        e.main_tab(page, "dashboard")
        tap(page, "#examples-card-dash .clear-examples")
        check("…and Clear leaves that unit", page.evaluate("() => models.map(m => m.name)") == ["Captain"], page.evaluate("() => models.map(m => m.name)"))

        # ---------- 7. Code and Help ----------
        print("\n--- 7. The code and Help ---")
        check("one clearExamples and one keepExamples", len(re.findall(r"function clearExamples\(", app)) == 1 and len(re.findall(r"function keepExamples\(", app)) == 1)
        check("the old per-card functions are gone", not re.search(r"function (clearRecipeExamples|keepRecipeExamples|exampleRecipeWords)\(", app))
        check("all three cards are filled by the same examplesCardParts", app.count("examplesCardParts(\"clear-") == 2 and len(re.findall(r"function examplesCardParts\(", app)) == 1)
        snippet = app[app.index("function examplesCardParts("):app.index("function clearExamples(")]
        check("the card code uses no innerHTML (text only)", "innerHTML" not in snippet)
        help_text = page.evaluate("() => document.getElementById('help-example-recipes').textContent")
        check("Help says Clear removes all the examples at once and Keep makes all of them yours",
              all(w in help_text for w in ("removes all the examples at once", "one Undo", "goes away on every tab")), help_text)

        # ---------- 8. No errors ----------
        print("\n--- 8. No errors ---")
        check("no page errors", not errors, errors[:3])
        check("no browser pop-ups were shown", not dialogs, dialogs[:3])
        browser.close()

    ok = all(results)
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
