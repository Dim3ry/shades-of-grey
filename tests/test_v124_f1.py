"""F1 tests for Minifolio: shopping suggestions and the Colour Lab Add button.

New behaviour only:
1. Suggested: a closed fold-out under the shopping list with Empty paints and Not owned paints one of your recipes uses; never an Owned
   paint, a Not owned paint no recipe uses, an example paint or a made-up one. Each row: the name, the word, Add and Dismiss.
   No fold-out when nothing qualifies. The basket counts the list only.
2. Add moves a paint to the list (source "Suggested") and out of Suggested, with Undo. Dismiss keeps it out, also after reopening the
   app; Remove on the list counts as dismissing; going on the list again clears it.
3. Colour Lab's Colour ideas: a visible Add to shopping list on a row you do not own, also with Settings -> Shop links off; the tag
   changes to On your shopping list, and Undo works.
4. Backup and restore keep the dismissal; an old backup without it still loads.
5. 390x844, 360x640 and 320 px, dark and light: no sideways scroll, 44 px taps, a long name stays on its row.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, **more):
    return dict({"id": i, "brand": "Citadel", "name": name, "colour": "#3366aa"}, **more)

LONG = "Zeta Empty With A Rather Long Paint Name That Goes On"
PAINTS = [P(1, "Alpha Empty", status="empty"), P(2, "Beta Needed", status="notowned"), P(3, "Gamma Owned", status="owned"),
          P(4, "Delta Unused", status="notowned"), P(5, "Eta Listed", status="wishlist", shopFrom=["Recipe: Blue"]),
          P(6, "Example Blue", brand="", example=True, status="empty")]   # brand-less example name: a made-up paint (no shop sells it)
SETTINGS = {"tab": "recipes", "recipeView": "shopping", "examplesChecked": True, "recipeExamplesChecked": True}

def open_shop(page):
    page.evaluate("() => { settings.recipeView = 'shopping'; renderRecipes(); }")
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_selector("#shop-panel .card")

def suggested(page):
    return page.evaluate("""() => [...document.querySelectorAll('#shop-panel .shop-suggest-item')].map(li => ({
        name: li.querySelector('.shop-text span').textContent.trim(), word: li.querySelector('.shop-suggest-word').textContent }))""")

def names(page):
    return [r["name"] for r in suggested(page)]

def basket(page):
    return page.inner_text("#basket-button").strip()

def paint(page, pid):
    return page.evaluate("(id) => { const p = book.paints.find(x => x.id === id); return { s: paintStatus(p), d: p.shopDismissed === true, from: p.shopFrom || [] }; }", pid)

def row(page, name):
    return page.locator("#shop-panel .shop-suggest-item", has_text=name)

def small_taps(page):
    return page.evaluate("""() => [...document.querySelectorAll('#shop-panel button')].filter(b => b.offsetParent)
        .map(b => b.getBoundingClientRect()).filter(r => r.height < 44 || r.width < 44).length""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. Suggested ---")
        load(page, paints=PAINTS, recipes=[t.rec(1, "Blue", "Armour", [2, 3, 5, 6])], settings=SETTINGS)
        mname = page.evaluate("() => EXAMPLE_RECIPES[0].steps[0].paints[0][1]")
        page.evaluate("(n) => { const p = book.paints.find(x => x.id === 6); p.name = n; save(); }", mname)
        open_shop(page)
        head = page.locator("#shop-panel .shop-suggest-head")
        check("Suggested sits under the list, closed, and named Suggested", head.count() == 1 and head.inner_text().strip() == "Suggested"
              and head.get_attribute("aria-expanded") == "false" and not page.locator("#shop-panel .shop-suggest-item").first.is_visible())
        head.click()
        rows = suggested(page)
        check("it lists the Empty paint and the Not owned recipe paint, each with its word, and nothing else",
              rows == [{"name": "Alpha Empty", "word": "Empty"}, {"name": "Beta Needed", "word": "Not owned"}], rows)
        check("each row has one Add and a Dismiss named Dismiss",
              all(row(page, n).locator(".shop-suggest-add").count() == 1 for n in names(page))
              and (row(page, "Alpha Empty").locator(".shop-suggest-dismiss").get_attribute("aria-label") == "Dismiss"))
        check("no explanatory sentence in it", page.locator("#shop-panel .shop-suggested p").count() == 0)
        check("the basket counts the list only", basket(page) == "1", basket(page))

        print("\n--- 2. Add, Undo, Dismiss, Remove ---")
        row(page, "Beta Needed").locator(".shop-suggest-add").click()
        page.wait_for_timeout(150)
        b = paint(page, 2)
        check("Add puts it on the list with the source Suggested and says so", b["s"] == "wishlist" and b["from"] == ["Suggested"]
              and page.inner_text("#toast").startswith("Added Beta Needed"), (b, page.inner_text("#toast")))
        check("it leaves Suggested, the fold-out stays open, and the basket follows", names(page) == ["Alpha Empty"] and basket(page) == "2"
              and head.get_attribute("aria-expanded") == "true", (names(page), basket(page)))
        check("the focus moves to the next row's Add", page.evaluate("() => document.activeElement.classList.contains('shop-suggest-add')"))
        page.click("#toast-undo")
        page.wait_for_timeout(150)
        check("Undo takes it off the list and back into Suggested", paint(page, 2)["s"] == "notowned" and "Beta Needed" in names(page) and basket(page) == "1")

        row(page, "Alpha Empty").locator(".shop-suggest-dismiss").click()
        page.wait_for_timeout(150)
        check("Dismiss takes it out of Suggested and leaves the paint Empty and off the list",
              names(page) == ["Beta Needed"] and paint(page, 1) == {"s": "empty", "d": True, "from": []} and basket(page) == "1", (names(page), paint(page, 1)))
        page.click("#toast-undo")
        page.wait_for_timeout(150)
        check("Undo brings it back", "Alpha Empty" in names(page) and not paint(page, 1)["d"])
        row(page, "Alpha Empty").locator(".shop-suggest-dismiss").click()
        page.wait_for_timeout(150)

        page.locator("#shop-panel .shop-item", has_text="Eta Listed").locator(".shop-remove").click()
        page.wait_for_timeout(150)
        check("Remove on the list counts as dismissing: the paint is Not owned and does not jump into Suggested",
              paint(page, 5)["s"] == "notowned" and paint(page, 5)["d"] and "Eta Listed" not in names(page), (paint(page, 5), names(page)))
        page.reload()
        page.wait_for_function("() => typeof renderShopPanel === 'function'")
        leave_launch(page)
        open_shop(page)
        page.click("#shop-panel .shop-suggest-head")
        check("after reopening the app, dismissed paints stay out", names(page) == ["Beta Needed"], names(page))
        page.evaluate("() => addToShoppingList(book.paints.find(x => x.id === 5), 'Colour Lab: Colour ideas')")
        check("adding it to the list yourself clears the dismissal", paint(page, 5)["s"] == "wishlist" and not paint(page, 5)["d"])
        row(page, "Beta Needed").locator(".shop-suggest-dismiss").click()
        page.wait_for_timeout(150)
        check("with nothing left to suggest there is no fold-out at all", page.locator("#shop-panel .shop-suggested").count() == 0)

        print("\n--- 3. Backup and restore ---")
        saved = page.evaluate("JSON.parse(JSON.stringify(backupData()))")
        kept = {x["id"]: x.get("shopDismissed") for x in saved["recipes"]["paints"]}
        check("the backup carries the dismissal", kept.get(1) is True and kept.get(2) is True and 5 not in [k for k, v in kept.items() if v], kept)
        again = page.evaluate("(b) => cleanRecipeBook(b).paints.filter(p => p.shopDismissed === true).map(p => p.id).sort()", saved["recipes"])
        check("it survives a restore", again == [1, 2], again)
        old = dict(saved["recipes"], paints=[{k: v for k, v in x.items() if k != "shopDismissed"} for x in saved["recipes"]["paints"]])
        old["paints"][0]["shopDismissed"] = "yes"
        back = page.evaluate("(b) => { const c = cleanRecipeBook(b); return { n: c.paints.length, any: c.paints.some(p => 'shopDismissed' in p) }; }", old)
        check("an old backup without it loads, and only a real true counts", back == {"n": len(saved["recipes"]["paints"]), "any": False}, back)

        print("\n--- 4. Colour Lab Add button ---")
        lab = {"tab": "recipes", "recipeView": "colourlab", "examplesChecked": True, "recipeExamplesChecked": True, "hideShopLinks": True}
        load(page, paints=[P(1, "Mid Blue", status="owned")], settings=lab)
        page.click('nav button[data-tab="recipes"]')
        page.evaluate("""() => { compendiumState.lab = 'ideas'; const c = compendiumBaseChoices();
            const all = [...c.own, ...c.other, ...c.brands.flatMap(b => b.list)]; compendiumState.base = c.key(all.find(x => x.name === 'Lustful Purple')); renderColourLab(); }""")
        rows = page.locator(f"#cmp-lab-ideas .idea-list > li")
        unowned = [i for i in range(rows.count()) if rows.nth(i).locator(".idea-tag").first.inner_text() != "You own this"]
        r0 = rows.nth(unowned[0]) if unowned else rows.nth(0)
        btn = r0.locator(".shop-add-row button")
        check("with Shop links off, a colour idea you do not own shows Add to shopping list on its row (and no shop links)",
              unowned and btn.count() == 1 and btn.is_visible() and btn.inner_text() == "Add to shopping list"
              and page.locator("#cmp-lab-ideas .shop-more").count() == 0, (unowned, btn.count()))
        name = r0.locator(".idea-name").first.evaluate("e => e.childNodes[0].textContent")
        btn.click()
        page.wait_for_timeout(150)
        mine = page.evaluate("(n) => { const p = book.paints.find(x => x.name === n); return p ? { s: paintStatus(p), from: p.shopFrom } : null; }", name)
        check("Add puts it on the list from Colour Lab: Colour ideas, and the tag says On your shopping list",
              mine == {"s": "wishlist", "from": ["Colour Lab: Colour ideas"]} and r0.locator(".idea-tag").first.inner_text() == "On your shopping list"
              and r0.locator(".shop-add-row .shop-onlist").count() == 1 and basket(page) == "1", (mine, r0.locator(".idea-tag").first.inner_text()))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        rows = page.locator("#cmp-lab-ideas .idea-list > li")
        r0 = rows.nth(unowned[0])
        check("Undo takes it off, the tag goes back and the button returns", r0.locator(".idea-tag").first.inner_text() == "Not in your palette"
              and r0.locator(".shop-add-row button").count() == 1 and page.locator("#basket-button.hidden").count() == 1, r0.locator(".idea-tag").first.inner_text())
        page.evaluate("() => { settings.hideShopLinks = false; renderColourLab(); }")
        r0 = page.locator("#cmp-lab-ideas .idea-list > li").nth(unowned[0])
        check("with Shop links on, the Shop links fold-out is still there and keeps its own Add", r0.locator(".shop-more").count() == 1
              and r0.locator(".shop-more .shop-add button").count() == 1)

        print("\n--- 5. Phone sizes, dark and light ---")
        for (w, h), scheme in (((390, 844), "dark"), ((360, 640), "light"), ((320, 640), "dark"), ((320, 640), "light")):
            page.close()
            c2 = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = c2.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            load(page, paints=PAINTS[:5] + [P(7, LONG, status="empty")], recipes=[t.rec(1, "Blue", "Armour", [2])], settings=dict(SETTINGS, appearance=scheme))
            open_shop(page)
            page.click("#shop-panel .shop-suggest-head")
            fit = page.evaluate("""() => [...document.querySelectorAll('#shop-panel .shop-suggest-item')].every(li => {
                const r = li.getBoundingClientRect(), t = li.querySelector('.shop-text').getBoundingClientRect(),
                      a = li.querySelector('.shop-suggest-add').getBoundingClientRect(), d = li.querySelector('.shop-suggest-dismiss').getBoundingClientRect();
                return t.left >= r.left - 1 && t.right <= a.left + 1 && a.right <= d.left + 1 && d.right <= r.right + 1 && t.width > 60; })""")
            check(f"{w}x{h} {scheme}: no sideways scroll, every button 44 px, names wrap and keep their place", no_sideways(page) and not small_taps(page) and fit,
                  (no_sideways(page), small_taps(page), fit))
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
