"""v58 tests for Minifolio (chunk 1.3: kept example paints off the shopping list).

What changed:
 AI testers tapped Keep them on the examples card, then found made-up example paints such as "Example deep blue" on the shopping list
 as missing, because a kept example recipe uses them. No shop sells them, so the list looked broken and testers tried to buy them.
 v44 had deliberately let kept example paints count like any paint; v58 changes that decision. A paint that started as an example
 (one of the made-up names, no brand) never goes on the shopping list or into Copy as text, whether the examples were kept or not,
 and even with a status. A recipe that only needs made-up paints says "Uses example paints" instead of "Missing". Each made-up paint
 has "Swap for a real paint" in its More options on Your Palette (the same search box as the Compendium's Start from), which
 puts a real paint in every recipe that used it.

Checks:
1. Versions, the v58 Updates entry, Help.
2. After Keep them: no made-up paint on the list, on the Shopping page or in Copy as text (also with a status on one).
3. Real paints work as before: a real missing paint, a wishlist paint and a running low paint are on the list.
4. The recipe card line: "Uses example paints" for an example-only recipe, "Missing 1" when a real paint is missing; no cross on made-up paints.
5. Swap for a real paint: only on made-up paints; picking a real paint swaps it in every recipe, removes the made-up one, Undo puts it back.
6. Renaming a made-up paint or giving it a brand makes it an ordinary paint (it can go on the list again).
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
from combo_helpers import pick_combo
import test_v31 as t
import test_v44 as e   # fresh, main_tab, recipe_view, toast, own_recipe

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def list_names(page):
    return page.evaluate("() => shoppingItems().map(i => i.paint.name)")

def copied(page):
    """Presses Copy as text on the Shopping page and returns what went to the clipboard."""
    page.evaluate("() => { window.__copied = null; navigator.clipboard.writeText = (x) => { window.__copied = x; return Promise.resolve(); }; }")
    e.main_tab(page, "recipes")
    e.recipe_view(page, "shopping")
    button = page.locator("#shop-panel button:has-text('Copy as text')")
    if not button.count():   # an empty list has no Copy as text button: the words it would copy
        return page.evaluate("() => shoppingText(shoppingItems())")
    button.click()
    page.wait_for_timeout(150)
    return page.evaluate("() => window.__copied") or ""

def kept(page):
    """A brand-new start, then Keep them on the card (real taps)."""
    e.fresh(page)
    e.main_tab(page, "recipes")
    page.click("#examples-card-recipes .keep-recipe-examples")
    page.wait_for_timeout(300)

def paint_id(page, name):
    return page.evaluate("(n) => (book.paints.find(p => p.name === n) || {}).id", name)

def open_paint(page, pid):
    """Your Palette, with this paint opened and its More options showing."""
    page.evaluate("""pid => { settings.recipeView = 'palette'; showTab('recipes');
                     openPaintIds.clear(); openPaintIds.add(pid); render(); }""", pid)
    page.evaluate("() => document.querySelectorAll('.paint-options .more-info-button[aria-expanded=false]').forEach(b => b.click())")
    page.wait_for_timeout(100)

def card_status(page, recipe):
    e.main_tab(page, "recipes")
    e.recipe_view(page, "recipes")
    return page.evaluate("""(n) => { const card = [...document.querySelectorAll('#recipe-list .recipe-card')]
        .find(c => c.querySelector('.name').textContent === n); const s = card && card.querySelector('.recipe-status');
        return s ? s.textContent : null; }""", recipe)

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

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions, the Updates entry and Help ---")
        e.fresh(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v58 or later", float(version[1:]) >= 58, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comments that name the number agree", f'The "?v={version[1:]}" makes' in html and f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v58')")
        check("the v58 Updates entry exists and is the newest while v58 is current", bool(entry) and (version != "v58" or page.evaluate("CHANGELOG[0].version") == "v58"))
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names the shopping list, Copy as text, Uses example paints and Swap for a real paint",
              all(w in joined for w in ("shopping list", "Copy as text", "Uses example paints", "Swap for a real paint")), joined)
        check("no em dash in the v58 Updates entry", "—" not in app[app.index('{ version: "v58"'):app.index('{ version: "v57"')])
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        help_text = page.text_content("#help-example-recipes") or ""
        check("Help says made-up paints stay off the list after Keep them, and how to swap one",
              all(w in help_text for w in ("even after Keep them", "Uses example paints", "Swap for a real paint")), help_text[-300:])

        # ---------- 2. After Keep them ----------
        print("\n--- 2. After Keep them: no made-up paint on the list ---")
        kept(page)
        check("Keep them took the example mark off every paint", page.evaluate("() => book.paints.every(p => p.example !== true)"))
        check("the sixteen paints are still made-up", page.evaluate("() => book.paints.filter(isMadeUpPaint).length") == 16)
        check("none of them is on the shopping list", list_names(page) == [], list_names(page))
        e.main_tab(page, "recipes")
        e.recipe_view(page, "shopping")
        shop = page.inner_text("#shop-panel")
        check("the Shopping page names no example paint and says there is nothing to buy", "Example" not in shop and "Nothing to buy" in shop, shop[:200])
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example deep blue'), 'wishlist'); render(); }")
        check("a kept made-up paint put on the wishlist still stays off the list", list_names(page) == [], list_names(page))
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example mid blue'), 'empty'); render(); }")
        check("and so does one marked empty", list_names(page) == [], list_names(page))
        text = copied(page)
        check("Copy as text has no example paint in it", text.startswith("Shopping list") and "Example" not in text, text)
        e.fresh(page)
        check("before Keep them the examples are off the list too (as since v24)", list_names(page) == [], list_names(page))
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Example pale grey'), 'wishlist'); render(); }")
        check("a made-up paint given a status before Keep them stays off the list", list_names(page) == [], list_names(page))

        # ---------- 3. Real paints work as before ----------
        print("\n--- 3. Real paints work as before ---")
        kept(page)
        e.own_recipe(page, "My armour", "Real Blue", "#2244aa")
        page.evaluate("""() => { const p = book.paints.find(x => x.name === 'Real Blue'); p.brand = 'Test Paints';
            const w = findOrAddPaint('Test Paints', 'Wish Green', '#22aa44'); applyPaintStatus(w, 'wishlist');
            const l = findOrAddPaint('Test Paints', 'Low Red', '#aa2222'); applyPaintStatus(l, 'low'); render(); }""")
        got = list_names(page)
        check("a real paint your recipe needs, a wishlist paint and a running low paint are on the list, and nothing made-up",
              sorted(got) == ["Low Red", "Real Blue", "Wish Green"], got)
        reasons = page.evaluate("() => Object.fromEntries(shoppingItems().map(i => [i.paint.name, i.reason]))")
        check("with the same reasons as before", reasons == {"Real Blue": "missing, used in 1 recipe", "Wish Green": "wishlist", "Low Red": "running low"}, reasons)
        text = copied(page)
        check("Copy as text lists the real ones, under their brand", "Test Paints" in text and all(n in text for n in ("Real Blue", "Wish Green", "Low Red"))
              and "Example" not in text, text)

        # ---------- 4. The recipe card line ----------
        print("\n--- 4. Have / Missing on a recipe ---")
        # The line shows once any paint has a status (Low Red above).
        check("Blue armour (only made-up paints) says Uses example paints", card_status(page, "Blue armour") == "Uses example paints", card_status(page, "Blue armour"))
        check("so does Stone base", card_status(page, "Stone base") == "Uses example paints", card_status(page, "Stone base"))
        check("your own recipe with a real missing paint still says Missing 1", card_status(page, "My armour") == "Missing 1", card_status(page, "My armour"))
        check("no recipe card says Missing for made-up paints",
              page.evaluate("() => [...document.querySelectorAll('#recipe-list .recipe-status')].filter(s => s.textContent.startsWith('Missing')).length") == 1)
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Real Blue'), 'owned'); render(); }")
        check("once you own it, your recipe says Have all", card_status(page, "My armour") == "Have all", card_status(page, "My armour"))
        mixed = page.evaluate("""() => { const r = book.recipes.find(x => x.name === 'Blue armour');
            r.steps.push({ technique: 'Layer', coats: 1, paints: [{ paint: findOrAddPaint('Test Paints', 'Real Teal', '#118888').id, mix: null }], ratio: '', note: '', optional: false });
            render(); return r.id; }""")
        check("a recipe with made-up paints and a real missing one says Missing 1", card_status(page, "Blue armour") == "Missing 1", card_status(page, "Blue armour"))
        page.evaluate("(id) => { openRecipeId = id; renderRecipes(); document.querySelectorAll('#recipe-page .step-line').forEach(b => b.click()); }", mixed)
        page.wait_for_timeout(150)
        marks = page.evaluate("""() => [...document.querySelectorAll('#recipe-page .paint-line')].map(l => [l.childNodes[1].textContent, !!l.querySelector('.have-mark')])""")
        check("in the open recipe, made-up paints have no tick or cross and the real one has its cross",
              all(not has for name, has in marks if name.startswith("Example")) and ["Real Teal", True] in marks, marks)
        lines = page.evaluate("() => [...document.querySelectorAll('#recipe-page .step-line')].map(b => !!b.querySelector('.have-mark.missing'))")
        check("only the step with the real missing paint is marked Missing a paint", lines == [False, False, False, False, True], lines)
        page.evaluate("() => { openRecipeId = null; renderRecipes(); }")

        # ---------- 5. Swap for a real paint ----------
        print("\n--- 5. Swap for a real paint ---")
        kept(page)
        blue = paint_id(page, "Example deep blue")
        open_paint(page, blue)
        swap = page.locator(".paint-options .swap-real")
        check("a made-up paint's More options has Swap for a real paint", swap.count() == 1 and swap.inner_text() == "Swap for a real paint")
        check("the box is shut until you tap it", swap.get_attribute("aria-expanded") == "false" and page.locator(f"#swap-{blue}-pick").count() == 0)
        swap.click()
        page.wait_for_timeout(100)
        check("tapping it opens the paint search box", page.locator(f"#swap-{blue}-pick").is_visible() and swap.get_attribute("aria-expanded") == "true")
        check("the hint says why", "made-up example" in page.inner_text(".swap-box"))
        groups = page.evaluate(f"""() => {{ document.getElementById('swap-{blue}-pick').click(); return [...document.querySelectorAll('#swap-{blue}-pick-list .combo-group')].map(g => g.textContent); }}""")
        check("it lists real paints from the built-in list, by brand", any(g.startswith("More ") for g in groups), groups)
        options = page.evaluate(f"() => [...document.querySelectorAll('#swap-{blue}-pick-list [role=option]')].map(o => o.textContent)")
        check("no made-up paint is offered", not any(o.startswith("Example ") for o in options), options[:5])
        real = page.evaluate("() => { const k = searchedPaints.find(x => x.brand && x.colour && !book.paints.some(p => sameText(p.name, x.name))); return { name: k.name, brand: k.brand }; }")
        page.keyboard.press("Escape")
        before = page.evaluate("() => JSON.stringify(book)")
        pick_combo(page, f"#swap-{blue}-pick", text=f"{real['name']} ({real['brand']})", wait=300)
        now = page.evaluate("""(r) => { const p = book.paints.find(x => x.name === r.name && x.brand === r.brand);
            const uses = book.recipes.filter(x => x.steps.some(s => s.paints.some(sp => p && sp.paint === p.id))).map(x => x.name);
            return { there: !!p, uses, gone: !book.paints.some(x => x.name === 'Example deep blue') }; }""", real)
        check("the real paint is in your palette and Blue armour uses it", now["there"] and now["uses"] == ["Blue armour"], now)
        check("Example deep blue has left your palette", now["gone"], now)
        check("the message says what was swapped, with Undo", e.toast(page)["shown"] and e.toast(page)["undo"]
              and e.toast(page)["text"] == f"Swapped Example deep blue for {real['name']}", e.toast(page))
        check("the real paint can go on the shopping list now (you don't have it)", list_names(page) == [real["name"]], list_names(page))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo puts everything back", page.evaluate("() => JSON.stringify(book)") == before)
        own = page.evaluate("() => { const p = findOrAddPaint('Test Paints', 'Plain Real', '#335577'); render(); return p.id; }")
        open_paint(page, own)
        check("a real paint has no Swap button", page.locator(".paint-options .swap-real").count() == 0)
        # swapping to a paint already in your palette keeps its status
        page.evaluate("() => { applyPaintStatus(book.paints.find(p => p.name === 'Plain Real'), 'owned'); render(); }")
        wash = paint_id(page, "Example dark wash")
        open_paint(page, wash)
        page.click(".paint-options .swap-real")
        page.wait_for_timeout(100)
        pick_combo(page, f"#swap-{wash}-pick", text="Plain Real (Test Paints)", wait=300)
        after = page.evaluate("""() => { const p = book.paints.find(x => x.name === 'Plain Real');
            return { status: paintStatus(p), uses: book.recipes.filter(r => r.steps.some(s => s.paints.some(sp => sp.paint === p.id))).map(r => r.name).sort(),
                     dupes: book.paints.filter(x => x.name === 'Plain Real').length }; }""")
        check("swapping to a palette paint uses it in both recipes that had the dark wash, keeps it owned and adds no copy",
              after == {"status": "owned", "uses": ["Blue armour", "Gold metal"], "dupes": 1}, after)
        saved = e.saved_book(page)
        check("the swap is saved", not any(q["name"] == "Example dark wash" for q in saved["paints"]))

        # ---------- 6. Renamed or branded ----------
        print("\n--- 6. A made-up paint you rename or give a brand ---")
        kept(page)
        page.evaluate("() => { const p = book.paints.find(x => x.name === 'Example mid green'); p.brand = 'Test Paints'; applyPaintStatus(p, 'wishlist'); render(); }")
        check("given a brand, it is an ordinary paint and can go on the list", list_names(page) == ["Example mid green"], list_names(page))
        page.evaluate("() => { const p = book.paints.find(x => x.name === 'Example bright green'); p.name = 'My bright green'; applyPaintStatus(p, 'wishlist'); render(); }")
        check("renamed, it is an ordinary paint too", sorted(list_names(page)) == ["Example mid green", "My bright green"], list_names(page))

        # ---------- 7. Safety ----------
        print("\n--- 7. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
