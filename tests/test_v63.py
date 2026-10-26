"""v63 tests for Minifolio (chunk 3.3: popular ranges first in the colour wheel, shorter lists).

What changed:
 In the Compendium colour wheel, each group shows 12 paints before Show all (it was 8). The order inside a group is now:
 your own paints, the rest of Your Palette, then built-in paints from the popular ranges (Citadel, The Army Painter, Vallejo),
 then built-in paints from other brands. Each of those runs dark to light. There is no "popular" in the paint data, so the
 list lives in POPULAR_BRANDS in app.js (chosen by George). No colour maths and no paint content changed.

Checks:
1. Versions, the v63 Updates entry, DATA_VERSION is still 1.
2. POPULAR_BRANDS and the group size of 12.
3. With nothing of yours in Blues: the first 12 built-in paints shown are all from popular ranges, dark to light, and
   Show all lists every paint, other brands after popular ones.
4. A paint of yours from an unknown brand still comes before every popular paint.
5. Help names the order and the popular ranges. No em dash in the new Updates entry or the Help line.
6. 390 px and 360 px, dark and light: no sideways scroll, Show all 44 px or more.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import wheel_helpers as wh
import test_v31 as t
import test_v37b as w   # the wheel's row reader, the Compendium tab, made-up paints

read, load, no_sideways = t.read, t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

POPULAR = ["Citadel", "The Army Painter", "Vallejo"]

# The Blues group as the app sorts it, built-in paints only: [{ name, brand, popular, L }]
GROUP_JS = """() => wheelItems().filter(i => i.at.seg === 'blue' && i.at.sub === 'blue')
    .sort((a, b) => a.origin - b.origin || wheelPopular(a) - wheelPopular(b) || a.at.L - b.at.L || String(a.paint.name).localeCompare(String(b.paint.name)))
    .map(i => ({ name: i.paint.name, brand: i.paint.brand, origin: i.origin, popular: POPULAR_BRANDS.includes(i.paint.brand), L: i.at.L }))"""

def open_blues(page, paints):
    load(page, paints=paints)
    w.open_tab(page)
    wh.zoom_in(page, "blue")
    wh.open_group(page, "blue", "blue")
    if page.locator("#cmp-wheel-others").count() and page.get_attribute("#cmp-wheel-others", "aria-expanded") != "true":
        page.click("#cmp-wheel-others")
        page.wait_for_timeout(150)

def main():
    errors, dialogs = [], []
    app = read("app.js")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        load(page, paints=[])
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v63')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry says 12 and popular ranges, and names no brand (no Games Workshop names in our words)", "12" in joined and "popular ranges" in joined and not any(b in joined for b in POPULAR), joined)

        # ---------- 2. The settings ----------
        print("\n--- 2. Popular ranges and group size ---")
        check("POPULAR_BRANDS is Citadel, The Army Painter and Vallejo", page.evaluate("POPULAR_BRANDS") == POPULAR, page.evaluate("POPULAR_BRANDS"))
        check("every popular brand is a brand the app knows", page.evaluate("POPULAR_BRANDS.every(b => PAINT_BRANDS.includes(b))"))
        check("a wheel group shows 12 before Show all", page.evaluate("WHEEL_GROUP_SHOWN") == 12)

        # ---------- 3. Nothing of yours in Blues ----------
        print("\n--- 3. Popular first, with nothing of yours ---")
        open_blues(page, [])
        rows = page.evaluate(w.ROWS_JS)
        group = page.evaluate(GROUP_JS)
        pop = [g for g in group if g["popular"]]
        check("Blues has more than 12 popular paints, so the short list can be all popular", len(pop) > 12, len(pop))
        check("the group shows 12 paints", len(rows) == 12, len(rows))
        check("they are the first 12 in the new order", [r["name"] for r in rows] == [g["name"] for g in group[:12]], ([r["name"] for r in rows], [g["name"] for g in group[:12]]))
        check("all 12 are from popular ranges", all(g["popular"] for g in group[:12]), [g["brand"] for g in group[:12]])
        Ls = [g["L"] for g in group[:12]]
        check("they run dark to light", Ls == sorted(Ls), Ls)
        more = page.locator("#cmp-wheel-more-blue")
        check("there is a Show all button with the full count", more.count() == 1 and page.inner_text("#cmp-wheel-more-blue") == f"Show all {len(group)}", page.inner_text("#cmp-wheel-more-blue") if more.count() else None)
        more.click()
        page.wait_for_timeout(150)
        rows_all = page.evaluate(w.ROWS_JS)
        flags = [g["popular"] for g in group]
        first_other = flags.index(False) if False in flags else len(flags)
        check("Show all lists every paint in the group", len(rows_all) == len(group), (len(rows_all), len(group)))
        check("in the full list, every popular paint comes before every other brand", all(flags[:first_other]) and not any(flags[first_other:]), first_other)
        rest = [g["L"] for g in group[first_other:]]
        check("the other brands run dark to light too", rest == sorted(rest))

        # ---------- 4. Yours still first ----------
        print("\n--- 4. Your paints stay first ---")
        mine = w.P(901, "Own Odd Blue", w.hx(220, .6, .55), brand="Nobody Knows Paints")
        open_blues(page, [mine])
        rows = page.evaluate(w.ROWS_JS)
        check("your paint from an unknown brand is first, ahead of the popular ranges", rows and rows[0]["name"] == "Own Odd Blue" and rows[0]["tag"] == "You own this", rows[:2])
        group = page.evaluate(GROUP_JS)
        check("12 in all: yours, then 11 built-in paints, all popular", len(rows) == 12 and all(g["popular"] for g in group[1:12]), len(rows))

        # ---------- 5. Help and wording ----------
        print("\n--- 5. Help ---")
        help_li = page.evaluate("() => { const e = document.getElementById('help-wheel-order'); return e ? e.textContent : ''; }")
        check("Help has a line on the wheel's order: 12, popular ranges, Show all, and no brand names", "12" in help_li and "popular ranges" in help_li and "Show all" in help_li and not any(b in help_li for b in POPULAR), help_li)
        check("no em dash in the Help line or the v63 Updates entry", "—" not in help_li and "—" not in app[app.index('{ version: "v63"'):app.index('{ version: "v62"')])
        check("the wheel's group sentence says popular ranges come next", "yours first, then popular ranges" in app)

        # ---------- 6. Phones, dark and light ----------
        print("\n--- 6. Phones ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                open_blues(page, [])
                h = page.evaluate("() => { const b = document.getElementById('cmp-wheel-more-blue'); return b ? b.getBoundingClientRect().height : 0; }")
                check(f"{width} px {scheme}: no sideways scroll, Show all is 44 px or more", no_sideways(page) and h >= 44, h)
                page.click("#cmp-wheel-more-blue")
                page.wait_for_timeout(120)
                check(f"{width} px {scheme}: with Show all open, still no sideways scroll", no_sideways(page))
        page.emulate_media(color_scheme="dark")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Errors ----------
        print("\n--- 7. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
