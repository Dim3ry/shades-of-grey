"""v41 tests for Minifolio (Shopping 2, part A): the Compendium remembers where its shopping-list paints came from, and shows what is already on the list.

What changed:
 - The colour wheel's paint panel records "Compendium: Colour wheel, <the colour part you were in>" when you tap Add to shopping list.
 - The Compendium's Colour ideas record "Compendium: Colour ideas".
 - Both use the one shared list and the one place sources are kept (the paint's own shopFrom notes). Nothing else was added to hold them.
 - A paint that is already on the shopping list says "On your shopping list" on its row in the Compendium (wheel lists, matching colours, Colour ideas).
   The words stay right after Add and after Undo, and the basket count follows.
 - The scheme buttons ("Add paints to shopping list" on starter and your own schemes) are part B, not in this release.

Checks:
1. Versions, Updates entry, nothing else touched (no new address, no Games Workshop words, shop links and the Pro preview label unchanged).
2. Sources: the wheel panel (a hue part and a neutral part) and Colour ideas, kept on the one paint, shown on the Shopping list.
3. Markers: wheel lists, matching colours and Colour ideas say On your shopping list; they flip in place on Add and back on Undo; the basket count agrees.
4. Shop links off: the markers and the basket stay. Copy as text keeps the words.
5. Hostile text (text-injection test): paint and brand names are plain text everywhere new.
6. Phones and looks: 360 and 390 px, dark and light, no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v35 as c   # Compendium helpers (open every part, pick a start colour)
import test_v39 as h   # wheel and paint-panel helpers, the made-up Probe paints

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur = t.read, t.load, t.blur
shot, no_sideways = t.shot, t.no_sideways
HOSTILE, HOSTILE_BRAND = t.HOSTILE, t.HOSTILE_BRAND
GW_WORDS = t.GW_WORDS
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

LISTED = "On your shopping list"
WHEEL_SRC = "Compendium: Colour wheel, "
IDEAS_SRC = "Compendium: Colour ideas"
P, at = h.P, h.at
BASE = "test paints|probe blue"

def count_text(page):
    return page.evaluate("() => { const b = document.getElementById('basket-button'); return b.classList.contains('hidden') ? '' : b.textContent.trim(); }")

def source_of(page, name):
    return next((p.get("shopFrom") for p in h.stored_paints(page) if p["name"] == name), "missing")

def panel_tags(page):
    return {r["name"]: r["tag"] for r in h.prows(page) if r["section"] != h.STARTER_LABEL}

def ideas_rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-ideas-panel > .idea-list > li')].map(li => ({
        name: li.querySelector('.idea-name').childNodes[0].textContent, brand: (li.querySelector('.idea-name small') || {}).textContent || '', tag: li.querySelector('.idea-tag').textContent,
        fold: !!li.querySelector('.shop-more'), add: li.querySelectorAll('.shop-add button').length }))""")

def open_ideas(page, paints, settings=None):
    load(page, paints=paints, settings=settings)
    c.open_comp(page)
    c.pick_base(page, BASE)
    page.wait_for_timeout(150)

