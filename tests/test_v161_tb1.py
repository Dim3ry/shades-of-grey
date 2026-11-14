"""TB1 tests for Minifolio (sub-tab rows that scroll sideways show that more tabs are there). New behaviour only:
the fade at each hidden edge, the "More tabs" arrow, the active tab in view, rows that fit show nothing.
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

STATE = """(sel) => {
    const seg = document.querySelector(sel), wrap = seg.parentElement, more = wrap.querySelector(':scope > .tab-more');
    const r = seg.getBoundingClientRect(), bs = [...seg.querySelectorAll(':scope > button')];
    const full = (b) => { const x = b.getBoundingClientRect(); return x.left >= r.left - 1 && x.right <= r.right + 1; };
    const op = (pseudo) => parseFloat(getComputedStyle(wrap, pseudo).opacity);
    const mb = more && !more.hidden && more.getBoundingClientRect().width ? more.getBoundingClientRect() : null;
    return { wrapOk: wrap.classList.contains('tab-wrap'), fadeL: op('::before'), fadeR: op('::after'),
      fadeW: parseFloat(getComputedStyle(wrap, '::after').width),
      arrow: !!mb, arrowW: mb ? mb.width : 0, arrowH: mb ? mb.height : 0, arrowName: more ? more.getAttribute('aria-label') : null,
      arrowMidY: mb ? (mb.top + mb.height / 2) : 0, rowMidY: r.top + r.height / 2,
      last: full(bs[bs.length - 1]), cutOff: bs.some(b => b.getBoundingClientRect().right > r.right + 1),
      sel: bs.filter(b => b.getAttribute('aria-selected') === 'true').map(b => ({ t: b.textContent.trim(), full: full(b) })),
      pageScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth };
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=[])
        print("\n--- 390 px: the Painting row ---")
        page.click('nav button[data-tab="recipes"]'); quiet(page)
        page.click('#recipe-seg button[data-view="recipes"]'); page.wait_for_timeout(500)
        d = page.evaluate(STATE, "#recipe-seg")
        check("the row sits in the shared wrapper", d["wrapOk"], d)
        check("the arrow shows, named More tabs, at least 44 px, centred on the tab words",
              d["arrow"] and d["arrowName"] == "More tabs" and d["arrowW"] >= 44 and d["arrowH"] >= 44 and abs(d["arrowMidY"] - d["rowMidY"]) <= 2, d)
        check("the right edge is faded about 70 px, the left is not", d["fadeR"] > 0.9 and abs(d["fadeW"] - 70) <= 1 and d["fadeL"] < 0.1, d)
        check("Shopping is not fully in view and a tab is cut off at the edge", not d["last"] and d["cutOff"], d)
        check("the chosen tab is fully in view", d["sel"] and d["sel"][0]["full"], d)

        print("\n--- the arrow ---")
        page.click('#recipe-seg ~ .tab-more, .tab-wrap:has(#recipe-seg) > .tab-more'); page.wait_for_timeout(900)
        d = page.evaluate(STATE, "#recipe-seg")
        check("pressing the arrow brings Shopping fully into view", d["last"], d)
        check("the arrow and the right fade are gone at the end", not d["arrow"] and d["fadeR"] < 0.1, d)
        check("the left edge now fades", d["fadeL"] > 0.9, d)
        check("the page does not scroll sideways", not d["pageScroll"], d)

        print("\n--- keyboard ---")
        page.evaluate("() => { document.getElementById('recipe-seg').scrollLeft = 0; }"); page.wait_for_timeout(300)
        page.focus('#recipe-seg button[data-view="colourlab"]')
        page.keyboard.press("Tab"); page.keyboard.press("Tab"); page.wait_for_timeout(400)
        focused = page.evaluate("() => { const a = document.activeElement, s = document.getElementById('recipe-seg'), r = s.getBoundingClientRect(), x = a.getBoundingClientRect();"
                                " return { text: a.textContent.trim(), inView: x.left >= r.left - 1 && x.right <= r.right + 1 }; }")
        check("a tab that gets focus is scrolled into view", focused["text"] == "Shopping" and focused["inView"], focused)
        page.evaluate("() => { document.getElementById('recipe-seg').scrollLeft = 0; }"); page.wait_for_timeout(300)
        page.focus('#recipe-seg button[data-view="shopping"]')
        page.keyboard.press("Tab"); page.wait_for_timeout(100)
        check("Tab from the last tab never lands on a hidden arrow",
              page.evaluate("() => document.activeElement.className !== 'tab-more' || !document.activeElement.hidden"))

        print("\n--- arriving from elsewhere ---")
        page.click('nav button[data-tab="guides"]'); quiet(page); page.wait_for_timeout(300)
        page.evaluate("() => { document.getElementById('recipe-seg').scrollLeft = 0; }")
        page.evaluate("() => { const b = document.querySelector('#recipe-seg button[data-view=\"shopping\"]'); document.querySelector('nav button[data-tab=\"recipes\"]').click(); }")
        page.wait_for_timeout(400)
        page.evaluate("() => document.querySelector('#recipe-seg button[data-view=\"shopping\"]').click()")
        page.wait_for_timeout(500)
        d = page.evaluate(STATE, "#recipe-seg")
        check("opening Shopping shows it chosen and fully in view", d["sel"] and d["sel"][0]["t"] == "Shopping" and d["sel"][0]["full"], d)
        page.evaluate("() => { document.getElementById('recipe-seg').scrollLeft = 0; }"); page.wait_for_timeout(200)
        page.evaluate("() => { const b = document.getElementById('basket-button'); if (b) b.click(); }")
        page.wait_for_timeout(700)
        d = page.evaluate(STATE, "#recipe-seg")
        check("the basket button opens Shopping chosen and in view", d["sel"] and d["sel"][0]["t"] == "Shopping" and d["sel"][0]["full"], d)
        ctx.close()

        print("\n--- a row that fits shows nothing new ---")
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
        page = ctx.new_page()
        t.load(page, units=[])
        page.click('nav button[data-tab="recipes"]'); quiet(page); page.wait_for_timeout(400)
        d = page.evaluate(STATE, "#recipe-seg")
        check("at 1280 px there is no arrow and no fade", d["wrapOk"] and not d["arrow"] and d["fadeL"] < 0.1 and d["fadeR"] < 0.1 and d["last"], d)
        ctx.close()

        print("\n--- 320 px and the Tools row ---")
        ctx = browser.new_context(viewport={"width": 320, "height": 568}, service_workers="block")
        page = ctx.new_page()
        t.load(page, units=[])
        page.click('nav button[data-tab="guides"]'); quiet(page); page.wait_for_timeout(300)
        page.click('#more-seg button[data-page="settings"]'); page.wait_for_timeout(500)
        d = page.evaluate(STATE, "#more-seg")
        check("the Tools row also gets the arrow and fade, with the chosen tab in view",
              d["arrow"] and d["fadeR"] > 0.9 and d["sel"][0]["full"] and not d["pageScroll"], d)
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
