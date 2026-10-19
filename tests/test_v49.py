"""v49 tests for Minifolio (declutter: More info, Swatches, cascading filters).

What changed:
 (a) A shared "More info" button (plain text, opens the detail under it). In the Compendium the page introduction, each part's
     explanation, a scheme's "why" and each paint row's reason and note sit behind it.
 (b) The Compendium's action row: Copy as text and Save into a new recipe are equal-width buttons across the card, the Shopping list
     fold-out is a full-width button, and a small greyed-out "Add to shopping list" button with a hint shows until a scheme is picked.
 (c) Your Palette: a List | Swatches switch. Swatches shows small colour tiles with a status mark (a different shape per status) and a
     key. Tap a tile to open that paint. Name, brand, Merge and Remove sit behind "More options".
 (d) Units filters: To do, Done and Repaint are three equal buttons; the stage buttons open underneath once a group or stage is
     picked, or "Pick by stage" is tapped.

Checks:
1. Versions and the v49 Updates entry.
2. Compendium: More info closed by default, opens and closes, row reasons hidden until opened, targets at least 44 px,
   greyed shopping list button and its hint, equal-width action buttons after picking a scheme.
3. Palette: the switch, tiles, marks and key, tapping a tile, More options, no sideways scroll at 390 and 360 px.
4. Units: three equal group buttons, stages hidden until needed, Pick by stage, a picked group shows the stages.
5. No page errors, no browser pop-ups, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def box(loc):
    return loc.bounding_box()

def no_sideways(page):
    return page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

def main():
    errors, csp, popups = [], [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        page.goto(t.BASE + "manifest.json"); page.evaluate("localStorage.clear()")
        page.goto(URL); page.wait_for_function("() => typeof APP_VERSION === 'string'")

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and wording ---")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v49 or later", float(version[1:]) >= 49, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v49')")
        check("the v49 Updates entry exists", bool(entry))
        check("the v49 entry has no em dashes", entry and not any("—" in c for c in entry["changes"]))

        # ---------- 2. Compendium ----------
        print("\n--- 2. Compendium ---")
        page.click('.tabs button[data-tab="compendium"]')
        top = page.locator("#compendium-body > .more-info").first
        check("a More info button sits at the top of the Compendium", top.count() == 1)
        btn = top.locator(".more-info-button")
        check("it starts closed", btn.get_attribute("aria-expanded") == "false")
        check("the introduction is hidden while closed", not page.locator("#cmp-intro").is_visible()
              if page.locator("#cmp-intro").count() else True)
        check("the button is at least 44 px tall", box(btn)["height"] >= 43.5, box(btn))
        btn.click()
        check("tapping opens it and the words change", btn.get_attribute("aria-expanded") == "true" and "Less info" in btn.inner_text())
        check("the introduction shows", page.locator("#cmp-intro").is_visible())
        btn.click()
        check("tapping again closes it", btn.get_attribute("aria-expanded") == "false")
        page.get_by_role("button", name="Starter schemes").first.click()
        check("with no scheme picked there is a greyed shopping list button",
              page.locator(".shop-idle-button").count() == 1 and page.locator(".shop-idle-button").get_attribute("aria-disabled") == "true")
        check("its hint says what to do", "Select a scheme" in page.locator(".shop-idle .hint").inner_text())
        page.locator('[data-mood="cold"]').first.click()
        page.get_by_role("button", name="Cold blue and gold").click()
        check("picking a scheme removes the greyed button", page.locator(".shop-idle-button").count() == 0)
        rows = page.locator("#compendium-body .idea-static")
        check("the scheme shows its paint rows", rows.count() >= 3, rows.count())
        row_more = rows.first.locator(".more-info-button")
        check("each row's reason is behind a More info button", row_more.count() == 1 and row_more.get_attribute("aria-expanded") == "false")
        check("the row's reason is hidden at first", not rows.first.locator(".idea-why").is_visible())
        row_more.click()
        check("opening it shows the reason", rows.first.locator(".idea-why").is_visible())
        check("row buttons are at least 44 px tall", box(row_more)["height"] >= 43.5, box(row_more))
        copy = page.get_by_role("button", name="Copy Cold blue armour, gold trim, red eyes as text") if False else page.locator(".fold-panel .share-row .plain-button")
        if copy.count() == 2:
            a, b = box(copy.nth(0)), box(copy.nth(1))
            check("Copy as text and Save into a new recipe are equal width", abs(a["width"] - b["width"]) <= 2, (a["width"], b["width"]))
        else:
            check("two action buttons are shown", False, copy.count())
        shop = page.locator(".scheme-shop > summary")
        check("the Shopping list fold-out stretches across the card", shop.count() == 1 and box(shop)["width"] > 300, box(shop) if shop.count() else None)
        check("no sideways scrolling in the Compendium", no_sideways(page))

        # ---------- 3. Palette ----------
        print("\n--- 3. Your Palette ---")
        page.click('.tabs button[data-tab="recipes"]')
        page.get_by_text("Your Palette").first.click()
        sw_btn = page.locator('#palette-layout [data-layout="swatches"]')
        check("a List | Swatches switch is there, List first", page.locator("#palette-layout .chip").count() == 2
              and page.locator('#palette-layout [data-layout="list"]').get_attribute("aria-pressed") == "true")
        n = page.locator(".paint-head").count()
        page.locator(".paint-head").first.click()
        page.locator(".status-chip").filter(has_text="Owned").first.click()
        opt = page.locator(".paint-options .more-info-button").first
        check("in the list, More options is closed", opt.get_attribute("aria-expanded") == "false")
        check("the name box is hidden until More options opens", not page.locator('input[aria-label="Paint name"]').first.is_visible())
        opt.click()
        check("More options shows the name box", page.locator('input[aria-label="Paint name"]').first.is_visible())
        page.locator(".paint-head").first.click()
        sw_btn.click()
        tiles = page.locator(".swatch-tile")
        check("Swatches shows one tile for each paint", tiles.count() == n, (tiles.count(), n))
        check("the key shows five marks", page.locator("#palette-legend .legend-item").count() == 5)
        check("the paint with a status has a mark", page.locator(".swatch-tile .status-marker").count() >= 1)
        check("a tile's name says its status", "Owned" in tiles.first.get_attribute("aria-label"), tiles.first.get_attribute("aria-label"))
        tb = box(tiles.first)
        check("tiles are at least 44 px", tb["width"] >= 43.5 and tb["height"] >= 43.5, tb)
        tiles.first.click()
        check("tapping a tile opens that paint", page.locator(".swatch-detail").count() == 1 and page.locator(".swatch-detail .status-chip").count() == 5)
        check("its tile says it is open", tiles.first.get_attribute("aria-expanded") == "true")
        page.locator(".swatch-detail .paint-head").click()
        check("tapping the paint closes it", page.locator(".swatch-detail").count() == 0)
        check("no sideways scrolling in Swatches at 390 px", no_sideways(page))
        page.set_viewport_size({"width": 360, "height": 800})
        check("no sideways scrolling in Swatches at 360 px", no_sideways(page))
        page.locator('#palette-layout [data-layout="list"]').click()
        check("no sideways scrolling in the list at 360 px", no_sideways(page))
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 4. Units filters ----------
        print("\n--- 4. Units filters ---")
        page.click('.tabs button[data-tab="units"]')
        if page.locator("#filter-card").is_hidden():
            page.click("#toggle-filters")
        groups = page.locator("#group-chips .chip")
        check("three group buttons", groups.count() == 3, groups.count())
        w = [box(groups.nth(i))["width"] for i in range(3)]
        check("they are equal width", max(w) - min(w) <= 2, w)
        check("the stages are hidden at first", page.locator("#stage-chips .chip").count() == 0)
        check("a Pick by stage button is there", page.locator("#stage-chips-toggle").count() == 1)
        page.click("#stage-chips-toggle")
        check("Pick by stage shows every stage", page.locator("#stage-chips .chip").count() >= 5)
        page.click("#stage-chips-toggle")
        check("Hide stages hides them again", page.locator("#stage-chips .chip").count() == 0)
        groups.first.click()
        check("picking To do shows the stages underneath", page.locator("#stage-chips .chip").count() >= 5)
        check("To do's stages are pressed", page.locator('#stage-chips .chip[aria-pressed="true"]').count() >= 1)
        check("no sideways scrolling on Units", no_sideways(page))

        # ---------- 5. Clean run ----------
        print("\n--- 5. A clean run ---")
        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not popups, popups[:2])
        check("no Content Security Policy errors", not csp, csp[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
