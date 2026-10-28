"""v82 tests for Minifolio (chunk R3b-1: Dashboard and Settings on wide screens).

What changed:
 Dashboard from 900 px: the headline card and any notice card (backup, feedback) take the full row instead of half of it.
 With 4 or more factions the stage card and faction card each take a full row, so no gap sits beside the stage card.
 Settings was already right at every width and is only checked here.
 Under 900 px nothing changes.

Checks:
1. 899 px: Dashboard cards are one column and as wide as each other. Dark and light.
2. 900 / 1280 / 1920 px, dark and light: headline full row, no sideways scroll, nothing wider than 1280 px.
3. 4 or more factions at 1280 / 1920 px: stage and faction cards each span the full row. 3 factions: side by side.
4. Settings at 899 / 900 / 1280 / 1920 px: no sideways scroll, nothing wider than 1280 px, every tap target 44 px or more (a checkbox counts by its label)."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def units(n_factions):
    return [{"id": i, "name": f"Unit {i}", "faction": f"Faction {i % n_factions}", "stage": i % 4, "count": 5,
             "added": "2026-05-10", "log": []} for i in range(1, 13)]

def cards(page):
    return page.evaluate("""() => Object.fromEntries(['headline-card', 'history-card', 'stage-card', 'faction-card'].map(id => {
        const r = document.getElementById(id).getBoundingClientRect(); return [id, { x: r.x, w: r.width }]; }))""")

def show(page, tab, width):
    page.set_viewport_size({"width": width, "height": 1000})
    page.click(f'nav button[data-tab="{tab}"]')
    page.wait_for_timeout(250)

def small_taps(page, scope):
    return page.evaluate("""(scope) => [...document.querySelectorAll(scope + ' button, ' + scope + ' select, ' + scope + ' summary, ' + scope + ' input')]
        .filter(e => e.offsetParent).map(e => (e.closest('label') || e).getBoundingClientRect().height).filter(h => h < 43.5)""", scope)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block").new_page()
        load(page, units=units(3))
        page.evaluate("() => document.querySelectorAll('.notice-card').forEach(e => e.classList.add('hidden'))")

        print("\n--- 1. 899 px: one column ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            show(page, "dashboard", 899)
            c = cards(page)
            check(f"899 {scheme}: all cards the same left edge and width",
                  len({(round(v["x"]), round(v["w"])) for v in c.values()}) == 1, c)
            check(f"899 {scheme}: no sideways scroll", no_sideways(page))

        print("\n--- 2. Headline full row ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for w in (900, 1280, 1920):
                show(page, "dashboard", w)
                c = cards(page)
                check(f"{w} {scheme}: headline as wide as the history card", abs(c["headline-card"]["w"] - c["history-card"]["w"]) < 2, c)
                check(f"{w} {scheme}: content no wider than 1280 px, no sideways scroll",
                      c["history-card"]["w"] <= 1280.5 and no_sideways(page))
                check(f"{w} {scheme}: dashboard tap targets 44 px or more", not small_taps(page, "#view-dashboard"), small_taps(page, "#view-dashboard"))

        print("\n--- 3. Stage and faction cards ---")
        page.emulate_media(color_scheme="dark")
        show(page, "dashboard", 1280)
        c = cards(page)
        check("3 factions: stage and faction cards side by side", c["stage-card"]["x"] < c["faction-card"]["x"] and c["stage-card"]["w"] < 700, c)
        load(page, units=units(7))
        for w in (900, 1280, 1920):
            show(page, "dashboard", w)
            c = cards(page)
            check(f"7 factions at {w}: stage and faction cards each take the full row",
                  abs(c["stage-card"]["w"] - c["history-card"]["w"]) < 2 and abs(c["faction-card"]["w"] - c["history-card"]["w"]) < 2, c)
            check(f"7 factions at {w}: no sideways scroll", no_sideways(page))
        show(page, "dashboard", 899)
        c = cards(page)
        check("7 factions at 899: still one column", abs(c["stage-card"]["w"] - c["faction-card"]["w"]) < 2 and no_sideways(page), c)

        print("\n--- 4. Settings ---")
        for scheme in ("dark", "light"):
            page.emulate_media(color_scheme=scheme)
            for w in (899, 900, 1280, 1920):
                show(page, "settings", w)
                widest = page.evaluate("() => Math.max(...[...document.querySelectorAll('#view-settings > .card')].map(c => c.getBoundingClientRect().right - c.getBoundingClientRect().left))")
                check(f"settings {w} {scheme}: no sideways scroll, cards fit", no_sideways(page) and widest <= 1280.5, widest)
                check(f"settings {w} {scheme}: tap targets 44 px or more", not small_taps(page, "#view-settings"), small_taps(page, "#view-settings"))
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
