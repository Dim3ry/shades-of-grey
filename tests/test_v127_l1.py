"""L1 and L2 tests for Minifolio: Where to buy, and Gear on the shopping list. New behaviour only.

1. The data (where-to-buy.js): every key is a Guides entry of the kind it names (a key with no entry fails here), 25 entries (L1's 5
   and L2's 20), 1 to 3 product types each, no type twice in one entry, and no brand, range or creator name in any type.
2. A Guides entry with products shows one closed "Where to buy" fold-out under its text; one without products shows none. Open, each
   product type has a plain search link per shop that sells every brand (the product type only, nothing added) and an Add button.
   A Basing tip with products shows it too.
3. Add makes one Gear item that remembers the entry's title; a second Add does not make another; Undo takes it off.
   Settings -> Shop links hides the links and their note but not Add.
4. The shopping list: a Gear section under the paints, with the name, where it came from, a Bought tick and Remove. Bought, Remove and
   Undo work; ticked Gear goes to Bought. Gear counts in the basket and shows in Copy as text; the Buy these shop buttons stay paint-only.
5. Backup and restore keep Gear; an old backup without it still loads.
6. Mentor: an answer whose best source has products shows the same fold-out under it, closed, inside the answer, not over a button or
   chip, and the window does not grow at 360x640.
7. 390x844 dark, 360x640 light and 320x640 dark: no sideways scroll, 44 px taps, rows wrap and never push a name off.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True}
PAINTS = [{"id": 1, "brand": "Citadel", "name": "Alpha Listed", "colour": "#3366aa", "status": "wishlist"}]
# Brand, range and creator names the product types must never use (checks.md for L1 and L2), on top of the app's own paint brands.
OTHER_BRANDS = ["Tamiya", "Vallejo", "Citadel", "Army Painter", "Green Stuff", "Milliput", "Woodland Scenics", "Peco", "Iwata", "Sparmax",
                "Redgrass", "Artis Opus", "AK", "Ammo", "Monument", "Colour Forge", "GodHand", "Expo", "Daylight", "Micro Sol", "Hydro",
                "Warhammer", "Games Workshop", "Two Thin Coats", "Scale 75", "Pro Acryl", "Kimera", "Liquitex", "Winsor"]

def open_entry(page, key, kind="guide"):
    page.evaluate("([k, kind]) => openGuide(k, kind)", [key, kind])
    page.wait_for_timeout(150)

def open_shop(page):
    page.evaluate("() => { settings.recipeView = 'shopping'; renderRecipes(); }")
    page.click('nav button[data-tab="recipes"]')
    page.wait_for_selector("#shop-panel .card")

def gear(page):
    return page.evaluate("() => JSON.parse(JSON.stringify(book.gear || []))")

def basket(page):
    return page.inner_text("#basket-button").strip() if page.locator("#basket-button:not(.hidden)").count() else "hidden"

def small_taps(page, scope):
    return page.evaluate("""(s) => [...document.querySelectorAll(s + ' button, ' + s + ' a, ' + s + ' summary')].filter(b => b.offsetParent)
        .map(b => b.getBoundingClientRect()).filter(r => r.height < 43.5).length""", scope)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. The data ---")
        load(page, paints=PAINTS, settings=SETTINGS)
        data = page.evaluate("""() => Object.entries(WHERE_TO_BUY).map(([key, v]) => { const e = knowledgeIndex().get(key, v.kind);
            return { key, kind: v.kind, types: v.types, found: !!e, title: e ? e.title : '' }; })""")
        missing = [d["key"] for d in data if not d["found"] or d["kind"] not in ("guide", "basing")]
        check("every key in the data file is a Guides entry of the kind it names", not missing, missing)
        check("25 entries: L1's 5 and L2's 20", len(data) == 25, len(data))
        bad_count = [d["key"] for d in data if not 1 <= len(d["types"]) <= 3 or len({x.lower() for x in d["types"]}) != len(d["types"])]
        check("each entry has 1 to 3 product types, none twice", not bad_count, bad_count)
        brands = page.evaluate("PAINT_BRANDS") + OTHER_BRANDS
        words = re.compile(r"\b(" + "|".join(re.escape(b) for b in brands if b.strip()) + r")\b", re.I)
        branded = [(d["key"], x) for d in data for x in d["types"] if words.search(x)]
        check("no product type names a brand, range or creator", not branded, branded)

        print("\n--- 2. The Where to buy fold-out ---")
        open_entry(page, "wet-palette")
        box = page.locator(".guides-entry .where-buy")
        check("an entry with products shows one closed Where to buy fold-out under its text",
              box.count() == 1 and box.get_attribute("open") is None and box.locator("summary").inner_text().strip() == "Where to buy"
              and page.evaluate("() => { const b = document.querySelector('.guides-entry .where-buy'); const ps = [...b.parentElement.querySelectorAll(':scope > p')]; return ps.length > 0 && ps.every(p => p.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING); }"))
        without = page.evaluate("() => knowledgeIndex().list({ kind: 'guide' }).find(e => !(e.key in WHERE_TO_BUY)).key")
        open_entry(page, without)
        check("an entry without products shows none", page.locator(".guides-entry").count() == 1 and page.locator(".where-buy").count() == 0, without)
        open_entry(page, "wet-palette")
        page.click(".guides-entry .where-buy > summary")
        rows = page.evaluate("""() => [...document.querySelectorAll('.guides-entry .where-buy-item')].map(li => ({ name: li.querySelector('.where-buy-name').textContent,
            links: [...li.querySelectorAll('a')].map(a => ({ href: a.href, text: a.textContent, target: a.target, rel: a.rel })), add: li.querySelectorAll('.where-buy-add button').length }))""")
        shops = page.evaluate("() => SHOPS.filter(s => s.brands === 'all').map(s => ({ name: s.name, search: s.search, extra: s.extra }))")
        check("each product type is a row with its name and one Add button", [r["name"] for r in rows] == ["Wet palette", "Wet palette paper"]
              and all(r["add"] == 1 for r in rows), rows)
        want = [[s["search"].replace("{q}", q) for s in shops] for q in ("wet+palette", "wet+palette+paper")]
        check("one plain search link per shop that sells every brand, searching for the product type only (no brand, nothing added)",
              [[l["href"] for l in r["links"]] for r in rows] == want and all(s["extra"] == "" for s in shops)
              and all(l["target"] == "_blank" and "noopener" in l["rel"] for r in rows for l in r["links"]), (rows, want))
        check("no link anywhere in Where to buy names a brand", not [l["href"] for r in rows for l in r["links"] if words.search(l["href"].split("?", 1)[1].replace("+", " "))])
        check("the plain-links words of the Shop links fold-out, for a product type",
              page.inner_text(".guides-entry .where-buy .hint") == "Plain links: Minifolio isn't paid for them, and only the product type goes to the shop.")
        label = page.evaluate("""() => { const a = document.querySelector('.guides-entry .where-buy a');
            return a.getAttribute('aria-labelledby').split(' ').map(id => id === a.id ? a.getAttribute('aria-label') : document.getElementById(id).textContent).join(' '); }""")
        check("a link's name says which shop and which product", label == "Search Firestorm Games for Wet palette", label)

        print("\n--- 3. Add, a second Add, Undo, Shop links off ---")
        page.locator(".guides-entry .where-buy-item").first.locator("button").click()
        page.wait_for_timeout(150)
        g = gear(page)
        check("Add makes one Gear item that remembers the entry's title", g == [{"id": "wet palette", "name": "wet palette", "from": "Using a wet palette"}]
              and page.inner_text("#toast").startswith("Added Wet palette to your shopping list"), (g, page.inner_text("#toast")))
        check("the row now says On your shopping list (and the focus goes there), and the basket counts it",
              page.locator(".guides-entry .where-buy-item").first.inner_text().strip().endswith("On your shopping list")
              and page.evaluate("() => document.activeElement.classList.contains('shop-onlist')") and basket(page) == "2", basket(page))
        again = page.evaluate("() => addGear('Wet palette', 'Somewhere else')")
        check("a second Add does not make another, and says it is already on the list", again is False and len(gear(page)) == 1
              and "already on your shopping list" in page.inner_text("#toast"), (again, gear(page), page.inner_text("#toast")))
        page.locator(".guides-entry .where-buy-item").nth(1).locator("button").click()
        page.wait_for_timeout(150)
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo takes it off again, and the fold-out stays open", [x["id"] for x in gear(page)] == ["wet palette"]
              and page.locator(".guides-entry .where-buy[open] .where-buy-item").nth(1).locator("button").count() == 1, gear(page))
        open_entry(page, "static-grass", "basing")
        check("a Basing tip with products shows the fold-out too", page.locator(".where-buy[data-where-buy='static-grass']").count() == 1)
        page.evaluate("() => { settings.hideShopLinks = true; saveSettings(); }")
        open_entry(page, "varnishing")
        page.click(".guides-entry .where-buy > summary")
        check("with Shop links off the links and their note go, the Add buttons stay",
              page.locator(".guides-entry .where-buy a").count() == 0 and page.locator(".guides-entry .where-buy .hint").count() == 0
              and page.locator(".guides-entry .where-buy-add button").count() == 3)
        page.locator(".guides-entry .where-buy-item").nth(1).locator("button").click()   # gloss varnish
        page.wait_for_timeout(150)
        page.evaluate("() => { settings.hideShopLinks = false; saveSettings(); }")

        print("\n--- 4. The shopping list ---")
        open_shop(page)
        order = page.evaluate("() => [...document.querySelectorAll('#shop-panel .shop-lists > .shop-brand')].map(h => h.textContent)")
        check("a Gear section with its own heading, under the paints", order == ["Citadel", "Gear"], order)
        grows = page.evaluate("""() => [...document.querySelectorAll('#shop-panel .shop-gear-list .shop-item')].map(li => ({ text: li.querySelector('.shop-text').innerText.replace(/\\s+/g, ' ').trim(),
            tick: li.querySelectorAll('.shop-tick').length, remove: li.querySelectorAll('.shop-remove').length }))""")
        check("each Gear row has the name, where it came from, a Bought tick and Remove",
              grows == [{"text": "Wet palette from Using a wet palette", "tick": 1, "remove": 1}, {"text": "Gloss varnish from Varnishing models", "tick": 1, "remove": 1}], grows)
        text = page.evaluate("() => shoppingText(shoppingItems())")
        check("Copy as text has Gear under its own heading", "\n\nGear\n- Wet palette (from Using a wet palette)\n- Gloss varnish (from Varnishing models)" in text, text)
        check("the basket counts the paint and the Gear", basket(page) == "3", basket(page))
        page.click("#buy-bar button[data-shop='firestorm']")
        buy = page.evaluate("() => [...document.querySelectorAll('#buy-links a')].map(a => a.href)")
        check("the Buy these shop buttons stay paint-only", len(buy) == 1 and "Alpha" in buy[0], buy)
        page.locator("#shop-panel .shop-gear-item", has_text="Wet palette").locator(".shop-tick").click()
        page.wait_for_timeout(900)
        check("the Bought tick moves it to Bought, out of the basket count", [x.get("bought") for x in gear(page)] == [True, None] and basket(page) == "2"
              and page.inner_text("#shop-panel .shop-bought-head").strip() == "Bought · 1" and page.inner_text("#toast").startswith("Bought Wet palette"), (gear(page), basket(page)))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo puts it back on the list", [x.get("bought") for x in gear(page)] == [None, None] and basket(page) == "3")
        page.locator("#shop-panel .shop-gear-item", has_text="Wet palette").locator(".shop-tick").click()
        page.wait_for_timeout(900)
        page.click("#shop-panel .shop-bought-head")
        page.locator("#shop-panel .shop-bought-list .shop-gear-item").locator(".shop-addback").click()
        page.wait_for_timeout(200)
        check("Add back in Bought puts it on the list again", [x.get("bought") for x in gear(page)] == [None, None] and basket(page) == "3")
        page.locator("#shop-panel .shop-gear-item", has_text="Gloss varnish").locator(".shop-remove").click()
        page.wait_for_timeout(200)
        check("Remove deletes the Gear item", [x["id"] for x in gear(page)] == ["wet palette"] and basket(page) == "2"
              and page.inner_text("#toast").startswith("Removed Gloss varnish"), gear(page))
        page.click("#toast-undo")
        page.wait_for_timeout(200)
        check("Undo brings it back in its place", [x["id"] for x in gear(page)] == ["wet palette", "gloss varnish"] and basket(page) == "3", gear(page))
        page.evaluate("() => { const p = book.paints[0]; removeFromShoppingList(p.id); }")
        page.wait_for_timeout(200)
        check("with only Gear on the list, the list shows it and there is no Buy these bar",
              page.locator("#shop-panel .shop-gear-item").count() == 2 and page.locator("#buy-bar").count() == 0
              and "Nothing to buy" not in page.inner_text("#shop-panel") and basket(page) == "2", page.inner_text("#shop-panel")[:200])

        print("\n--- 5. Backup and restore ---")
        saved = page.evaluate("() => JSON.parse(JSON.stringify(backupData()))")
        check("the backup carries Gear", [x["id"] for x in saved["recipes"].get("gear", [])] == ["wet palette", "gloss varnish"], saved["recipes"].get("gear"))
        back = page.evaluate("(b) => cleanRecipeBook(b).gear", saved["recipes"])
        check("it survives a restore", back == saved["recipes"]["gear"], back)
        old = {k: v for k, v in saved["recipes"].items() if k != "gear"}
        junk = dict(old, gear=[{"name": "  "}, "text", {"name": "Wet palette", "bought": "yes"}, {"name": "wet palette"}, None])
        res = page.evaluate("([a, b]) => [cleanRecipeBook(a), cleanRecipeBook(b).gear]", [old, junk])
        check("an old backup without Gear loads (and has none), and odd Gear entries are tidied",
              "gear" not in res[0] and len(res[0]["paints"]) == 1 and res[1] == [{"id": "wet palette", "name": "Wet palette"}], res)

        print("\n--- 6. Mentor ---")
        page.set_viewport_size({"width": 360, "height": 640})
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("() => { delete book.gear; save(); updateBasket(); }")
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        page.fill(".mentor-input", "how do I use a wet palette")
        page.keyboard.press("Enter")
        page.wait_for_selector(".mentor-reply")
        reply = page.locator(".mentor-reply").last
        page.evaluate("() => document.activeElement.blur()")   # the window is shorter while the typing box has the focus (the bottom bar's room is used then)
        page.wait_for_timeout(150)
        h0 = page.evaluate("() => document.querySelector('.mentor-window').getBoundingClientRect().height")
        check("an answer whose best source has products shows the closed fold-out inside the answer, under its sources",
              reply.locator(".where-buy").count() == 1 and reply.locator(".where-buy").get_attribute("open") is None
              and page.evaluate("() => { const r = [...document.querySelectorAll('.mentor-reply')].pop(); const s = r.querySelector('.mentor-sources'), b = r.querySelector('.where-buy'); return !!s && !!(s.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING); }"))
        reply.locator(".where-buy > summary").click()
        page.wait_for_timeout(150)
        # In the answer's own flow (inside the conversation's scroll box, which clips it), no other button or chip of the answer overlaps it,
        # and once scrolled into view each of its own buttons and links is the thing under its centre (nothing sits over it).
        lay = page.evaluate("""() => { const w = document.querySelector('.mentor-window').getBoundingClientRect(); const reply = [...document.querySelectorAll('.mentor-reply')].pop();
            const b = reply.querySelector('.where-buy'), box = b.getBoundingClientRect();
            const others = [...reply.querySelectorAll('button, a, .mentor-chip')].filter(x => !b.contains(x) && x.getClientRects().length);
            const over = others.filter(x => { const r = x.getBoundingClientRect(); return r.left < box.right && r.right > box.left && r.top < box.bottom && r.bottom > box.top; }).length;
            let covered = 0;
            for (const x of b.querySelectorAll('summary, a, button')) { x.scrollIntoView({ block: 'nearest' }); const r = x.getBoundingClientRect();
                const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); if (!at || !(x === at || x.contains(at))) covered++; }
            const flow = getComputedStyle(b).position === 'static' && !!b.closest('.mentor-scroll');
            return { h: document.querySelector('.mentor-window').getBoundingClientRect().height, maxH: innerHeight, over, covered, flow,
                     sideways: document.documentElement.scrollWidth > innerWidth, inWin: box.left >= w.left - 0.5 && box.right <= w.right + 0.5 }; }""")
        check("open, it never sits over a button or chip, stays inside the window, and the window does not grow at 360x640",
              lay["over"] == 0 and lay["covered"] == 0 and lay["flow"] and lay["inWin"] and not lay["sideways"] and abs(lay["h"] - h0) < 1 and lay["h"] <= lay["maxH"], (h0, lay))
        reply.locator(".where-buy-add button").first.click()
        page.wait_for_timeout(150)
        check("Add works from the Mentor answer too", [x["id"] for x in gear(page)] == ["wet palette"], gear(page))
        page.fill(".mentor-input", "what colour for armour")
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        check("a colour answer has no Where to buy", page.locator(".mentor-reply").last.locator(".where-buy").count() == 0)

        print("\n--- 7. Phone sizes, dark and light ---")
        long_gear = [{"id": "airbrush cleaning kit", "name": "airbrush cleaning kit", "from": "Cleaning an airbrush between colours"}]
        page.keyboard.press("Escape")
        page.wait_for_selector(".mentor-backdrop", state="detached")
        page.evaluate("(g) => { book.gear = g; save(); }", long_gear)
        for (w, h), scheme in (((390, 844), "dark"), ((360, 640), "light"), ((320, 640), "dark")):
            page.set_viewport_size({"width": w, "height": h})
            page.emulate_media(color_scheme=scheme)
            page.evaluate("(s) => { settings.appearance = s; setAppearanceMark(); }", scheme)
            open_entry(page, "airbrush-cleaning")
            page.click(".guides-entry .where-buy > summary")
            fit = page.evaluate("""() => [...document.querySelectorAll('.guides-entry .where-buy-item')].every(li => { const r = li.getBoundingClientRect();
                return [...li.querySelectorAll('.where-buy-name, a, button, .shop-onlist')].every(x => { const q = x.getBoundingClientRect(); return q.left >= r.left - 1 && q.right <= r.right + 1; }); })""")
            ok_g = no_sideways(page) and fit and small_taps(page, ".guides-entry .where-buy") == 0
            open_shop(page)
            fit2 = page.evaluate("""() => [...document.querySelectorAll('#shop-panel .shop-gear-item')].every(li => { const r = li.getBoundingClientRect(),
                t = li.querySelector('.shop-text').getBoundingClientRect(), b = li.querySelector('.shop-remove').getBoundingClientRect();
                return t.left >= r.left - 1 && t.right <= b.left + 1 && b.right <= r.right + 1 && t.width > 60; })""")
            check(f"{w}x{h} {scheme}: no sideways scroll, 44 px taps, Where to buy and Gear rows wrap and keep their names",
                  ok_g and no_sideways(page) and fit2 and small_taps(page, "#shop-panel .shop-gear-list") == 0, (ok_g, fit, fit2))
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
