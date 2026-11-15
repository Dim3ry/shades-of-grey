"""TQ2 test for Minifolio: one render-time check with a big collection.
With 500 units saved, the Models tab opens and shows every card within a generous limit (2 seconds at normal CPU speed;
a slower machine, as measured by the runner, gets the limit scaled up by common.speed_factor). Reduced motion is on, so the whole
list is drawn at once and this is the slowest case. The limit is deliberately loose: it catches a real slowdown (a list that
takes many seconds), not a few hundred milliseconds either way.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from common import speed_factor

N = 500
LIMIT_MS = 2000 * speed_factor()
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def units(n):
    out = []
    for i in range(1, n + 1):
        u = {"id": i, "name": f"Squad {i}", "hobby": "40K", "stage": i % 6, "count": 3,
             "log": [["2026-10-01", i % 6]], "added": "2026-10-01"}
        if i % 3 == 0: u["faction"] = "Iron Wolves"
        if i % 6 == 0: u.update(each=True, stages=[1, 3, 5])
        out.append(u)
    return out

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        t.load(page, units=units(N), settings={"tab": "dashboard", "examplesChecked": True})
        check("500 units are saved and loaded", page.evaluate("models.length") == N, page.evaluate("models.length"))

        # Time from the tap on Models until the last card is in the page.
        ms = page.evaluate("""async (n) => {
            const t0 = performance.now();
            document.querySelector('nav button[data-tab="units"]').click();
            while (document.querySelectorAll('#view-units li.unit').length < n && performance.now() - t0 < 20000)
                await new Promise(r => requestAnimationFrame(r));
            return performance.now() - t0; }""", N)
        cards = page.locator("#view-units li.unit").count()
        print(f"     Models with {N} units: {cards} cards in {ms:.0f} ms (limit {LIMIT_MS:.0f} ms)")
        check("Models draws all 500 cards", cards == N, cards)
        check(f"and does it within {LIMIT_MS / 1000:.0f} seconds", ms < LIMIT_MS, f"{ms:.0f} ms")
        check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
