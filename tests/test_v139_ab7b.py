"""AB7b tests for Minifolio (section tabs, from the approved AI-tells item AT-28). New behaviour only:
1. The Painting tabs, the Colour Lab tabs and the Tools tabs are a row of words: one line, 44 px tall, never wrapping, scrolling sideways.
2. One 2 px line sits under the chosen word, and the chosen word is in view.
3. The line slides to a newly chosen word (it is part way there a moment after the tap) and, with reduced motion, does not slide.
4. List / Swatches and Topics / A to Z are still boxed two-way switches.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROW = """(sel) => {
    const row = document.querySelector(sel), r = row.getBoundingClientRect();
    const bs = [...row.querySelectorAll(':scope > button')], line = row.querySelector(':scope > .tab-line');
    const sel_b = row.querySelector(':scope > button[aria-selected="true"]');
    const sb = sel_b ? sel_b.getBoundingClientRect() : null, lb = line.getBoundingClientRect();
    return { n: bs.length, tops: [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top)))].length,
      heights: bs.map(b => Math.round(b.getBoundingClientRect().height)), rowH: Math.round(r.height),
      scrolls: row.scrollWidth > row.clientWidth, overflowX: getComputedStyle(row).overflowX,
      boxed: getComputedStyle(row).borderTopWidth !== '0px' || getComputedStyle(row).backgroundColor !== 'rgba(0, 0, 0, 0)',
      lineH: Math.round(lb.height), lineW: Math.round(lb.width), lineL: Math.round(lb.left), lineBottom: Math.round(lb.bottom),
      selW: sb ? Math.round(sb.width) : -1, selL: sb ? Math.round(sb.left) : -1, selBottom: sb ? Math.round(sb.bottom) : -1,
      selInView: sb ? sb.left >= r.left - 1 && sb.right <= r.right + 1 : false,
      roles: bs.every(b => b.getAttribute('role') === 'tab'), selected: bs.filter(b => b.getAttribute('aria-selected') === 'true').length,
      pageScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth };
}"""

def row_checks(page, label, sel, width):
    d = page.evaluate(ROW, sel)
    tag = f"{label} at {width}"
    check(f"{tag}: one line, 44 px tall, never wraps", d["tops"] == 1 and all(h >= 44 for h in d["heights"]) and d["rowH"] <= 46, d)
    check(f"{tag}: no box round the row", not d["boxed"], d)
    check(f"{tag}: scrolls sideways when it must", d["overflowX"] in ("auto", "scroll") and (width > 330 or d["scrolls"]), d)
    check(f"{tag}: one chosen word, the 2 px line sits under it", d["selected"] == 1 and d["lineH"] == 2 and abs(d["lineW"] - d["selW"]) <= 1
          and abs(d["lineL"] - d["selL"]) <= 1 and abs(d["lineBottom"] - d["selBottom"]) <= 1, d)
    check(f"{tag}: the chosen word is in view, the page does not scroll sideways", d["selInView"] and not d["pageScroll"], d)
    check(f"{tag}: every tab keeps its tab role", d["roles"], d)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in ((390, 844), (320, 568)):
            ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, units=[])
            print(f"\n--- rows at {width} px ---")
            page.click('nav button[data-tab="recipes"]'); quiet(page)
            page.click('#recipe-seg button[data-view="palette"]'); page.wait_for_timeout(400)
            row_checks(page, "Painting (Your Palette)", "#recipe-seg", width)
            page.click('#recipe-seg button[data-view="colourlab"]'); page.wait_for_timeout(400)
            row_checks(page, "Colour Lab", "#lab-seg", width)
            page.click('nav button[data-tab="guides"]'); quiet(page)
            page.wait_for_timeout(300)
            page.click('#more-seg button[data-page="updates"]'); page.wait_for_timeout(400)
            row_checks(page, "Tools (Updates)", "#more-seg", width)
            if width == 390:
                print("\n--- the line slides ---")
                page.click('#more-seg button[data-page="about"]')
                page.wait_for_timeout(500)
                before = page.evaluate("() => getComputedStyle(document.querySelector('#more-seg .tab-line')).transform")
                page.click('#more-seg button[data-page="settings"]')
                page.wait_for_timeout(90)
                mid = page.evaluate("() => getComputedStyle(document.querySelector('#more-seg .tab-line')).transform")
                page.wait_for_timeout(600)
                after = page.evaluate("() => getComputedStyle(document.querySelector('#more-seg .tab-line')).transform")
                dur = page.evaluate("() => getComputedStyle(document.querySelector('#more-seg .tab-line')).transitionDuration")
                check("a moment after the tap the line is part way between the two words", len({before, mid, after}) == 3, (before, mid, after))
                check("the slide takes the fast-move time, not zero", dur.split(",")[0].strip() not in ("0s", ""), dur)
                row_checks(page, "Tools (Settings, after the slide)", "#more-seg", width)
            ctx.close()

        print("\n--- reduced motion: no slide ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        t.load(page, units=[])
        page.click('nav button[data-tab="recipes"]'); quiet(page)
        page.click('#recipe-seg button[data-view="palette"]'); page.wait_for_timeout(300)
        page.click('#recipe-seg button[data-view="schemes"]'); page.wait_for_timeout(60)
        d = page.evaluate(ROW, "#recipe-seg")
        dur = page.evaluate("() => getComputedStyle(document.querySelector('#recipe-seg .tab-line')).transitionDuration")
        check("with reduced motion the line is already under the new word", abs(d["lineL"] - d["selL"]) <= 1, d)
        check("with reduced motion the line has no transition", all(x.strip() == "0s" for x in dur.split(",")), dur)
        ctx.close()

        print("\n--- two-way choices stay boxed ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        t.load(page, units=[])
        page.click('nav button[data-tab="recipes"]'); quiet(page)
        page.click('#recipe-seg button[data-view="palette"]'); page.wait_for_timeout(300)
        view = page.evaluate("() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === 'Swatches'); const s = b && b.parentElement;"
                             " return s ? { boxedOrGrid: getComputedStyle(s).display, tabRow: s.classList.contains('tab-row'), bg: getComputedStyle(b).backgroundColor } : null; }")
        check("List / Swatches is not turned into a tab row", view is not None and not view["tabRow"], view)
        page.click('nav button[data-tab="guides"]'); quiet(page)
        page.wait_for_timeout(300)
        page.click('#more-seg button[data-page="guides"]'); page.wait_for_timeout(500)
        g = page.evaluate("() => { const s = document.querySelector('.guides-order'); if (!s) return null; const cs = getComputedStyle(s);"
                          " return { tabRow: s.classList.contains('tab-row'), border: cs.borderTopWidth, display: cs.display, line: !!s.querySelector('.tab-line') }; }")
        check("Topics / A to Z is still a boxed two-way switch", g is not None and not g["tabRow"] and g["border"] != "0px" and g["display"] == "grid" and not g["line"], g)
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
