"""SF3 test for Minifolio (Models page: the Filters sheet). New behaviour only.
Run with the whole suite, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def unit(i, hobby, faction, stage, repaint=False):
    return {"id": i, "name": f"Squad {i}", "hobby": hobby, "faction": faction, "stage": stage, "count": 1, "added": "2026-09-01",
            "log": [["2026-09-01", 0], ["2026-09-02", stage]], "repaint": repaint}

# 2 games, 3 factions: Skirmish has Bright Host and Gloom Legion, Fantasy has Moss Court
UNITS = [unit(1, "Skirmish", "Bright Host", 0), unit(2, "Skirmish", "Gloom Legion", 2), unit(3, "Skirmish", "Bright Host", 7, True),
         unit(4, "Fantasy", "Moss Court", 3), unit(5, "Fantasy", "Moss Court", 7), unit(6, "Skirmish", "Gloom Legion", 5)]
MANY = [unit(i + 1, "Skirmish" if i % 2 else "Fantasy", f"Faction number {i + 1:02d} with a long name", i % 8) for i in range(34)]
OPEN = "() => !!document.getElementById('filters-sheet')"

def sheet(page): return page.locator("#filters-sheet")
def shown(page): return page.locator("#unit-list > li.unit").count()
def chip(page, group, text): return page.locator(f"#fs-chips-{group} .chip", has_text=text)
def pressed(page, group): return page.locator(f'#fs-chips-{group} .chip[aria-pressed="true"]').all_text_contents()
def count_text(page): return page.locator("#fs-show").text_content().strip()
def open_sheet(page):
    if not page.evaluate(OPEN): page.click("#toggle-filters")
    page.wait_for_selector("#filters-sheet .fs-chip")
    page.wait_for_function("() => !document.getAnimations().some(a => a.playState === 'running')")   # the sheet has finished rising

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=UNITS, settings={"examplesChecked": True})
        page.click('nav button[data-tab="units"]'); t.quiet(page)

        print("\n--- 1. Opening and closing ---")
        check("the old fold-away is gone", page.evaluate("() => ['filter-card', 'hobby-filter', 'faction-filter', 'group-chips', 'stage-chips', 'stage-chips-toggle'].every(i => !document.getElementById(i))"))
        check("the sheet is not there until Filters is tapped, and the button says only Filters", not page.evaluate(OPEN) and page.text_content("#toggle-filters").strip() == "Filters")
        page.click("#toggle-filters")
        page.wait_for_selector("#filters-sheet .fs-chip")
        info = page.evaluate("""() => { const d = document.querySelector('#filters-sheet [role=dialog]');
            return { modal: d.getAttribute('aria-modal'), title: document.getElementById(d.getAttribute('aria-labelledby')).textContent,
                     labels: [...d.querySelectorAll('.fs-label')].map(l => [l.textContent, getComputedStyle(l).textTransform]), inside: d.contains(document.activeElement) }; }""")
        check("a dialog titled Filters with four uppercase section labels, focus inside it",
              info["modal"] == "true" and info["title"] == "Filters" and info["inside"]
              and info["labels"] == [["Game", "uppercase"], ["Faction", "uppercase"], ["Progress", "uppercase"], ["Stage", "uppercase"]], info)
        page.click(".fs-close"); check("the X button closes it and focus goes back to Filters", not page.evaluate(OPEN) and page.evaluate("document.activeElement.id") == "toggle-filters")
        page.click("#toggle-filters"); page.keyboard.press("Escape"); check("Escape closes it", not page.evaluate(OPEN))
        page.click("#toggle-filters"); page.mouse.click(190, 20); check("a tap on the dim area closes it", not page.evaluate(OPEN))
        page.click("#toggle-filters"); page.click("#fs-show"); check("the main button closes it", not page.evaluate(OPEN))
        page.click("#toggle-filters")
        last = page.evaluate("""() => { const b = [...document.querySelectorAll('#filters-sheet button')].filter(x => !x.disabled); b[b.length - 1].focus(); return b[0].className; }""")
        page.keyboard.press("Tab")
        check("Tab from the last button goes back inside the sheet, not behind it", page.evaluate("() => document.querySelector('#filters-sheet .fs-sheet').contains(document.activeElement)"))
        page.keyboard.press("Shift+Tab")
        check("Shift+Tab from the first goes to the last, still inside", page.evaluate("() => document.querySelector('#filters-sheet .fs-sheet').contains(document.activeElement)"))

        print("\n--- 2. Each section sets the same filters as before ---")
        check("Game: All games, then each game; All games chosen", [c.strip() for c in page.locator("#fs-chips-game .chip").all_text_contents()] == ["All games", "Fantasy", "Skirmish"] and pressed(page, "game") == ["All games"], pressed(page, "game"))
        check("Faction: All factions, then every faction", page.locator("#fs-chips-faction .chip").count() == 4)
        chip(page, "game", "Skirmish").click()
        check("a game sets the game filter, ticks its chip (aria-pressed) and the factions shrink to that game",
              page.evaluate("filters.hobby") == "Skirmish" and pressed(page, "game") == ["Skirmish"] and page.locator("#fs-chips-faction .chip").count() == 3, pressed(page, "game"))
        check("the tick is drawn for the chosen chip", page.evaluate("() => getComputedStyle(document.querySelector('#fs-chips-game .chip[aria-pressed=true]'), '::before').opacity") == "1")
        check("the count says how many units match and the list behind already shows them", count_text(page) == "Show 4 units" and shown(page) == 4, (count_text(page), shown(page)))
        chip(page, "faction", "Gloom Legion").click()
        check("a faction sets the faction filter", page.evaluate("filters.faction") == "Gloom Legion" and count_text(page) == "Show 2 units" and shown(page) == 2)
        chip(page, "game", "Fantasy").click()
        check("choosing another game clears the faction (as before) and shows that game's factions", page.evaluate("filters.faction") == "" and page.locator("#fs-chips-faction .chip").count() == 2)
        chip(page, "game", "All games").click()
        sq = page.evaluate("""() => ({ f: [...document.querySelectorAll('#fs-chips-faction .chip .fs-dot')].length, s: [...document.querySelectorAll('#fs-chips-stage .chip .fs-dot')].length,
            n: document.querySelectorAll('#fs-chips-stage .chip').length, stages: STAGES.length, hidden: [...document.querySelectorAll('.fs-dot')].every(d => d.getAttribute('aria-hidden') === 'true') }); """)
        check("faction chips (not All factions) and every stage chip carry a colour square, hidden from screen readers",
              sq["f"] == 3 and sq["s"] == sq["n"] == sq["stages"] and sq["hidden"], sq)
        chip(page, "progress", "To do").click()
        check("To do chooses every to-do stage, as the old group chip did", page.evaluate("[...filters.stages].sort().join()") == page.evaluate("[...todoStages()].sort().join()"))
        chip(page, "progress", "To do").click()
        chip(page, "progress", "Done").click()
        check("Done chooses every done stage and the list follows", page.evaluate("[...filters.stages].sort().join()") == page.evaluate("[...doneStages()].sort().join()")
              and shown(page) == page.evaluate("models.filter(m => doneStages().includes(m.stage)).length") > 0, (shown(page), page.evaluate("[...doneStages()]")))
        chip(page, "progress", "Done").click()
        chip(page, "progress", "Repaint").click()
        check("Repaint turns the repaint filter on", page.evaluate("filters.repaint") is True and shown(page) == 1)
        chip(page, "progress", "Repaint").click()
        chip(page, "stage", page.evaluate("STAGES[0]")).click(); chip(page, "stage", page.evaluate("STAGES[3]")).click()
        check("several stages can be chosen together", page.evaluate("[...filters.stages].join()") == "0,3" and shown(page) == 2)
        check("the Filters button counts what is on", page.text_content("#toggle-filters").strip() == "Filters (1)", page.text_content("#toggle-filters"))
        chip(page, "game", "Skirmish").click(); chip(page, "faction", "Bright Host").click()
        check("…counting game, faction and stages each once", page.text_content("#toggle-filters").strip() == "Filters (3)" and count_text(page) == "Show 1 unit", (page.text_content("#toggle-filters"), count_text(page)))
        check("focus stays on the chip just tapped (the sheet is redrawn in place)", page.evaluate("document.activeElement.dataset.fk") == "faction:Bright Host")
        chip(page, "faction", "Gloom Legion").click()
        check("a combination with no match says 0 units and the list says so", count_text(page) == "Show 0 units" and "No units match" in page.text_content("#unit-list"), count_text(page))
        page.click("#fs-clear")
        check("Clear all turns every filter off", page.evaluate("[filters.hobby, filters.faction, filters.stages.size, filters.repaint].join()") == ",,0,false" and count_text(page) == "Show 6 units"
              and page.text_content("#toggle-filters").strip() == "Filters" and page.is_disabled("#fs-clear") and shown(page) == 6)
        page.keyboard.press("Escape")

        print("\n--- 3. Shortcuts and the summary line ---")
        page.evaluate("goToUnits({ faction: 'Moss Court' })"); t.quiet(page)
        check("a Nexus shortcut opens Models already filtered, with the count on the button and the summary line", shown(page) == 2 and page.text_content("#toggle-filters").strip() == "Filters (1)"
              and "Moss Court" in page.text_content("#filter-note") and not page.evaluate(OPEN), (shown(page), page.text_content("#filter-note")))
        page.evaluate("goToUnits({ repaint: true })"); t.quiet(page)
        check("the repaint shortcut works too", shown(page) == 1)
        open_sheet(page)
        check("the sheet opened after a shortcut shows the filter that was set", pressed(page, "progress") == ["↻ Repaint"], pressed(page, "progress"))
        page.keyboard.press("Escape"); page.click("#clear-filters")
        check("the Clear link above the list still clears", page.evaluate("filters.repaint") is False and shown(page) == 6)

        print("\n--- 4. Phone sizes, light and dark, two looks ---")
        for w, h, mode, theme in ((390, 844, "dark", "classic"), (360, 640, "light", "classic"), (320, 568, "dark", "bench"), (320, 568, "light", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, units=UNITS, settings={"examplesChecked": True, "theme": theme, "appearance": mode})
            page.click('nav button[data-tab="units"]'); t.quiet(page); open_sheet(page)
            m = page.evaluate("""() => { const sh = document.querySelector('#filters-sheet .fs-sheet').getBoundingClientRect();
                const btns = [...document.querySelectorAll('#filters-sheet button')].map(b => b.getBoundingClientRect());
                return { short: Math.min(...btns.map(b => b.height)), narrow: Math.min(...btns.map(b => b.width)), inside: sh.left >= 0 && sh.right <= innerWidth + 1 && sh.top >= 0 && Math.abs(sh.bottom - innerHeight) < 2,
                         noScroll: document.documentElement.scrollWidth <= innerWidth + 1, footer: document.querySelector('#fs-show').getBoundingClientRect().bottom <= innerHeight + 1 }; }""")
            check(f"{w}x{h} {mode} {theme}: every button 44 px or more, sheet on screen, footer visible, no sideways scroll",
                  m["short"] >= 43.5 and m["narrow"] >= 43.5 and m["inside"] and m["noScroll"] and m["footer"], m)
            page.keyboard.press("Escape")

        print("\n--- 5. 34 factions ---")
        page.set_viewport_size({"width": 320, "height": 568})
        t.load(page, units=MANY, settings={"examplesChecked": True})
        page.click('nav button[data-tab="units"]'); t.quiet(page); open_sheet(page)
        many = page.evaluate("""() => { const b = document.querySelector('#fs-chips-faction'), body = document.querySelector('.fs-body'), s = document.querySelector('.fs-sheet').getBoundingClientRect();
            const kids = [...b.children]; return { n: kids.length, tops: new Set(kids.map(c => Math.round(c.getBoundingClientRect().top))).size > 5, scrolls: body.scrollHeight > body.clientHeight + 20,
                inView: s.top >= 0 && s.bottom <= innerHeight + 1, clipped: kids.filter(c => c.scrollWidth > c.clientWidth + 1).length, side: document.documentElement.scrollWidth <= innerWidth + 1,
                foot: document.querySelector('#fs-show').getBoundingClientRect().bottom <= innerHeight + 1 }; }""")
        check("34 factions wrap onto many lines, the sheet scrolls inside itself and the footer stays in view",
              many["n"] == 35 and many["tops"] and many["scrolls"] and many["inView"] and many["foot"] and many["side"] and many["clipped"] == 0, many)
        page.locator("#fs-chips-stage .chip").last.scroll_into_view_if_needed()
        check("the last section can be scrolled to and tapped", page.locator("#fs-chips-stage .chip").last.is_visible())
        check("no page errors", not [e for e in errors if "woff2" not in e], errors)
        browser.close()
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

main()
