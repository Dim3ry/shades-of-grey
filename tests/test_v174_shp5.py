"""SHP5 tests for Minifolio: Shopping screen words and behaviour (AR4 findings 1, 3, 4, 5, 8, 9).

New behaviour only:
1. The models tab is "Wishlist models"; the Paints tab says what fills it; empty and Suggested wording; the models note and the button description.
2. Bought and Remove carry the item name ("Remove, Name") on Paints and Gear rows.
3. A real double click on Remove removes one item (300 to 299) on Paints and Gear, and Undo puts it back.
4. The + Add model draft survives leaving Shopping and a reload, is offered back, and is gone after Save or Cancel.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SETTINGS = {"tab": "dashboard", "examplesChecked": True}
BIG = [{"id": i, "brand": "Citadel", "name": f"Paint {i:03d}", "colour": "#3366aa", "status": "wishlist"} for i in range(1, 301)]
FEW = [{"id": 1, "brand": "Citadel", "name": "Abaddon Black", "colour": "#111111", "status": "wishlist"},
       {"id": 2, "brand": "Citadel", "name": "Mephiston Red", "colour": "#aa1111", "status": "low"}]

def open_shop(page, tab):
    page.click("#basket-button")
    page.wait_for_function("() => settings.tab === 'shopping'")
    page.click(f'#shop-seg [data-stab="{tab}"]')
    page.wait_for_timeout(150)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Words ---")
        load(page, paints=FEW, settings=SETTINGS)
        open_shop(page, "paints")
        tabs = page.locator("#shop-seg button").all_inner_texts()
        check("the models tab is Wishlist models, with its count", tabs[2] == "Wishlist models (0)", tabs)
        check("the Paints tab says what fills it", page.locator("#shop-panel .shop-fills").inner_text() == "Paints marked Wishlist are listed here.")
        check("the Suggested fold-out says it includes Running low and Empty", "Running low and Empty" in page.locator(".shop-suggest-head").inner_text(),
              page.locator(".shop-suggest-head").inner_text())
        open_shop(page, "wishlist")
        check("the models tab says models are not in the button", page.locator("#shop-wish-panel .shop-fills").inner_text() == "Models are not counted in the button.")
        check("the Paints line is not on the other tabs", page.locator("#shop-wish-panel").inner_text().count("listed here") == 0)
        tip = page.evaluate("() => { const b = document.getElementById('basket-button'); const d = document.getElementById(b.getAttribute('aria-describedby')); return [b.title, d && d.textContent]; }")
        check("the Shopping button has a tooltip and a description about models", "not counted" in tip[0] and tip[1] == "Models are not counted in the button.", tip)
        load(page, paints=[], settings=SETTINGS)
        open_shop(page, "paints")
        line = page.locator("#shop-panel .shop-empty").inner_text()
        check("the empty Paints tab says it in one line and has no second line", "Wishlist" in line and "Suggested" in line and page.locator("#shop-panel .shop-fills").count() == 0, line)

        print("\n--- 2. Row names ---")
        load(page, paints=FEW, settings=SETTINGS)
        page.evaluate("() => { book.gear = [{ id: 'wet palette', name: 'wet palette', from: 'Guides' }]; render(); }")
        open_shop(page, "paints")
        rm = page.locator("#shop-panel .shop-remove").first
        tk = page.locator("#shop-panel .shop-tick").first
        check("a paint's Remove and Bought are named with the paint", rm.get_attribute("aria-label") == "Remove, Abaddon Black" and tk.get_attribute("aria-label") == "Bought, Abaddon Black",
              (rm.get_attribute("aria-label"), tk.get_attribute("aria-label")))
        check("the visible word is still Remove", rm.inner_text() == "Remove")
        open_shop(page, "gear")
        check("a gear row's Remove and Bought are named with the item", page.locator("#shop-gear-panel .shop-remove").first.get_attribute("aria-label").startswith("Remove, ")
              and page.locator("#shop-gear-panel .shop-tick").first.get_attribute("aria-label").startswith("Bought, "))

        print("\n--- 3. Double tap on Remove ---")
        load(page, paints=BIG, settings=SETTINGS)
        page.evaluate("() => { book.gear = Array.from({length: 300}, (_, i) => ({ id: 'g' + i, name: 'wet palette ' + i, from: 'Guides' })); render(); }")
        for tab, panel, count in (("paints", "#shop-panel", "shoppingItems().length"), ("gear", "#shop-gear-panel", "gearItems().length")):
            open_shop(page, tab)
            first = page.locator(f"{panel} .shop-remove").first
            name = first.get_attribute("aria-label")
            first.dblclick()
            page.wait_for_timeout(250)
            after = page.evaluate(f"() => {count}")
            check(f"{tab}: a real double click removes one item, 300 to 299", after == 299, after)
            page.click("#toast-undo")
            page.wait_for_timeout(250)
            check(f"{tab}: Undo puts the removed item back", page.evaluate(f"() => {count}") == 300 and page.locator(f"{panel} .shop-remove").first.get_attribute("aria-label") == name)
            page.wait_for_timeout(700)
            page.locator(f"{panel} .shop-remove").first.click()
            page.wait_for_timeout(700)
            page.locator(f"{panel} .shop-remove").first.click()
            page.wait_for_timeout(250)
            check(f"{tab}: two separate taps (over 600 ms apart) remove two", page.evaluate(f"() => {count}") == 298)

        print("\n--- 4. Add model draft ---")
        load(page, paints=[], settings=SETTINGS)
        open_shop(page, "wishlist")
        page.click("#shop-add-btn")
        page.fill(".wish-form .w-name", "Ork Boyz")
        page.fill(".wish-form .w-note", "ten of them")
        page.wait_for_timeout(500)
        page.evaluate("() => showTab('dashboard')")
        page.click("#basket-button")
        page.wait_for_timeout(200)
        check("leaving Shopping and coming back keeps the typed text", page.locator(".wish-form .w-name").input_value() == "Ork Boyz")
        page.reload()
        t.app_ready(page)
        t.leave_launch(page)
        page.click("#basket-button")
        page.wait_for_function("() => settings.tab === 'shopping'")
        card = page.locator("#draft-card-wish")
        check("after a reload Shopping offers the kept model", card.is_visible() and "Ork Boyz" in card.inner_text(), card.inner_text() if card.count() else "")
        card.locator(".draft-keep").click()
        page.wait_for_timeout(250)
        check("Keep going opens the form with the text back",
              page.locator(".wish-form .w-name").input_value() == "Ork Boyz" and page.locator(".wish-form .w-note").input_value() == "ten of them"
              and page.locator("#draft-card-wish").is_hidden())
        page.click(".wish-form .w-cancel")
        page.wait_for_timeout(500)
        check("Cancel clears the draft", page.evaluate("() => localStorage.getItem('shades-of-grey-drafts')") is None)
        page.click("#shop-add-btn")
        page.fill(".wish-form .w-name", "Necron Warriors")
        page.wait_for_timeout(500)
        check("a new draft is kept while typing", "Necron Warriors" in (page.evaluate("() => localStorage.getItem('shades-of-grey-drafts')") or ""))
        page.click('.wish-form button[type="submit"]')
        page.wait_for_timeout(500)
        check("Save clears the draft and the model has no Game", page.evaluate("() => localStorage.getItem('shades-of-grey-drafts')") is None
              and page.evaluate("() => wishes().length") == 1 and page.evaluate("() => wishes()[0].game") == "")
        check("an empty form is not kept", (page.click("#shop-add-btn"), page.wait_for_timeout(500), page.evaluate("() => localStorage.getItem('shades-of-grey-drafts')"))[2] is None)

        print("\n--- 5. Layout (390 and 360, dark and light) ---")
        for w in (390, 360):
            for scheme in ("light", "dark"):
                page.set_viewport_size({"width": w, "height": 844})
                page.emulate_media(color_scheme=scheme)
                load(page, paints=FEW, settings=SETTINGS)
                for tab in ("paints", "wishlist"):
                    open_shop(page, tab)
                    check(f"no sideways scroll at {w} {scheme} on {tab}", no_sideways(page))
                small = page.evaluate("() => [...document.querySelectorAll('#shop-seg button')].filter(b => b.getBoundingClientRect().height < 44).length")
                check(f"tab buttons are 44 px or more tall at {w} {scheme}", small == 0, small)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