def wheel_rows_everywhere(page):
    """name -> tag for every paint row in the wheel's lists, tapping each of the ten parts in turn."""
    out = {}
    for key in ["red", "orange", "yellow", "green", "blue", "purple", "white", "grey", "black", "metallic"]:
        h.open_tab(page)
        h.tap(page, key)
        for name, tag in page.evaluate("() => [...document.querySelectorAll('#cmp-wheel-detail ul.idea-list > li')].map(li => [li.querySelector('.idea-name').childNodes[0].textContent, li.querySelector('.idea-tag').textContent])"):
            out.setdefault(name, tag)
        h.tap(page, key)   # close it again
    return out

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions and what did not change ----------
        print("\n--- 1. Versions and what did not change ---")
        load(page, paints=h.UNOWNED)
        html, sw = read("index.html"), read("sw.js")
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("the version is v41 in APP_VERSION, sw.js and all six script tags",
              page.evaluate("APP_VERSION") in ("v41", "v42") and re.search(r'const VERSION = "v([\d.]+)"', sw).group(1) in ("41", "42") and len(tags) == 6 and len({v for _, v in tags}) == 1,
              (page.evaluate("APP_VERSION"), tags))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v41')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the newest Updates entry is v41 and tells about where a paint came from and On your shopping list",
              entry and entry["version"] == "v41" and all(w in joined for w in ("Colour wheel", "Colour ideas", "same list", LISTED)), joined[:120])
        diff = subprocess.run(["git", "diff", "main", "--", "app.js"], cwd=ROOT, capture_output=True, text=True).stdout
        added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        code_added = [re.sub(r"\s//\s.*$", "", l) for l in added if not l.strip().startswith("//")]
        check("no new web address, network call or storage in the new code",
              not any(re.search(r"https?:|fetch\(|XMLHttpRequest|localStorage|indexedDB|WebSocket|sendBeacon", l) for l in code_added), [l for l in code_added if "http" in l][:2])
        check("nothing was added that writes page text from variables (no innerHTML, insertAdjacentHTML or outerHTML)",
              not any(re.search(r"innerHTML|insertAdjacentHTML|outerHTML|document\.write|eval\(", l) for l in code_added))
        check("no Games Workshop word in anything added", not [l for l in added if GW_WORDS.search(l)], [l for l in added if GW_WORDS.search(l)][:2])
        check("the shop links, the shop table and the Pro preview label were not touched (only checked while v41 is the newest version, because it compares with main)",
              page.evaluate("APP_VERSION") != "v41" or not any(re.search(r"shopLink|SHOPS|shopsFor|SHOP_PLAIN_WORDS|Pro preview|pro-pill", l) for l in added + removed))
        html_diff = subprocess.run(["git", "diff", "main", "--", "index.html"], cwd=ROOT, capture_output=True, text=True).stdout
        html_changed = [l[1:] for l in html_diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        check("index.html only changed the version number (so no security-policy entry was added or changed) (only checked while v41 is the newest version, because it compares with main)",
              page.evaluate("APP_VERSION") != "v41" or html_changed and all("?v=4" in l for l in html_changed) and not any("Content-Security-Policy" in l for l in html_changed), html_changed[:3])
        check("no new file in the repo", subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.count("??") <= 1)   # only this test file

        # ---------- 2. Sources ----------
        print("\n--- 2. Sources ---")
        h.panel_for(page, h.JUST_BLUE)
        first = h.prows(page)[0]["name"]
        h.open_fold(page, 0)
        page.click("#cmp-paint-panel .shop-more .shop-add button")
        page.wait_for_timeout(250)
        check("Add in the wheel's matching colours (Blue) records Compendium: Colour wheel, Blue on the one paint", source_of(page, first) == [WHEEL_SRC + "Blue"], source_of(page, first))
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(200)
        page.click('#recipe-seg [data-view="shopping"]')
        page.wait_for_timeout(150)
        text = page.inner_text("#shop-panel")
        check("the Shopping list shows that paint once, saying from Compendium: Colour wheel, Blue", text.count(first) == 1 and "from " + WHEEL_SRC + "Blue" in text, text[:200])
        check("the Copy as text for the list keeps the words", "(from " + WHEEL_SRC + "Blue" in page.evaluate("() => shoppingText(shoppingItems())"))

        h.panel_for(page, [P(1, "Probe Grey", "#8a8a8a")], key="grey", name="Probe Grey")
        first = h.prows(page)[0]["name"]
        h.open_fold(page, 0)
        page.click("#cmp-paint-panel .shop-more .shop-add button")
        page.wait_for_timeout(250)
        check("a grey paint opened from the Greys part records Compendium: Colour wheel, Greys", source_of(page, first) == [WHEEL_SRC + "Greys"], source_of(page, first))

        open_ideas(page, h.JUST_BLUE)
        r0 = ideas_rows(page)
        check("Compendium Colour ideas show unowned paints with a closed shop fold-out (as before)", len(r0) >= 3 and all(r["fold"] and r["add"] == 1 for r in r0), r0)
        page.locator("#cmp-fold-ideas-panel > .idea-list > li .shop-more > summary").first.click()
        page.locator("#cmp-fold-ideas-panel > .idea-list > li .shop-add button").first.click()
        page.wait_for_timeout(250)
        check("Add in the Compendium's Colour ideas records Compendium: Colour ideas on the one paint",
              source_of(page, r0[0]["name"]) == [IDEAS_SRC], source_of(page, r0[0]["name"]))
        check("the basket counts that one paint", count_text(page) == "1", count_text(page))

        # one paint, one entry, whichever door it came in by: add from the ideas, then the wheel's matches show it already listed
        paints_now = [x for x in h.stored_paints(page) if x["name"] == r0[0]["name"]]
        check("it is in the palette once (no second paint, no second list)", len(paints_now) == 1, paints_now)

        # ---------- 3. Markers ----------
        print("\n--- 3. Markers ---")
        h.panel_for(page, h.UNOWNED)
        tags = panel_tags(page)
        check("in the matching colours, paints on your wishlist or marked empty say On your shopping list", tags.get("Probe Left") == LISTED and tags.get("Probe Right") == LISTED, tags)
        check("a paint in your palette that is not on the list, and one that is not in your palette, keep their usual words",
              tags.get("Probe Opposite") in ("Not in your palette", "In your palette, not owned") and LISTED not in (tags.get("Probe Opposite"), tags.get("Probe Triad A")), tags)
        check("the basket already counts the two paints on the list", count_text(page) == "2", count_text(page))

        h.open_fold(page, [r["name"] for r in h.prows(page) if r["section"] != h.STARTER_LABEL].index("Probe Opposite"))
        page.evaluate("() => { for (const li of document.querySelectorAll('#cmp-paint-panel ul.idea-list > li')) if (li.textContent.includes('Probe Opposite')) li.__mark = 'same row'; }")
        page.locator("#cmp-paint-panel li", has_text="Probe Opposite").locator(".shop-add button").click()
        page.wait_for_timeout(250)
        flip = page.evaluate("() => { const li = [...document.querySelectorAll('#cmp-paint-panel ul.idea-list > li')].find(x => x.textContent.includes('Probe Opposite')); return { mark: li.__mark, tag: li.querySelector('.idea-tag').textContent, cls: li.querySelector('.idea-tag').className }; }")
        check("after Add, that row's words change to On your shopping list in place (the row is not redrawn)", flip["mark"] == "same row" and flip["tag"] == LISTED and "none" in flip["cls"], flip)
        check("the basket went from 2 to 3 straight away", count_text(page) == "3", count_text(page))
        check("the source is the part you were in", source_of(page, "Probe Opposite") == [WHEEL_SRC + "Blue"], source_of(page, "Probe Opposite"))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        h.reopen_panel(page)
        tags = panel_tags(page)
        check("after Undo the words go back and the basket goes back to 2", tags.get("Probe Opposite") != LISTED and tags.get("Probe Left") == LISTED and count_text(page) == "2", (tags, count_text(page)))
        check("after Undo the paint has forgotten where it came from", source_of(page, "Probe Opposite") in (None, "missing"), source_of(page, "Probe Opposite"))

        h.open_tab(page)
        every = wheel_rows_everywhere(page)
        check("in the wheel's own lists, paints on the list say On your shopping list (they used to say On your wishlist)", every.get("Probe Left") == LISTED and every.get("Probe Right") == LISTED, every)
        check("the other paints in those lists keep their words (owned, in your palette, or not in it)", every.get("Probe Blue") == "You own this" and LISTED not in (every.get("Probe Opposite"), every.get("Probe Triad A"), every.get("Probe Triad B")), every)

        open_ideas(page, h.JUST_BLUE)
        listed_name = ideas_rows(page)[0]["name"]
        known = page.evaluate("([n, b]) => KNOWN_PAINTS.find(k => k.name === n && k.brand === b)", [listed_name, ideas_rows(page)[0]["brand"]])
        ideas_palette = [h.BLUE, P(2, listed_name, known["colour"], "wishlist", brand=known["brand"])]
        open_ideas(page, ideas_palette)
        rr = {r["name"]: r for r in ideas_rows(page)}
        check("in Colour ideas, a paint already on the list says On your shopping list", rr.get(listed_name, {}).get("tag") == LISTED and count_text(page) == "1", (list(rr.values())[:4], count_text(page)))
        page.locator("#cmp-fold-ideas-panel > .idea-list > li", has_text=listed_name).locator("summary").click()
        shows = page.locator("#cmp-fold-ideas-panel > .idea-list > li", has_text=listed_name).locator(".shop-onlist").count()
        adds = page.locator("#cmp-fold-ideas-panel > .idea-list > li", has_text=listed_name).locator(".shop-add button").count()
        check("and its fold-out shows no Add button (it says the same words)", shows == 1 and adds == 0, (shows, adds))
        pick = next(r for r in ideas_rows(page) if r["tag"] != LISTED)
        idx = [r["name"] for r in ideas_rows(page)].index(pick["name"])
        page.locator("#cmp-fold-ideas-panel > .idea-list > li").nth(idx).locator("summary").click()
        page.locator("#cmp-fold-ideas-panel > .idea-list > li").nth(idx).locator(".shop-add button").click()
        page.wait_for_timeout(250)
        after = ideas_rows(page)[idx]
        check("after Add in Colour ideas, that row says On your shopping list and the basket goes from 1 to 2", after["tag"] == LISTED and count_text(page) == "2", (after, count_text(page)))
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        c.open_comp(page)
        check("after Undo that row's words and the basket are back", count_text(page) == "1" and LISTED not in [r["tag"] for r in ideas_rows(page) if r["name"] == pick["name"]], (count_text(page), ideas_rows(page)))

        # ---------- 4. Shop links off, and Copy as text ----------
        print("\n--- 4. Shop links off, and Copy as text ---")
        h.panel_for(page, h.UNOWNED, settings={"hideShopLinks": True})
        tags = panel_tags(page)
        check("with Show shop links off: no shop fold-out anywhere, but the words and the basket stay",
              page.locator(".shop-more").count() == 0 and tags.get("Probe Left") == LISTED and count_text(page) == "2", (tags, count_text(page)))
        h.panel_for(page, h.UNOWNED)
        c.copy_spy(page)
        page.click("#cmp-paint-panel .share-row button")
        out = c.copied(page) or ""
        check("Copy as text for the matching colours says On your shopping list for the paints on it", re.search(r"Probe Left[^\n]*" + LISTED, out) is not None, out[:300])

        # ---------- 5. Hostile text ----------
        print("\n--- 5. Hostile text ---")
        hp = [h.BLUE, P(2, HOSTILE, at(180), "wishlist", brand=HOSTILE_BRAND), P(3, HOSTILE + " B", at(30), "notowned", brand=HOSTILE_BRAND), P(4, "Probe Right", at(-30), "notowned")]
        h.panel_for(page, hp)
        h.open_fold(page, 2)
        bad = page.evaluate("() => ({ pwned: window.__pwned || 0, bad: document.querySelectorAll('#compendium-body img, #compendium-body script, #compendium-body b').length, html: document.getElementById('compendium-body').innerHTML, text: document.getElementById('compendium-body').textContent })")
        check("hostile paint and brand names show as plain words in the wheel panel: no picture, script or bold appears and nothing runs",
              bad["pwned"] == 0 and bad["bad"] == 0 and "<img" in bad["text"] and "&lt;img" in bad["html"], bad["bad"])
        tags = panel_tags(page)
        check("the hostile paint on the wishlist gets the words On your shopping list like any other", tags.get(HOSTILE) == LISTED, list(tags)[:4])
        page.locator("#cmp-paint-panel li", has_text="Probe Right").locator("summary").click()
        page.locator("#cmp-paint-panel li", has_text="Probe Right").locator(".shop-add button").click()
        page.wait_for_timeout(250)
        check("the saved source is exactly the fixed words, whatever the paints are called", source_of(page, "Probe Right") == [WHEEL_SRC + "Blue"], source_of(page, "Probe Right"))
        open_ideas(page, hp)
        bad2 = page.evaluate("() => ({ pwned: window.__pwned || 0, bad: document.querySelectorAll('#compendium-body img, #compendium-body script, #compendium-body b').length })")
        check("hostile names in Colour ideas and the wheel's lists are plain text too", bad2["pwned"] == 0 and bad2["bad"] == 0, bad2)
        h.open_tab(page)
        for key in ["red", "orange", "yellow", "green", "blue", "purple"]:
            h.tap(page, key)
            h.tap(page, key)
        check("the hostile paint's row in the wheel's lists is plain text", page.evaluate("() => (window.__pwned || 0) === 0 && document.querySelectorAll('#compendium-body img, #compendium-body b').length === 0"))

        # ---------- 6. Phones and looks ----------
        print("\n--- 6. Phones and looks ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 780})
                h.panel_for(page, h.UNOWNED, settings={"appearance": appearance})
                tag = f"{appearance} {width}px"
                fits = page.evaluate("() => [...document.querySelectorAll('#cmp-paint-panel .idea-tag')].every(e => e.getBoundingClientRect().right <= innerWidth)")
                check(f"{tag}: the new words fit on the screen and nothing scrolls sideways", fits and no_sideways(page))
                shot(page, f"v41-compendium-listed-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})
        check("no page error and no unexpected dialog during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
