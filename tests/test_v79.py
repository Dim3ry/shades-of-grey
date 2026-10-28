"""v79 tests for Minifolio (chunk R2b: the Units tab shows open unit details in a side pane on wide screens).

What changed:
 From 900 px the unit list is on the left and the details of every open unit are stacked as cards in a pane on the right,
 each with a Close button. Under 900 px the details still open inside the unit's own card.

Checks:
1. 899 px (and 390 / 360): details inside the card, no side pane, no sideways scroll. Dark and light.
2. 900 px and 1280 px: list left, pane right, same top, open card marked. Dark and light, no sideways scroll.
3. Several units open at once, closing one, closing all (the list gets the full width back). Tap targets 44 px or more.
4. Select mode hides the pane; leaving it brings the pane back.
5. Delete then Undo from the pane.
6. Crossing 900 px with details open moves them between the card and the pane.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways, unit = t.load, t.no_sideways, t.unit
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [unit(1, "Troop A", "Gloom Legion"), unit(2, "Troop B", "Gloom Legion"), unit(3, "Other", "Other Host")]

def state(page):
    return page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
        const shown = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; };
        return { side: shown('#unit-side'), cards: document.querySelectorAll('#unit-side .unit-side-card').length,
                 inline: document.querySelectorAll('#unit-list .panel').length,
                 list: r('#unit-list'), pane: r('#unit-side') }; }""")

def tap(page, name):
    page.click(f'#unit-list li.unit:has-text("{name}") .info')

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        load(page, units=UNITS)
        page.click('nav button[data-tab="units"], nav button[data-tab="units"]')

        print("\n--- 1. Under 900 px: unchanged ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (360, 390, 899):
                page.set_viewport_size({"width": width, "height": 900})
                tap(page, "Troop A")
                s = state(page)
                check(f"{scheme} {width}: details inside the card, no pane", s["inline"] == 1 and not s["side"] and s["cards"] == 0, s)
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                tap(page, "Troop A")
                check(f"{scheme} {width}: tapping again closes it", state(page)["inline"] == 0)

        print("\n--- 2. 900 px and wider: side by side ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for width in (900, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                tap(page, "Troop A")
                s = state(page)
                check(f"{scheme} {width}: list left, pane right, same top, no inline panel",
                      s["side"] and s["cards"] == 1 and s["inline"] == 0 and s["list"]["left"] < s["pane"]["left"]
                      and abs(s["list"]["top"] - s["pane"]["top"]) < 2, s)
                check(f"{scheme} {width}: the open card is marked in the list",
                      page.evaluate("() => document.querySelector('#unit-list li.unit[aria-current=true]').textContent.includes('Troop A')"))
                check(f"{scheme} {width}: no sideways scroll", no_sideways(page))
                page.click("#unit-side .unit-side-card >> text=Close")
                check(f"{scheme} {width}: closing hides the pane", not state(page)["side"])

        print("\n--- 3. Several open, close one, close all ---")
        page.set_viewport_size({"width": 1280, "height": 900})
        tap(page, "Troop A"); tap(page, "Troop B"); tap(page, "Other")
        check("three units open as three stacked cards", state(page)["cards"] == 3, state(page))
        page.click('#unit-side .unit-side-card:has-text("Troop B") >> text=Close')
        names = page.inner_text("#unit-side")
        check("closing one leaves the other two", state(page)["cards"] == 2 and "Troop B" not in names.split("Close")[0] + names.split("Close")[1], names)
        small = page.evaluate("""() => [...document.querySelectorAll('#unit-side button, #unit-list .up-button, #unit-list .info')]
            .filter(b => b.offsetParent && b.tagName === 'BUTTON').map(b => b.getBoundingClientRect().height).filter(h => h < 43.5)""")
        check("buttons in the pane and the list are 44 px or taller", not small, small)
        tap(page, "Troop A")
        tap(page, "Other")
        s = state(page)
        check("closing all gives the list the full width back", not s["side"] and s["list"]["width"] > 1000, s)

        print("\n--- 4. Select mode ---")
        tap(page, "Troop A")
        page.click("#toggle-select")
        check("Select mode hides the pane", not state(page)["side"])
        page.click("#toggle-select")
        check("leaving Select mode brings the open unit back", state(page)["cards"] == 1, state(page))

        print("\n--- 5. Delete and Undo ---")
        page.click("#unit-side >> text=Delete")
        page.click("#dialog-yes")
        check("deleted: gone from the list and the pane", page.locator('#unit-list li.unit:has-text("Troop A")').count() == 0 and not state(page)["side"])
        page.click("#toast-undo")
        check("Undo brings the unit back, still open", page.locator('#unit-list li.unit:has-text("Troop A")').count() == 1 and state(page)["cards"] == 1, state(page))

        print("\n--- 6. Crossing 900 px ---")
        page.set_viewport_size({"width": 700, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("narrowing puts the details inside the card", s["inline"] == 1 and not s["side"], s)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(300)
        s = state(page)
        check("widening puts them in the pane again", s["inline"] == 0 and s["cards"] == 1, s)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
