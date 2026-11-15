"""NX1 test for Minifolio (Nexus: the Stages fold lives inside the top card). New behaviour only.
Run with the whole suite, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, app_ready, leave_launch

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

UNITS = [
    {"id": 1, "name": "Alpha", "hobby": "40K", "faction": "Tyranids", "stage": 5, "count": 3},
    {"id": 2, "name": "Beta", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 1},
    {"id": 3, "name": "Gamma", "hobby": "40K", "faction": "Orks", "stage": 3, "count": 2},
]
BOX = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, h: r.height, w: r.width }; }"""
BTN = "#headline-card .card-fold-button"

def load(browser, w, h, units=UNITS, appearance="dark", theme="classic"):
    c = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
    pg = c.new_page()
    t.load(pg, units=units, settings={"tab": "dashboard", "examplesChecked": True, "appearance": appearance, "theme": theme})
    wait_settled(pg)
    return pg, c

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg, c = load(browser, 390, 844)
        pg.on("pageerror", lambda x: errors.append(str(x)))

        check("one card holds the ring and the Stages row",
              pg.evaluate("() => !!document.querySelector('#headline-card #overall-chart svg') && !!document.querySelector('#headline-card #stage-legend') && !!document.querySelector('#headline-card #card-fold-stage-legend-button')"))
        check("there is no separate #stage-card", pg.locator("#stage-card").count() == 0)
        check("the row is under the repaint link, one 44 px button reading Stages",
              pg.inner_text(BTN).strip() == "Stages" and pg.evaluate(BOX, BTN)["h"] >= 44
              and pg.evaluate("() => document.getElementById('repaint-link').compareDocumentPosition(document.getElementById('stage-fold')) & Node.DOCUMENT_POSITION_FOLLOWING") > 0)
        check("it starts closed and says so", pg.get_attribute(BTN, "aria-expanded") == "false" and not pg.is_visible("#stage-legend"))
        check("the chevron is drawn", pg.evaluate("() => { const m = document.querySelector('#headline-card .fold-mark'); const r = m.getBoundingClientRect(); return r.width > 0 && getComputedStyle(m).borderBottomWidth !== '0px'; }"))

        pg.click(BTN); wait_settled(pg)
        names = pg.evaluate("() => STAGES.length")
        check("opening it announces expanded and shows every stage",
              pg.get_attribute(BTN, "aria-expanded") == "true" and pg.locator("#stage-legend li").count() == names and pg.is_visible("#stage-legend"))
        counts = pg.evaluate("() => [...document.querySelectorAll('#stage-legend .num')].map(n => Number(n.textContent))")
        check("each stage shows its count", counts == pg.evaluate("stageCounts(models)"), counts)
        check("the whole card still fits the width and has no sideways scroll",
              pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1") and pg.evaluate(BOX, "#headline-card")["right"] <= 390)

        pg.click("#stage-legend li:nth-child(6) button"); wait_settled(pg)
        check("tapping a stage opens Models filtered to it", pg.is_visible("#view-units") and pg.locator("#unit-list li.unit").count() == 1, pg.locator("#unit-list li.unit").count())

        pg.reload(); app_ready(pg); leave_launch(pg); wait_settled(pg)
        check("reopening the app closes it again", pg.get_attribute(BTN, "aria-expanded") == "false" and not pg.is_visible("#stage-legend"))
        check("nothing about it is saved", pg.evaluate("() => !('stagesOpen' in JSON.parse(localStorage.getItem('shades-of-grey-settings')))"))
        c.close()

        # Classic corner marks: 3 px in and 10 px long, so the row (and its chevron) must start at least 14 px from every card edge
        for state in ("closed", "open"):
            pg, c = load(browser, 360, 640)
            if state == "open": pg.click(BTN); wait_settled(pg)
            m = pg.evaluate("""() => { const card = document.getElementById('headline-card').getBoundingClientRect();
              const b = document.querySelector('#headline-card .card-fold-button').getBoundingClientRect();
              const mk = document.querySelector('#headline-card .fold-mark').getBoundingClientRect();
              return { left: Math.min(b.left, mk.left) - card.left, right: card.right - Math.max(b.right, mk.right), bottom: card.bottom - b.bottom, mark: card.right - mk.right }; }""")
            check(f"Classic, {state}: the row and chevron stay clear of the corner marks", m["left"] >= 14 and m["right"] >= 14 and (state == "open" or m["bottom"] >= 14), m)
            c.close()

        # Looks and sizes: focus ring and chevron visible, no sideways scroll, the row is 44 px
        for w, h, ap, th in ((390, 844, "dark", "classic"), (390, 844, "light", "forge"), (360, 640, "dark", "bench"), (320, 568, "light", "parchment")):
            pg, c = load(browser, w, h, appearance=ap, theme=th)
            pg.focus(BTN)
            f = pg.evaluate("""() => { const b = document.querySelector('#headline-card .card-fold-button'); const s = getComputedStyle(b), m = getComputedStyle(b.querySelector('.fold-mark'));
              return { ring: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0, mark: m.borderBottomColor !== 'rgba(0, 0, 0, 0)' && m.borderBottomColor !== s.backgroundColor,
                       h: b.getBoundingClientRect().height, side: document.documentElement.scrollWidth > innerWidth + 1 }; }""")
            check(f"{w}x{h} {ap} {th}: focus ring and chevron show, 44 px, no sideways scroll", f["ring"] and f["mark"] and f["h"] >= 44 and not f["side"], f)
            c.close()

        # No units, and many stages
        pg, c = load(browser, 360, 640, units=[])
        pg.click(BTN); wait_settled(pg)
        check("with no units it opens and every count is 0", pg.locator("#stage-legend li").count() > 0 and all(x == "0" for x in pg.evaluate("() => [...document.querySelectorAll('#stage-legend .num')].map(n => n.textContent.trim())")))
        c.close()
        many = [{"id": i + 1, "name": f"U{i}", "hobby": "40K", "faction": "Orks", "stage": i % 6, "count": 1} for i in range(8)]
        pg, c = load(browser, 320, 568, units=many)
        pg.click(BTN); wait_settled(pg)
        check("with 8 models open at 320 px: no sideways scroll and the card holds every row",
              pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1") and pg.evaluate("() => document.getElementById('headline-card').contains(document.querySelector('#stage-legend li:last-child'))"))
        c.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
