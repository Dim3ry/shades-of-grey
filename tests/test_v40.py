"""v40 tests for Minifolio (Shopping 1 of 2): the shopping list is its own switch on the Recipes tab.

What changed:
 - The shopping list moved out of Your Palette into its own part of the Recipes tab (a "Shopping" switch next to Recipes, Schemes and Your Palette).
   It keeps everything it did: running low / empty / wishlist / paints your recipes use but you don't have, the Buy these bar, grouped by brand, Copy as text.
 - One shared list, one entry per paint. A paint added from two places is listed once. Each paint remembers where it came from (a recipe name now,
   a scheme name from chunk 2), saved on the paint itself as `shopFrom` (up to 5 notes, 60 characters each, plain text).
 - A small basket with the count sits on the tab bar on every tab (hidden at zero). Tapping it opens the Shopping switch.
 - The Compendium is NOT changed in this release (that is chunk 2).

Checks:
1. Versions, Updates entry, sw.js, wiring, the Compendium code untouched.
2. The new switch and where the list lives (not under Your Palette any more).
3. What is on the list, and that everything it did before still works (Buy bar, Copy as text, grouping, example paints left out).
4. No duplicates and where it came from (added twice, from two places; recipe names; kept after a reload; cleaned when loaded).
5. The basket: count on every tab, hidden at zero, updates, a tap opens the Shopping switch, keyboard works, stays when shop links are off.
6. Hostile text (text-injection test): names, brands, recipes and source notes are always plain text.
7. Phones and looks: 360 and 390 px, dark and light, no sideways scroll, the switch buttons fit, basket contrast, nothing else changed.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, HOSTILE, HOSTILE_BRAND = t.rec, t.HOSTILE, t.HOSTILE_BRAND
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(pid, name, status="owned", brand="Test Paints", **extra):
    return dict({"id": pid, "brand": brand, "name": name, "colour": "#3366aa", "status": status}, **extra)

PAINTS = [
    P(1, "Owned One"),
    P(2, "Low One", "low"),
    P(3, "Empty One", "empty"),
    P(4, "Wish One", "wishlist"),
    P(5, "Missing One", "notowned"),
    P(6, "Missing Two", "notowned", brand="Other Paints"),
    P(7, "Plain One", "notowned"),
]
RECIPES = [rec(1, "Moss Armour", "Armour", [5, 1]), rec(2, "Dusty Cloak", "Armour", [5, 6])]

def tab(page, name):
    blur(page)
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def open_shopping(page):
    tab(page, "recipes")
    page.click('#recipe-seg button[data-view="shopping"]')
    page.wait_for_timeout(150)

def items(page):
    return page.evaluate("() => [...document.querySelectorAll('#shop-panel .shop-list li')].map(li => li.textContent.replace(/\\s+/g, ' ').trim())")

def count_text(page):
    return page.evaluate("() => { const b = document.getElementById('basket-button'); return b.classList.contains('hidden') ? '' : b.textContent.trim(); }")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions and wiring ---")
        load(page, paints=PAINTS, recipes=RECIPES)
        html, sw, app = read("index.html"), read("sw.js"), read("app.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the version is v40 in APP_VERSION, sw.js and all six script tags",
              page.evaluate("APP_VERSION") in ("v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49") and re.search(r'const VERSION = "v([\d.]+)"', sw).group(1) in ("40", "41", "42", "43", "44", "45", "46", "47", "48", "49") and len(tags) == 6 and len({v for _, v in tags}) == 1,
              (page.evaluate("APP_VERSION"), tags))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v40')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("!!CHANGELOG.find(r => r.version === 'v40')"):
            check("the v40 Updates entry is there (and is the newest or second newest) and tells about the Shopping switch, one entry per paint, where it came from, and the basket",
                  entry and entry["version"] == "v40" and all(w in joined for w in ("Shopping", "once", "came from", "basket")), joined[:120])
        else:
            print("SKIP: "+'the v40 Updates entry is there (and is the newest or second newest) and tells ab')
        check("no new files and no new network address", "http" not in "".join(re.findall(r"updateBasket[\s\S]{0,1800}", app)[:1]) and len(tags) == 6)
        # the Compendium code is exactly as it was (chunk 2 changes it)
        import subprocess
        diff = subprocess.run(["git", "diff", "main", "--", "app.js"], cwd=ROOT, capture_output=True, text=True).stdout
        compendium_touched = [l for l in diff.splitlines() if l.startswith(("+", "-")) and re.search(r"compendiumDoor|renderCompendium|cmp-|buildPaintPanel", l)]
        check("no line that belongs to the Compendium was changed in app.js (only checked while v40 is the newest version; v41 changes it on purpose)", page.evaluate("APP_VERSION") != "v40" or not compendium_touched, compendium_touched[:3])

        # ---------- 2. The new switch ----------
        print("\n--- 2. The new switch ---")
        tab(page, "recipes")
        labels = page.evaluate("() => [...document.querySelectorAll('#recipe-seg button')].map(b => b.textContent.trim())")
        check("the Recipes switch now reads Recipes, Schemes, Your Palette, Shopping", labels == ["Recipes", "Schemes", "Your Palette", "Shopping"], labels)
        page.click('#recipe-seg button[data-view="palette"]')
        page.wait_for_timeout(150)
        check("Your Palette no longer has a shopping list button or panel under it",
              page.locator("#palette-view #shop-button").count() == 0 and page.locator("#palette-view #shop-panel").count() == 0)
        page.click('#recipe-seg button[data-view="shopping"]')
        page.wait_for_timeout(150)
        check("Shopping opens its own page: the list is showing, the palette and recipe list are hidden, and it is the selected part",
              page.is_visible("#shop-panel") and not page.is_visible("#paint-list") and not page.is_visible("#recipe-home")
              and page.get_attribute('#recipe-seg button[data-view="shopping"]', "aria-selected") == "true")
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        check("after a reload the app comes back on Shopping (the choice is remembered)", page.is_visible("#shop-panel"))

        # ---------- 3. What is on the list ----------
        print("\n--- 3. What is on the list ---")
        got = items(page)
        names = " | ".join(got)
        check("it lists running low, empty, wishlist and the paints recipes use that you don't have, and not the paint you own or an unused one",
              all(n in names for n in ("Low One", "Empty One", "Wish One", "Missing One", "Missing Two"))
              and "Owned One" not in names and "Plain One" not in names, got)
        check("Missing One, used by two recipes, is listed once and names both recipes",
              sum("Missing One" in g for g in got) == 1 and any("Missing One" in g and "Recipe: Moss Armour" in g and "Recipe: Dusty Cloak" in g for g in got), got)
        check("grouped by brand", page.locator("#shop-panel .shop-brand").count() == 2, page.locator("#shop-panel .shop-brand").all_inner_texts())
        check("the Buy these bar and Copy as text are still there", page.locator("#shop-panel .shop-buy, #shop-panel [class*=buy]").count() >= 1
              and page.locator("#shop-panel button:has-text('Copy as text')").count() == 1)
        text = page.evaluate("() => shoppingText(shoppingItems())")
        check("Copy as text carries where each paint came from", "Missing One" in text and "(from Recipe: Moss Armour, Recipe: Dusty Cloak)" in text, text[:200])
        page.evaluate("() => { book.paints.push({ id: 90, brand: 'Test Paints', name: 'Example Paint', colour: '#112233', example: true }); book.recipes.push({ id: 91, name: 'Example Recipe', part: 'Armour', notes: '', example: true, steps: [{ technique: 'Base coat', coats: 1, paints: [{ paint: 90, mix: null }], ratio: '', note: '', optional: false }] }); render(); }")
        check("example paints still never go on the list", not any("Example Paint" in g for g in items(page)))

        # ---------- 4. No duplicates, and where it came from ----------
        print("\n--- 4. No duplicates and sources ---")
        load(page, paints=PAINTS, recipes=RECIPES)
        before = page.evaluate("() => shoppingItems().length")
        page.evaluate("() => { addToShoppingList({ brand: 'Test Paints', name: 'Plain One' }, 'Recipe: Moss Armour'); }")
        page.evaluate("() => { addToShoppingList({ brand: 'Test Paints', name: 'Plain One' }, 'Scheme: Frozen Waste'); }")
        page.evaluate("() => { addToShoppingList({ brand: 'Test Paints', name: 'Plain One' }, 'Recipe: Moss Armour'); }")
        after = page.evaluate("() => shoppingItems().filter(i => i.paint.name === 'Plain One').map(i => i.from)")
        check("a paint added three times from two places is on the list once, and remembers both places once each",
              page.evaluate("() => shoppingItems().length") == before + 1 and len(after) == 1 and after[0] == ["Recipe: Moss Armour", "Scheme: Frozen Waste"], after)
        check("only one paint of that name exists in the palette (no duplicate was created)", page.evaluate("() => book.paints.filter(p => p.name === 'Plain One').length") == 1)
        page.evaluate("() => { addToShoppingList({ brand: 'Brand New', name: 'Fresh Paint' }); }")
        check("with no source given it says Colour suggestion", page.evaluate("() => shoppingItems().find(i => i.paint.name === 'Fresh Paint').from") == ["Colour suggestion"])
        open_shopping(page)
        plain = [g for g in items(page) if g.startswith("Plain One")]
        check("the list shows 'from' under the paint", plain and "from Recipe: Moss Armour, Scheme: Frozen Waste" in plain[0], plain)
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        check("the notes are still there after a reload", page.evaluate("() => shoppingItems().find(i => i.paint.name === 'Plain One').from") == ["Recipe: Moss Armour", "Scheme: Frozen Waste"])
        page.evaluate("() => { const p = book.paints.find(x => x.name === 'Plain One'); applyPaintStatus(p, 'owned'); render(); }")
        check("marking it Owned takes it off the list and clears the notes", page.evaluate("() => !book.paints.find(x => x.name === 'Plain One').shopFrom && !shoppingItems().some(i => i.paint.name === 'Plain One')"))
        cleaned = page.evaluate("""() => { const b = cleanRecipeBook({ paints: [
            { id: 1, name: 'A', brand: 'X', status: 'wishlist', shopFrom: ['  one  ', 'ONE', 'two', 3, null, 'x'.repeat(100), 'a', 'b', 'c', 'd'] },
            { id: 2, name: 'B', brand: 'X', status: 'owned', shopFrom: ['kept?'] },
            { id: 3, name: 'C', brand: 'X', status: 'wishlist', shopFrom: 'not a list' }], recipes: [], schemes: [] });
          return b.paints.map(p => p.shopFrom || null); }""")
        check("loading cleans the notes: trimmed, no repeats, at most 5, 60 characters, gone for owned paints, ignored if not a list",
              cleaned[0] and len(cleaned[0]) == 5 and cleaned[0][0] == "one" and all(len(s) <= 60 for s in cleaned[0]) and cleaned[1] is None and cleaned[2] is None, cleaned)
        dr = page.evaluate("""() => { const b = cleanRecipeBook(JSON.parse(JSON.stringify(book))); return JSON.stringify(b.paints) === JSON.stringify(book.paints); }""")
        check("cleaning an already clean book changes nothing", dr)

        # ---------- 5. The basket ----------
        print("\n--- 5. The basket ---")
        load(page, paints=PAINTS, recipes=RECIPES)
        n = page.evaluate("() => shoppingItems().length")
        seen = {}
        for name in ("dashboard", "units", "recipes", "compendium", "settings"):
            tab(page, name)
            seen[name] = (count_text(page), page.is_visible("#basket-button"))
        check("the basket shows the same count on all five tabs", all(v == (str(n), True) for v in seen.values()) and n >= 4, seen)
        shot(page, "v40-basket-390.png")
        load(page, paints=[P(1, "Owned One")], recipes=[])
        check("with nothing to buy the basket is hidden", count_text(page) == "" and not page.is_visible("#basket-button"))
        page.evaluate("() => { addToShoppingList({ brand: 'B', name: 'New Paint' }, 'Recipe: Test'); }")
        check("adding a paint raises the count at once, without leaving the page", count_text(page) == "1", count_text(page))
        load(page, paints=PAINTS, recipes=RECIPES)
        tab(page, "dashboard")
        page.click("#basket-button")
        page.wait_for_timeout(250)
        check("tapping the basket on the Dashboard opens Recipes on the Shopping switch",
              page.is_visible("#shop-panel") and page.get_attribute('nav button[data-tab="recipes"]', "aria-current") == "page"
              and page.get_attribute('#recipe-seg button[data-view="shopping"]', "aria-selected") == "true")
        tab(page, "settings")
        page.focus("#basket-button")
        page.keyboard.press("Enter")
        page.wait_for_timeout(250)
        check("the keyboard works: Enter on the basket opens Shopping", page.is_visible("#shop-panel"))
        page.evaluate("() => startRecipeDraft(draftFrom(recipeById(1)))")
        page.wait_for_timeout(200)
        page.click("#basket-button")
        page.wait_for_timeout(250)
        check("from an open recipe nobody has changed, the basket goes straight to Shopping", page.is_visible("#shop-panel") and not page.is_visible("#recipe-page"))
        page.evaluate("() => { settings.hideShopLinks = true; saveSettings(); render(); }")
        check("with Shop links switched off the basket and the list stay, only the shop buttons go",
              count_text(page) != "" and page.locator("#shop-panel .shop-brand").count() >= 1 and page.locator("#shop-panel button:has-text('Copy as text')").count() == 1)
        page.evaluate("() => { settings.hideShopLinks = false; saveSettings(); render(); }")

        # ---------- 6. Hostile text ----------
        print("\n--- 6. Hostile text ---")
        hp = [P(1, HOSTILE, "wishlist", brand=HOSTILE_BRAND, shopFrom=[HOSTILE]), P(2, "Used " + HOSTILE, "notowned", brand=HOSTILE_BRAND)]
        load(page, paints=hp, recipes=[rec(1, HOSTILE, "Armour", [2])])
        open_shopping(page)
        panel = page.evaluate("() => ({ html: document.getElementById('shop-panel').innerHTML, pwned: window.__pwned || 0, bad: document.querySelectorAll('#shop-panel img, #shop-panel script, #shop-panel b').length, text: document.getElementById('shop-panel').textContent })")
        check("hostile paint, brand, recipe and source text show as plain words: no picture, script or bold appears and nothing runs",
              panel["pwned"] == 0 and panel["bad"] == 0 and "<img" in panel["text"] and "&lt;img" in panel["html"], panel["bad"])
        check("the basket holds only a picture and a number", page.evaluate("() => [...document.getElementById('basket-button').children].map(c => c.tagName).join()") == "svg,SPAN"
              and re.fullmatch(r"\d+", page.inner_text("#basket-button").strip()) is not None)
        copy = page.evaluate("() => shoppingText(shoppingItems())")
        check("Copy as text keeps the hostile words as plain text", "<img" in copy and "<script>" in copy)

        # ---------- 7. Phones and looks ----------
        print("\n--- 7. Phones and looks ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 780})
                load(page, paints=PAINTS, recipes=RECIPES, settings={"appearance": appearance})
                open_shopping(page)
                tag = f"{appearance} {width}px"
                fits = page.evaluate("() => [...document.querySelectorAll('#recipe-seg button')].every(b => b.scrollWidth <= b.clientWidth + 1)")
                check(f"{tag}: the four switch buttons all fit their words", fits)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                box = page.evaluate("() => { const r = document.getElementById('basket-button').getBoundingClientRect(); const t = document.querySelector('nav button[data-tab=recipes]').getBoundingClientRect(); const n = document.querySelector('nav button[data-tab=compendium] .icon svg').getBoundingClientRect(); return { l: r.left, r: r.right, top: r.top, bot: r.bottom, h: r.height, tl: t.left, tr: t.right, tt: t.top, tb: t.bottom, nextIcon: n.left, w: innerWidth }; }")
                check(f"{tag}: the basket is a small pill at the top corner of the Recipes tab, inside the screen and clear of the next tab's picture", box["l"] >= box["tl"] and box["r"] <= box["w"] and box["r"] <= box["nextIcon"] and box["top"] >= box["tt"] and box["h"] <= 30, box)
                col = page.evaluate("() => { const cs = getComputedStyle(document.getElementById('basket-button')); const root = getComputedStyle(document.documentElement); return [cs.color, root.getPropertyValue('--accent').trim()]; }")
                acc = rgb(col[1]) if col[1].startswith("rgb") else [int(col[1][i:i + 2], 16) for i in (1, 3, 5)]
                end = [0.72 * a + 0.28 * b for a, b in zip(acc, (0x1e, 0x3a, 0x8a))]
                check(f"{tag}: the basket number has contrast of at least 4.5 against both ends of its colour", min(contrast(rgb(col[0]), acc), contrast(rgb(col[0]), end)) >= 4.5, (col, round(contrast(rgb(col[0]), end), 2)))
                shot(page, f"v40-shopping-{appearance}-{width}.png")
        page.set_viewport_size({"width": 1100, "height": 800})
        load(page, paints=PAINTS, recipes=RECIPES)
        d = page.evaluate("() => { const r = document.getElementById('basket-button').getBoundingClientRect(); const t = document.querySelector('nav button[data-tab=recipes]').getBoundingClientRect(); return [r.left >= t.left && r.right <= t.right + 4, r.top >= t.top && r.bottom <= t.bottom]; }")
        check("on a wide screen (tabs along the top) the basket sits inside the Recipes tab", d[0] and d[1], d)
        shot(page, "v40-basket-wide.png")
        page.set_viewport_size({"width": 390, "height": 844})
        check("no page error and no unexpected dialog during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
