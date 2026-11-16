"""SHP4 tests for Minifolio: My shops, Find buttons on Gear and Wishlist rows, and the Ad line (built, hidden).

New behaviour only:
1. My shops ticks (Shopping screen and Settings) limit every shop bar, Where to buy row, fold-out and Find button, and agree with each other.
2. With every shop unticked, a one-line message and a Tick a shop button show instead of links.
3. Find on a Gear row and on a Wishlist row builds the right search link (product type or model name only, only ticked shops).
4. The Ad line: hidden with no tracking code, shown with a test-only code, hidden again when Shop links are off.
5. Layout: 390, 360 and 320 px, dark and light: no sideways scroll, tap targets 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import open_settings

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(i, name, **more):
    return dict({"id": i, "brand": "The Army Painter", "name": name, "colour": "#3366aa"}, **more)

PAINTS = [P(1, "Matt White", status="wishlist"), P(2, "Alpha Blue", status="wishlist", brand="Citadel")]
WISHES = [{"id": 1, "name": "Space Thing & Co", "count": 2}]
SETTINGS = {"tab": "dashboard", "examplesChecked": True, "modelWishes": WISHES}
ALL = ["Firestorm Games", "Wayland Games", "Element Games"]

def open_shop(page, tab):
    page.click("#basket-button")
    page.wait_for_function("() => settings.tab === 'shopping'")
    page.click(f'#shop-seg [data-stab="{tab}"]')
    page.wait_for_timeout(150)

def setup_gear(page):
    page.evaluate("() => { book.gear = [{ id: 'wet palette', name: 'wet palette', from: 'Guides' }]; render(); }")

def tick(page, shop, on, where="#my-shops-shopping"):
    box = page.locator(f'{where} input[data-my-shop="{shop}"]')
    box.set_checked(on)
    page.wait_for_timeout(100)

def links_text(page, sel):
    return [a.inner_text().replace(" ↗", "").strip() for a in page.locator(sel).all()]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. My shops limits every bar ---")
        load(page, paints=PAINTS, settings=SETTINGS)
        setup_gear(page)
        open_shop(page, "paints")
        bar = lambda: [b.inner_text().strip() for b in page.locator("#buy-bar .buy-shops button").all()]
        check("all four ticked by default, the bar shows all four", page.locator("#my-shops-shopping input:checked").count() == 4 and len(bar()) == 4, bar())
        tick(page, "wayland", False)
        check("unticking Wayland takes it out of the bar", "Wayland Games" not in bar() and len(bar()) == 3, bar())
        open_settings(page)
        check("Settings shows the same choice", page.locator('#my-shops-settings input[data-my-shop="wayland"]').is_checked() is False)
        tick(page, "armypainter", False, "#my-shops-settings")
        check("a change in Settings sticks and is kept in settings, not the book",
              page.evaluate("() => settings.hideShops.slice().sort().join()") == "armypainter,wayland" and page.evaluate("() => JSON.stringify(book).indexOf('hideShops') < 0"))
        page.click("#basket-button"); page.wait_for_function("() => settings.tab === 'shopping'")
        check("the Shopping screen follows", page.locator('#my-shops-shopping input[data-my-shop="armypainter"]').is_checked() is False and bar() == ["Firestorm Games", "Element Games"], bar())

        print("\n--- 2. Find on Gear and on a Wishlist model ---")
        page.click('#shop-seg [data-stab="gear"]')
        row = page.locator("#shop-gear-panel .shop-gear-item")
        row.locator(".shop-find > summary").click()
        hrefs = [a.get_attribute("href") for a in row.locator(".shop-find a").all()]
        check("Find on Gear: ticked shops only, product type only", links_text(page, "#shop-gear-panel .shop-find a") == ["Firestorm Games", "Element Games"]
              and hrefs[0] == "https://www.firestormgames.co.uk/products?q=wet+palette" and hrefs[1] == "https://elementgames.co.uk/search?q=wet+palette", hrefs)
        check("Find link opens in a new tab with noopener", row.locator(".shop-find a").first.get_attribute("rel") == "noopener noreferrer" and row.locator(".shop-find a").first.get_attribute("target") == "_blank")
        page.click('#shop-seg [data-stab="wishlist"]')
        wrow = page.locator("#shop-wish-panel .wish-row")
        wrow.locator(".shop-find > summary").click()
        wh = [a.get_attribute("href") for a in wrow.locator(".shop-find a").all()]
        check("Find on a Wishlist model uses the typed name, encoded", wh[0] == "https://www.firestormgames.co.uk/products?q=Space+Thing+%26+Co", wh)
        check("the Find button has a name that includes the model", "Space Thing" in (wrow.locator(".shop-find > summary").get_attribute("aria-label") or "") or
              page.evaluate("() => document.querySelector('#shop-wish-panel .shop-find > summary').getAttribute('aria-labelledby')"))
        page.click('#shop-seg [data-stab="paints"]')
        check("paint rows have no Find button (they keep their behaviour)", page.locator("#shop-panel .shop-find").count() == 0)

        print("\n--- 3. Where to buy and fold-outs follow My shops ---")
        page.evaluate("() => { showTab('guides'); }")
        wb = page.evaluate("""() => { const b = buildWhereToBuy(Object.keys(WHERE_TO_BUY)[0], WHERE_TO_BUY[Object.keys(WHERE_TO_BUY)[0]].kind, 'x');
            return b ? [...b.querySelectorAll('.where-buy-item')][0].querySelectorAll('.where-buy-links a').length : -1; }""")
        check("a Where to buy row shows only the two ticked shops", wb == 2, wb)

        print("\n--- 4. Nothing ticked ---")
        open_shop(page, "paints")
        for s in ("firestorm", "element"):
            tick(page, s, False)
        txt = page.inner_text("#buy-bar")
        check("the bar says No shops ticked and offers Tick a shop", "No shops ticked." in txt and page.locator("#buy-bar .shop-none button").count() == 1, txt)
        page.click("#buy-bar .shop-none button")
        check("Tick a shop puts focus on the first My shops box", page.evaluate("() => document.activeElement.closest('#my-shops-shopping') !== null"))
        page.click('#shop-seg [data-stab="gear"]')
        page.locator("#shop-gear-panel .shop-find > summary").click()
        check("Find shows the same line with no links", "No shops ticked." in page.inner_text("#shop-gear-panel .shop-find") and page.locator("#shop-gear-panel .shop-find a").count() == 0)
        for s in ("firestorm", "wayland", "element", "armypainter"):
            tick(page, s, True)

        print("\n--- 5. The Ad line ---")
        page.click('#shop-seg [data-stab="paints"]')
        check("no codes today: no Ad line anywhere", page.locator(".shop-ad").count() == 0 and "Ad:" not in page.inner_text("#view-shopping"))
        page.evaluate("() => minifolioShopTest('firestorm', '&ref=TEST')")
        page.wait_for_timeout(100)
        check("a test code on a ticked shop shows the Ad line above the shop buttons", page.locator("#buy-bar .shop-ad").count() == 1 and "Ad: we may earn from these links" in page.inner_text("#buy-bar"))
        page.click('#shop-seg [data-stab="gear"]')
        page.locator("#shop-gear-panel .shop-find > summary").click()
        check("the Find fold-out carries the Ad line and the code on the link",
              page.locator("#shop-gear-panel .shop-find .shop-ad").count() == 1 and page.locator("#shop-gear-panel .shop-find a").first.get_attribute("href").endswith("&ref=TEST"))
        tick(page, "firestorm", False)
        check("unticking the only shop with a code hides the Ad line", page.locator(".shop-ad").count() == 0)
        tick(page, "firestorm", True)
        page.locator("#shop-links-switch").set_checked(False)
        page.wait_for_timeout(100)
        check("Show shop links off hides every Find, link, My shops box and the Ad line",
              page.locator(".shop-find, .shop-ad, #buy-bar").count() == 0 and not page.locator("#my-shops-shopping").is_visible())
        page.locator("#shop-links-switch").set_checked(True)

        print("\n--- 6. Layout ---")
        for w, h in ((390, 844), (360, 640), (320, 640)):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": w, "height": h})
                page.emulate_media(color_scheme=scheme)
                page.click('#shop-seg [data-stab="gear"]')
                page.locator("#shop-gear-panel .shop-find > summary").click()
                small = page.evaluate("""() => [...document.querySelectorAll('#my-shops-shopping label, #shop-gear-panel .shop-find > summary, #shop-gear-panel .shop-find a')]
                    .filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height).filter(x => x < 43.5).length""")
                check(f"{w}px {scheme}: no sideways scroll, tap targets 44 px or more", no_sideways(page) and small == 0, small)
        check("no page errors and no pop-ups", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
