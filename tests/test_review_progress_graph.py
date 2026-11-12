"""Testing review (T6): the Dashboard's progress graph over several days.

How it works: the page's clock is set to noon (UK time) on 5 Oct 2026 and moved on to 7, 10, 12 and 14 Oct, with a reload
each day. On those days units are added with the Add unit form and moved with the card's Up and Back buttons, and one unit
tracked model by model has each model moved on its own row. Painted (Done) means Tabletop ready or later. Checks:
1. Each day the page's clock really is on that day.
2. On the first day the graph says it starts today (nothing to draw yet); on the second day it has that day and the first.
3. The units' diaries hold one entry per unit per day (several taps on one day keep the last), and the one tracked model
   by model has [date, stage, model] entries.
4. On the last day the table under the graph lists every day something changed, newest first, with the right Added,
   Painted and Done numbers, including a day when Painted went down (a unit moved back).
5. The drawn lines step on those same days to the same numbers, and the numbers at the end of the lines are today's.
6. Touching the graph on one of those days shows that day's numbers.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from launch_helpers import app_ready, leave_launch, quiet, tap_tab
from common import open_unit_card   # MC1: unit cards start closed

PORT = os.environ.get("SOG_PORT", "8000")
BASE = f"http://localhost:{PORT}"
URL = f"{BASE}/index.html"
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def noon(day):
    """Noon in London on that day of October 2026 (British Summer Time, so 11:00 UTC; the clocks change on 25 Oct)."""
    return datetime(2026, 10, day, 11, 0, tzinfo=timezone.utc)

# The default stages, given in the settings (a device with units and no stage list would get the original five).
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted", "Tabletop ready", "Needs touch-ups", "Display ready"]
# Made-up unit, tracked model by model, there from the first day.
HERO = {"id": 1, "name": "Hero band", "hobby": "Test game", "faction": "Gloom Legion", "stage": 4, "count": 2, "each": True,
        "stages": [4, 4], "added": "2026-10-05", "log": [["2026-10-05", 4]]}
# What the table should say on 14 Oct, newest first: date, Added, Painted, Done.
WANT_TABLE = [["Today", "11", "6", "55%"], ["12 Oct 2026", "11", "6", "55%"], ["10 Oct 2026", "11", "7", "64%"],
              ["7 Oct 2026", "8", "5", "63%"], ["5 Oct 2026", "8", "0", "0%"]]
# The same as (days after 5 Oct, Added, Painted) for the drawn lines.
WANT_POINTS = [(0, 8, 0), (2, 8, 5), (5, 11, 7), (7, 11, 6), (9, 11, 6)]

def new_day(page, day):
    page.clock.set_system_time(noon(day))
    page.reload()
    app_ready(page)
    leave_launch(page)
    check(f"{day} Oct: the page's clock is on that day", page.evaluate("todayISO()") == f"2026-10-{day:02d}", page.evaluate("todayISO()"))

def go(page, name):
    """Tap a section in the menu bar. The bar steps aside while a box has the cursor, so leave the box first."""
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_function("() => !document.body.classList.contains('typing')")
    tap_tab(page, name)
    quiet(page)

def add_unit(page, name, count, stage):
    go(page, "units")
    if page.get_attribute("#toggle-add", "aria-expanded") != "true":   # the form stays open after an Add
        page.click("#toggle-add")
    page.fill("#name-input", name)
    page.fill("#count-input", str(count))
    page.fill("#hobby-input", "Test game")
    page.fill("#faction-input", "Gloom Legion")
    page.select_option("#stage-input", str(stage))
    page.click("#add-form button[type=submit]")
    page.wait_for_function("(n) => models.some(m => m.name === n)", arg=name)
    quiet(page)
    return page.evaluate("(n) => models.find(m => m.name === n).id", name)

def unit_id(page, name):
    return page.evaluate("(n) => models.find(m => m.name === n).id", name)

def tap(page, uid, button, times, index=None):
    """Tap a unit's Up or Back button (or one model's, with index) `times` times, waiting for each move to land."""
    for _ in range(times):
        now = page.evaluate("([id, i]) => { const m = models.find(x => x.id === id); return i === null ? m.stage : m.stages[i]; }", [uid, index])
        if index is None:
            open_unit_card(page, f'li.unit[data-id="{uid}"]')   # MC1: the stepper is inside the opened card
            page.click(f'li.unit[data-id="{uid}"] .{button}')
        else:
            page.click(f'button.each-{button}[data-each-row="{uid}:{index}"]')
        page.wait_for_function("([id, i, was]) => { const m = models.find(x => x.id === id); return (i === null ? m.stage : m.stages[i]) !== was; }",
                               arg=[uid, index, now])
        quiet(page)

def open_details(page, uid):
    open_unit_card(page, f'li.unit[data-id="{uid}"]')   # MC1: open the card first; its Details button is inside
    if page.get_attribute(f'li.unit[data-id="{uid}"] .details-toggle', "aria-expanded") != "true":
        page.click(f'li.unit[data-id="{uid}"] .details-toggle')
    page.wait_for_selector('button.each-up[data-each-row="%s:0"]' % uid)
    quiet(page)

def table(page):
    return page.evaluate("() => [...document.querySelectorAll('#history-table tbody tr')].map(r => [...r.cells].map(c => c.textContent))")

def show_dashboard(page):
    go(page, "dashboard")
    page.wait_for_selector("#history-card:not(.hidden)")

# The drawn lines read back: each step's day (from its x) and number (from its y), using the axis numbers for the scale.
READ_LINES = r"""() => {
    const svg = document.querySelector('#history-chart svg');
    const w = Number(svg.getAttribute('width')), h = Number(svg.getAttribute('height'));
    const pad = { left: 38, right: 44, top: 12, bottom: 28 };
    const axis = [...svg.querySelectorAll('text[text-anchor="end"]')].map(t => Number(t.textContent)).filter(n => !isNaN(n));
    const top = Math.max(...axis);
    const paths = [...svg.querySelectorAll('path')].map(p => p.getAttribute('d'));
    const read = (d) => { const nums = d.match(/[MHV]\s*-?[\d.]+(\s+-?[\d.]+)?/g); const pts = []; let x = 0, y = 0;
        for (const part of nums) { const k = part[0], v = part.slice(1).trim().split(/\s+/).map(Number);
            if (k === 'M') { x = v[0]; y = v[1]; pts.push([x, y]); } else if (k === 'H') x = v[0]; else { y = v[0]; pts.push([x, y]); } }
        return { pts: pts.map(([px, py]) => [(px - pad.left) / (w - pad.left - pad.right), (h - pad.bottom - py) / (h - pad.top - pad.bottom) * top]),
                 end: (Number(d.trim().split(/\s+/).pop()) - pad.left) / (w - pad.left - pad.right) }; };
    const ends = [...svg.querySelectorAll('text[font-weight="600"]')].map(t => t.textContent);
    return { top, lines: paths.map(read), ends, label: svg.getAttribute('aria-label'), w, h };
}"""

def main():
    errors, dialogs = [], []
    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce",
                                  timezone_id="Europe/London")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("--- 5 Oct ---")
        page.clock.set_system_time(noon(5))
        page.goto(f"{BASE}/manifest.json")
        page.evaluate("""([hero, stages]) => { localStorage.clear(); localStorage.setItem('mini-tracker-models', JSON.stringify([hero]));
            localStorage.setItem('shades-of-grey-settings', JSON.stringify({ examplesChecked: true, recipeExamplesChecked: true, tab: 'units',
                stages, doneFrom: 5 })); }""", [HERO, STAGES])
        page.goto(URL)
        app_ready(page)
        leave_launch(page)
        check("5 Oct: the page's clock is on that day", page.evaluate("todayISO()") == "2026-10-05", page.evaluate("todayISO()"))
        troop = add_unit(page, "Troop A", 5, 0)
        walker = add_unit(page, "Walker", 1, 4)
        show_dashboard(page)
        check("on the first day the graph says it starts today, with nothing drawn yet",
              page.text_content("#history-note") == "Graph starts today." and page.locator("#history-chart svg").count() == 0,
              [page.text_content("#history-note"), page.locator("#history-chart svg").count()])

        print("\n--- 7 Oct ---")
        new_day(page, 7)
        go(page, "units")
        tap(page, troop, "up-button", 5)   # Unassembled to Tabletop ready: painted
        show_dashboard(page)
        check("on the second day the graph has today and the first day", table(page) == [["Today", "8", "5", "63%"], ["5 Oct 2026", "8", "0", "0%"]],
              table(page))

        print("\n--- 10 Oct ---")
        new_day(page, 10)
        scout = add_unit(page, "Scout", 3, 4)
        tap(page, walker, "up-button", 1)   # Part painted to Tabletop ready: painted
        hero = unit_id(page, "Hero band")
        open_details(page, hero)
        tap(page, hero, "up", 1, index=0)   # just model 1 to Tabletop ready

        print("\n--- 12 Oct ---")
        new_day(page, 12)
        go(page, "units")
        tap(page, troop, "step-back", 1)   # Tabletop ready back to Part painted: no longer painted
        tap(page, scout, "up-button", 1)
        open_details(page, hero)
        tap(page, hero, "up", 2, index=1)   # model 2 to Needs touch-ups

        print("\n--- 14 Oct ---")
        new_day(page, 14)
        logs = page.evaluate("() => Object.fromEntries(models.map(m => [m.name, m.log]))")
        check("several taps on one day keep one diary entry for that day (Troop A)",
              logs.get("Troop A") == [["2026-10-05", 0], ["2026-10-07", 5], ["2026-10-12", 4]], logs.get("Troop A"))
        check("the unit tracked model by model has one [date, stage, model] entry per model moved",
              logs.get("Hero band") == [["2026-10-05", 4], ["2026-10-10", 5, 0], ["2026-10-12", 6, 1]], logs.get("Hero band"))
        show_dashboard(page)
        got = table(page)
        check("the table lists every day something changed, newest first, with the right Added, Painted and Done", got == WANT_TABLE, got)
        lines = page.evaluate(READ_LINES)
        span = 9   # 5 Oct to 14 Oct
        def steps(line):
            return [(round(x * span, 2), round(v, 2)) for x, v in line["pts"]]
        added_line, done_line = (lines["lines"] + [None, None])[:2]
        check("the Added line steps on those days to those numbers",
              added_line and steps(added_line) == [(d, a) for d, a, _ in WANT_POINTS], added_line and steps(added_line))
        check("the Painted line steps on those days to those numbers, going down on 12 Oct",
              done_line and steps(done_line) == [(d, n) for d, _, n in WANT_POINTS], done_line and steps(done_line))
        check("both lines run to today, ending with today's numbers (11 added, 6 painted)",
              added_line and done_line and round(added_line["end"], 3) == 1 and round(done_line["end"], 3) == 1
              and lines["ends"] == ["11", "6"] and "Now 11 added, 6 painted." in (lines["label"] or ""), lines)

        svg = page.locator("#history-chart svg")
        svg.evaluate("e => e.scrollIntoView({ block: 'center' })")   # DB1: the graph now sits lower on the page, so centre it (the nearest-edge scroll left it under the bottom bar)
        page.wait_for_timeout(150)
        box = svg.bounding_box()
        x = 38 + (5 / span) * (lines["w"] - 38 - 44)   # 10 Oct
        page.mouse.move(box["x"] + x, box["y"] + lines["h"] / 2)
        page.wait_for_selector("#history-chart .chart-tip:not(.hidden)")
        tip = page.inner_text("#history-chart .chart-tip")
        check("touching the graph on 10 Oct shows that day's numbers", re.sub(r"\s+", " ", tip).strip() == "10 Oct Added 11 Painted 7 (64%)", tip)
        page.screenshot(path=os.path.join(SHOTS, "review_progress_graph.png"))
        browser.close()

    check("no browser pop-ups", not dialogs, dialogs)
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
