"""SF4 test for Minifolio (Filters sheet: changing the Game keeps a faction that fits, flags one that does not, with Undo). New behaviour only.
The older SF3 check "choosing another game clears the faction" still holds: its faction (Gloom Legion) is not in the other game."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def unit(i, hobby, faction, stage=1):
    return {"id": i, "name": f"Squad {i}", "hobby": hobby, "faction": faction, "stage": stage, "count": 1, "added": "2026-09-01", "log": [["2026-09-01", 0], ["2026-09-02", stage]]}

# Skirmish: Bright Host, Gloom Legion, Shared. Fantasy: Moss Court, Shared, <b>Odd</b> (to prove names are shown as plain text).
UNITS = [unit(1, "Skirmish", "Bright Host"), unit(2, "Skirmish", "Gloom Legion"), unit(3, "Skirmish", "Gloom Legion"), unit(4, "Skirmish", "Shared"),
         unit(5, "Fantasy", "Moss Court"), unit(6, "Fantasy", "Shared"), unit(7, "Fantasy", "<b>Odd</b>")]

def chip(page, group, text): return page.locator(f"#fs-chips-{group} .chip", has_text=text)
def count_text(page): return page.locator("#fs-show").text_content().strip()
def faction_chips(page): return [c.strip() for c in page.locator("#fs-chips-faction .chip").all_text_contents()]
def flt(page): return page.evaluate("[filters.hobby, filters.faction].join('|')")
def toast_open(page): return page.evaluate("!document.getElementById('toast').classList.contains('hidden')")
def toast_text(page): return page.text_content("#toast-text")
def open_sheet(page):
    if not page.evaluate("() => !!document.getElementById('filters-sheet')"): page.click("#toggle-filters")
    page.wait_for_selector("#filters-sheet .fs-chip")
    page.wait_for_function("() => !document.getAnimations().some(a => a.playState === 'running')")
def fresh(page, **settings):
    t.load(page, units=UNITS, settings={"examplesChecked": True, **settings})
    page.click('nav button[data-tab="units"]'); t.quiet(page); open_sheet(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        fresh(page)

        print("\n--- 1. A faction that fits is kept ---")
        chip(page, "game", "Skirmish").click(); chip(page, "faction", "Shared").click()
        chip(page, "game", "Fantasy").click()
        check("Shared is in both games: it stays chosen and no message appears", flt(page) == "Fantasy|Shared" and not toast_open(page), flt(page))
        check("the count follows (Shared in Fantasy is 1 unit)", count_text(page) == "Show 1 unit", count_text(page))
        chip(page, "game", "All games").click()
        check("All games keeps the faction too", flt(page) == "|Shared" and count_text(page) == "Show 2 units" and not toast_open(page), (flt(page), count_text(page)))
        chip(page, "faction", "Moss Court").click(); chip(page, "game", "Fantasy").click()
        check("a faction chosen under All games stays when its game is chosen", flt(page) == "Fantasy|Moss Court" and not toast_open(page), flt(page))

        print("\n--- 2. A faction that does not fit is cleared, with a message and Undo ---")
        chip(page, "game", "Skirmish").click()
        check("the faction is cleared and the factions shown are Skirmish's only",
              flt(page) == "Skirmish|" and faction_chips(page) == ["All factions", "Bright Host", "Gloom Legion", "Shared"], (flt(page), faction_chips(page)))
        check("the message names the faction and the game, no em dash", toast_open(page) and toast_text(page) == "Faction Moss Court cleared (not in Skirmish)." and "—" not in toast_text(page), toast_text(page))
        check("the message has an Undo button", page.text_content("#toast-undo").strip() == "Undo" and page.locator("#toast-undo").is_visible())
        page.click("#toast-undo")
        check("Undo puts back the game and the faction", flt(page) == "Fantasy|Moss Court", flt(page))
        check("the sheet shows Fantasy's factions again and the count is right",
              faction_chips(page) == ["All factions", "<b>Odd</b>", "Moss Court", "Shared"] and count_text(page) == "Show 1 unit", (faction_chips(page), count_text(page)))
        check("a faction name with tags in it is shown as plain words", page.locator("#fs-chips-faction b").count() == 0)

        print("\n--- 3. The toasted state no longer current ---")
        chip(page, "game", "Skirmish").click()
        chip(page, "faction", "Gloom Legion").click()
        page.click("#toast-undo") if toast_open(page) else None
        check("Undo after choosing another faction leaves the filters as they are", flt(page) == "Skirmish|Gloom Legion", flt(page))
        chip(page, "faction", "All factions").click(); chip(page, "game", "Fantasy").click(); chip(page, "faction", "<b>Odd</b>").click()
        chip(page, "game", "Skirmish").click()
        check("a newer message replaces the older one", toast_text(page) == "Faction <b>Odd</b> cleared (not in Skirmish).", toast_text(page))
        page.keyboard.press("Escape")
        check("closing the sheet does not break it: filters stay, no page error", flt(page) == "Skirmish|" and not [e for e in errors if "woff2" not in e], (flt(page), errors))
        page.click("#toast-undo")
        check("Undo after the sheet is closed still puts both back", flt(page) == "Fantasy|<b>Odd</b>", flt(page))
        check("the Filters button counts them", page.text_content("#toggle-filters").strip() == "Filters (2)", page.text_content("#toggle-filters"))

        print("\n--- 4. Where the message sits, at phone sizes, light and dark, two looks ---")
        for w, h, mode, theme in ((390, 844, "dark", "classic"), (360, 640, "light", "classic"), (320, 568, "dark", "bench"), (320, 568, "light", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            fresh(page, theme=theme, appearance=mode)
            chip(page, "game", "Skirmish").click(); chip(page, "faction", "Gloom Legion").click(); chip(page, "game", "Fantasy").click()
            page.wait_for_selector("#toast:not(.hidden)")
            # the message slides up (mo-toast-in); its thin drain line runs for the whole 10 seconds, so only the message's own move is waited for
            page.wait_for_function("() => !document.getElementById('toast').getAnimations().some(a => a.playState === 'running' && !(a.effect && a.effect.pseudoElement))")
            m = page.evaluate("""() => { const T = document.getElementById('toast'), r = T.getBoundingClientRect(), u = document.getElementById('toast-undo').getBoundingClientRect(),
                f = document.querySelector('#filters-sheet .fs-foot').getBoundingClientRect(), mid = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return { aboveFoot: r.bottom <= f.top + 1, onScreen: r.left >= 0 && r.right <= innerWidth + 1 && r.top >= 0, hit: T.contains(mid), undoH: u.height, undoW: u.width,
                         font: parseFloat(getComputedStyle(document.getElementById('toast-text')).fontSize), side: document.documentElement.scrollWidth <= innerWidth + 1,
                         buttons: [...document.querySelectorAll('#fs-clear, #fs-show')].every(b => { const q = b.getBoundingClientRect(); return T.contains(document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2)) === false; }) }; }""")
            check(f"{w}x{h} {mode} {theme}: above Clear all and Show, on top of the sheet, Undo 44 px or more, text 14 px or more, no sideways scroll",
                  m["aboveFoot"] and m["onScreen"] and m["hit"] and m["buttons"] and m["undoH"] >= 43.5 and m["undoW"] >= 43.5 and m["font"] >= 14 and m["side"], m)
            page.keyboard.press("Escape")
            n = page.evaluate("""() => { const r = document.getElementById('toast').getBoundingClientRect(), tabs = document.querySelector('nav.tabs').getBoundingClientRect();
                return { clear: r.bottom <= tabs.top + 1 || r.top >= tabs.bottom - 1 }; }""")
            check(f"{w}x{h} {mode} {theme}: with the sheet shut the message sits clear of the bottom menu", n["clear"], n)
        check("no page errors", not [e for e in errors if "woff2" not in e], errors)
        browser.close()
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

main()
