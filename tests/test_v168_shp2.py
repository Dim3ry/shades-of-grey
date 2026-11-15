"""SHP2 tests for Minifolio: Shopping becomes a screen of its own.

New behaviour only:
1. The Shopping button in the header: icon, the word Shopping, a count of paints and Gear only (hidden at 0), a screen reader name with the count.
2. Painting has no Shopping tab; the Painting tab row fits at 320 px.
3. The Shopping screen: Paints (N), Gear (N), Wishlist (N); each tab shows its own content; the Wishlist tab is drawn from the Models Wishlist.
4. Got it and Undo on the Wishlist tab; a row tap opens the model in Models; the count in the button does not move for Wishlist models.
5. Copy as text has Paints, Gear and Wishlist headings, and leaves out an empty one.
6. The Show shop links switch on Shopping and in Settings stay in step.
7. Back returns to where Shopping was opened from. The Bought tick has a name.
8. 390, 360 and 320 px, dark and light: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, **more):
    return dict({"id": i, "brand": "Citadel", "name": name, "colour": "#3366aa"}, **more)

WISH = {"status": "wishlist", "shopFrom": ["Recipe: Blue"]}
PAINTS = [P(1, "Alpha Blue", **WISH), P(2, "Beta Red", **WISH), P(3, "Delta Owned", status="owned")]
WISHES = [{"id": 1, "name": "Space Thing", "count": 5, "note": "for the big army"}, {"id": 2, "name": "Another One", "count": 1}]
SETTINGS = {"tab": "dashboard", "examplesChecked": True, "modelWishes": WISHES}

def badge(page):
    loc = page.locator("#basket-button .basket-count")
    return loc.inner_text().strip() if loc.count() else ""

def tabs(page):
    return [b.inner_text().strip() for b in page.locator("#shop-seg > button").all()]

def open_shop(page, tab=None):
    page.click("#basket-button")
    page.wait_for_function("() => settings.tab === 'shopping'")
    if tab:
        page.click(f'#shop-seg [data-stab="{tab}"]')
    page.wait_for_timeout(200)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. The Shopping button ---")
        load(page, paints=PAINTS, settings=SETTINGS)
        btn = page.locator("#basket-button")
        check("button says Shopping on the Nexus screen, with its icon", btn.is_visible() and "Shopping" in btn.inner_text() and btn.locator("svg").count() == 1)
        check("count is 2 (paints) and the Wishlist models are not in it", badge(page) == "2", badge(page))
        check("its screen reader name includes the count", page.get_attribute("#basket-button", "aria-label") == "Shopping, 2 paints",
              page.get_attribute("#basket-button", "aria-label"))
        page.evaluate("() => addGear('wet palette', 'Guides')")
        check("Gear is counted too", badge(page) == "3" and "1 gear item" in page.get_attribute("#basket-button", "aria-label"))
        page.evaluate("() => { for (const p of book.paints) if (p.status === 'wishlist') p.status = 'owned'; delete book.gear; render(); }")
        check("no count at 0, but the button still shows", badge(page) == "" and btn.is_visible()
              and page.get_attribute("#basket-button", "aria-label") == "Shopping, empty")
        page.evaluate("() => { for (const p of book.paints) if (p.id < 3) p.status = 'wishlist'; render(); }")
        for tab in ("units", "recipes", "guides"):
            page.click(f'.tabs button[data-tab="{tab}"]')
            page.wait_for_timeout(150)
            if not btn.is_visible():
                break
        check("it shows on Models, Painting and Tools too", btn.is_visible())

        print("\n--- 2. Painting has no Shopping tab ---")
        page.click('.tabs button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        check("no Shopping tab in the Painting row", page.locator('#recipe-seg [data-view="shopping"]').count() == 0
              and "Shopping" not in page.inner_text("#recipe-seg"))

        print("\n--- 3. The Shopping screen ---")
        page.click("#basket-button")
        page.wait_for_function("() => settings.tab === 'shopping'")
        check("the screen is titled Shopping and the Painting piece of the bar is lit",
              page.inner_text("#shopping-title") == "Shopping" and page.get_attribute('.tabs button[data-tab="recipes"]', "aria-current") == "page")
        check("tabs carry their counts", tabs(page) == ["Paints (2)", "Gear (0)", "Wishlist (2)"], tabs(page))
        check("Paints tab lists the two paints", page.locator("#shop-panel .shop-item").count() == 2 and page.locator("#shop-panel .shop-gear-item").count() == 0)
        page.evaluate("() => addGear('wet palette', 'Guides')")
        check("adding Gear updates the open screen's tab count and the button", tabs(page)[1] == "Gear (1)" and badge(page) == "3")
        page.click('#shop-seg [data-stab="gear"]')
        check("Gear tab shows the Gear row, and the Paints list is hidden", page.locator("#shop-gear-panel .shop-gear-item").count() == 1
              and page.locator("#shop-panel").is_hidden())
        names = page.locator("#shop-wish-panel").evaluate("e => e.innerText")
        page.click('#shop-seg [data-stab="wishlist"]')
        rows = page.locator("#shop-wish-panel .wish-row")
        check("Wishlist tab has a row per Models Wishlist item, with count and note",
              rows.count() == 2 and "5 models" in page.inner_text("#shop-wish-panel") and "for the big army" in page.inner_text("#shop-wish-panel"))
        page.evaluate("() => { settings.modelWishes.push({ id: 9, name: 'Late Add', count: 2, note: '', game: '', faction: '', really: false, added: '' }); render(); }")
        check("it is drawn from wishes(): a model added there shows here at once", page.locator("#shop-wish-panel .wish-row", has_text="Late Add").count() == 1
              and tabs(page)[2] == "Wishlist (3)")
        page.evaluate("() => { settings.modelWishes = settings.modelWishes.filter(w => w.id !== 9); render(); }")

        print("\n--- 4. Got it, Undo, open in Models ---")
        before = badge(page)
        page.locator("#shop-wish-panel .wish-row", has_text="Another One").locator(".wish-got").click()
        page.wait_for_timeout(200)
        check("Got it moves the model into Models and leaves the tab", page.evaluate("() => models.some(m => m.name === 'Another One')")
              and page.locator("#shop-wish-panel .wish-row").count() == 1 and tabs(page)[2] == "Wishlist (1)")
        check("the button's count did not change", badge(page) == before, badge(page))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo puts the Wishlist item back and removes the model", not page.evaluate("() => models.some(m => m.name === 'Another One')")
              and page.locator("#shop-wish-panel .wish-row").count() == 2)
        page.locator("#shop-wish-panel .wish-row", has_text="Space Thing").locator(".wish-info").click()
        page.wait_for_timeout(250)
        check("a row tap opens that model's form in Models",
              page.evaluate("() => settings.tab") == "units" and page.input_value("#wish-form-slot .w-name") == "Space Thing")

        print("\n--- 5. Copy as text ---")
        page.evaluate("() => { copied = null; navigator.clipboard.writeText = (x) => { copied = x; return Promise.resolve(); }; }")
        text = page.evaluate("() => shoppingText(shoppingItems())")
        check("Paints, Gear and Wishlist each have a heading, in that order",
              all(h in text for h in ("\nPaints\n", "\nGear\n", "\nWishlist\n")) and text.index("Paints") < text.index("Gear") < text.index("Wishlist"), text)
        check("a Wishlist line has name, models and note", "- Space Thing (5 models): for the big army" in text, text)
        empty = page.evaluate("() => shoppingText([], [], [])")
        no_gear = page.evaluate("() => shoppingText(shoppingItems(), [], wishes())")
        check("an empty section is left out", "Nothing to buy." in empty and "Gear" not in no_gear and "Paints" in no_gear and "Wishlist" in no_gear)

        print("\n--- 6. Show shop links switch ---")
        open_shop(page, "paints")
        sw = page.locator("#shop-links-switch")
        check("the switch is at the top of Shopping, on by default, with a name", sw.is_checked() and page.locator("label.shop-links-row").inner_text().strip() == "Show shop links")
        sw.uncheck()
        page.wait_for_timeout(150)
        check("off hides the Buy these bar and is saved", page.locator("#shop-panel .buy-bar").count() == 0 and page.evaluate("() => settings.hideShopLinks") is True)
        page.evaluate("() => { document.querySelector('#view-shopping').scrollIntoView(); }")
        page.click('.tabs button[data-tab="guides"]')
        page.click('#more-seg [data-page="settings"]')
        page.wait_for_timeout(200)
        check("Settings shows the same switch, unticked", not page.locator("#show-shop-links").is_checked())
        page.evaluate("() => { const b = document.getElementById('show-shop-links'); b.checked = true; b.dispatchEvent(new Event('change', { bubbles: true })); }")   # (it sits in a folded card)
        open_shop(page)
        check("ticking it in Settings ticks it here, and the Buy these bar is back", sw.is_checked() and page.locator("#shop-panel .buy-bar").count() == 1)

        print("\n--- 7. Back, and the Bought tick's name ---")
        label = page.locator("#shop-panel .shop-tick").first.get_attribute("aria-labelledby")
        name = page.evaluate("""() => { const t = document.querySelector('#shop-panel .shop-tick');
            return t.getAttribute('aria-labelledby').split(' ').map(id => document.getElementById(id)).map(e => e === t ? t.getAttribute('aria-label') : e.textContent).join(' ').trim(); }""")
        check("the Bought tick is named Bought plus the paint", name.startswith("Bought ") and ("Alpha Blue" in name or "Beta Red" in name), name)
        page.click('.tabs button[data-tab="units"]')
        page.wait_for_timeout(200)
        page.click("#basket-button")
        page.wait_for_function("() => settings.tab === 'shopping'")
        page.click("#back-menu")
        page.wait_for_function("() => settings.tab === 'units'")
        check("the back arrow returns to Models, where Shopping was opened", page.evaluate("() => settings.tab") == "units")
        page.click("#basket-button")
        page.wait_for_function("() => settings.tab === 'shopping'")
        page.go_back()
        page.wait_for_timeout(300)
        page.evaluate("() => 0")
        check("the phone's Back does the same", page.evaluate("() => settings.tab") == "units", page.evaluate("() => settings.tab"))

        check("no page errors or pop-ups", not errors, errors)
        ctx.close()

        print("\n--- 8. Sizes and looks ---")
        for width, height in ((390, 844), (360, 640), (320, 640)):
            for scheme in ("dark", "light"):
                c = browser.new_context(viewport={"width": width, "height": height}, service_workers="block", reduced_motion="reduce", color_scheme=scheme)
                pg = c.new_page()
                pg.on("pageerror", lambda x: errors.append(str(x)))
                load(pg, paints=PAINTS, settings=dict(SETTINGS, theme=scheme) if False else SETTINGS)
                pg.evaluate("() => addGear('wet palette', 'Guides')")
                small = []
                for tab in (None, "gear", "wishlist"):
                    open_shop(pg, tab)
                    # a tap area is the control, its label row (the switch), or the enlarged ::after box (the Shopping button, CLAUDE.md)
                    small += pg.evaluate("""() => [...document.querySelectorAll('#view-shopping button, #view-shopping label, #basket-button')].filter(b => b.offsetParent)
                        .map(b => { const r = b.getBoundingClientRect(); const a = b.id === 'basket-button' ? getComputedStyle(b, '::after') : null;
                          return [b.id || b.className || b.textContent.trim(), Math.round(a ? r.height + parseFloat(a.top) * -2 : r.height)]; }).filter(x => x[1] < 44)""")
                check(f"{width} px {scheme}: no sideways scroll, no control under 44 px", no_sideways(pg) and not small,
                      (no_sideways(pg), small))
                if width == 320:
                    check(f"320 px {scheme}: the header button and the title fit on one line",
                          pg.evaluate("() => document.querySelector('.app-bar').getBoundingClientRect().height") < 70)
                c.close()
        browser.close()

    check("no page errors in the size runs", not errors, errors)
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
