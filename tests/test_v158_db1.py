"""DB1 test for Minifolio (Nexus, one top card, folding Stages row, Done wording, Progress timeline). New behaviour only.
Run with the whole suite, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, app_ready, leave_launch

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

UNITS = [
    {"id": 1, "name": "Alpha", "hobby": "40K", "faction": "Tyranids", "stage": 5, "count": 3},
    {"id": 2, "name": "Beta", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 1},
    {"id": 3, "name": "Gamma", "hobby": "40K", "faction": "Orks", "stage": 3, "count": 2},
]
RING = "() => [...document.querySelectorAll('#overall-chart svg text')].map(x => x.textContent)"
BOX = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect();
  return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, h: r.height, w: r.width }; }"""

def load(browser, w, h, settings=None, units=UNITS, appearance="dark", theme="classic"):
    c = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
    pg = c.new_page()
    s = {"tab": "dashboard", "examplesChecked": True, "appearance": appearance, "theme": theme}
    s.update(settings or {})
    t.load(pg, units=units, settings=s)
    wait_settled(pg)
    return pg, c

def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg, c = load(browser, 390, 844)
        pg.on("pageerror", lambda x: errors.append(str(x)))

        # 1. One top card
        pct = pg.evaluate("() => Math.round(doneCount(models) / modelCount(models) * 100) + '%'")
        check("the ring reads the percentage over Done", pg.evaluate(RING) == [pct, "Done"], pg.evaluate(RING))
        check("the ring is inside the top card and no 'Where everything is' text is left",
              pg.evaluate("() => !!document.querySelector('#headline-card #overall-chart svg')") and "Where everything is" not in pg.inner_text("#view-dashboard"))
        same = pg.evaluate("""() => { const [a, b] = [...document.querySelectorAll('#overall-chart svg text')];
          const A = getComputedStyle(a), B = getComputedStyle(b);
          return [A.fontSize === B.fontSize, A.fontWeight === B.fontWeight, A.fontFamily === B.fontFamily, A.fill === B.fill]; }""")
        check("both ring lines have the same size, weight, font and colour", all(same), same)
        check("the capital D is used", "Done" in pg.evaluate(RING) and "done" not in pg.evaluate(RING))
        gone = pg.evaluate("() => ['done-percent', 'done-summary', 'done-meaning'].filter(id => document.getElementById(id))")
        check("the big percentage, the summary line and the Done means line are gone", gone == [] and "models done ·" not in pg.inner_text("#headline-card") and "Done means" not in pg.inner_text("#headline-card"), gone)
        ring, card, tiles = pg.evaluate(BOX, "#overall-chart svg"), pg.evaluate(BOX, "#headline-card"), pg.evaluate(BOX, ".groups")
        check("the ring is centred at the top of the card", abs((ring["left"] + ring["right"]) / 2 - (card["left"] + card["right"]) / 2) < 2 and ring["top"] - card["top"] < 40, (ring, card))
        check("the two tiles sit directly under the ring", 0 <= tiles["top"] - ring["bottom"] <= 24 and pg.locator(".groups .group-button").count() == 2, (ring, tiles))
        # NX1: the top card now also holds the Stages fold, whose heading is the Stages button; only the ring has no heading of its own.
        check("no heading on the ring", pg.locator("#headline-card h3").count() == 0 and pg.locator("#headline-card h2").count() == 1)

        # 2. The Stages row. NX1: it is inside the top card now (no #stage-card), starts shut every time the app opens and is no longer saved;
        # the fuller check of the row is in test_v167_nx1.py.
        btn = "#headline-card .card-fold-button"
        check("it is one row, 44 px or more, labelled Stages, and starts shut",
              pg.inner_text(btn).strip() == "Stages" and pg.evaluate(BOX, btn)["h"] >= 44 and pg.get_attribute(btn, "aria-expanded") == "false" and not pg.is_visible("#stage-legend"),
              (pg.inner_text(btn), pg.get_attribute(btn, "aria-expanded")))
        y0 = pg.evaluate("() => window.scrollY")
        pg.click(btn); wait_settled(pg)
        check("tapping opens it: aria-expanded, rows and counts are shown, the page does not jump",
              pg.get_attribute(btn, "aria-expanded") == "true" and pg.locator("#stage-legend li").count() == pg.evaluate("STAGES.length")
              and pg.is_visible("#stage-legend") and pg.evaluate("() => window.scrollY") == y0)
        counts = pg.evaluate("() => [...document.querySelectorAll('#stage-legend .num')].map(n => Number(n.textContent))")
        check("the counts are the models at each stage", counts == pg.evaluate("stageCounts(models)"), counts)
        pg.click("#stage-legend li:nth-child(6) button"); wait_settled(pg)
        check("a stage row opens Models filtered to that stage", pg.is_visible("#view-units") and pg.locator("#unit-list li.unit").count() == 1, pg.locator("#unit-list li.unit").count())
        c.close()

        # 3. Armies doughnuts say Done
        pg, c = load(browser, 390, 844, settings={"factionView": "doughnuts"})
        texts = pg.evaluate("() => [...document.querySelectorAll('#faction-grid .faction-button')].map(b => [...b.querySelectorAll('svg text')].map(x => x.textContent))")
        check("each army doughnut reads its percentage over Done", len(texts) == 2 and all(len(x) == 2 and x[1] == "Done" and x[0].endswith("%") for x in texts), texts)
        c.close()

        # 4. Empty collection
        pg, c = load(browser, 390, 844, units=[])
        check("with no units the ring reads 0% over Done and both tiles read 0",
              pg.evaluate(RING) == ["0%", "Done"] and pg.inner_text("#todo-button").startswith("0") and pg.inner_text("#done-button").startswith("0"), pg.evaluate(RING))
        c.close()

        # 5. Names: Progress timeline and Nexus
        pg, c = load(browser, 390, 844)
        check("the graph card is called Progress timeline", pg.inner_text("#history-card h2").strip() == "Progress timeline")
        leftovers = [f for f in ("app.js", "index.html", "guides-data.js", "guides-groups.js", "mentor-data.js", "mentor-tips.js", "mentor-engine.js") if "Added and painted" in read(f)]
        check("no 'Added and painted' is left in the app or the guides", leftovers == [], leftovers)
        labels = pg.evaluate("""() => [...document.querySelectorAll('[data-tab="dashboard"]')].map(b => (b.getAttribute('aria-label') || b.textContent).trim())""")
        check("every menu button for the page says Nexus", labels and all(l == "Nexus" for l in labels), labels)
        check("Help says Nexus and no longer says Dashboard", "Nexus" in pg.evaluate("() => document.getElementById('view-help').textContent") and "Dashboard" not in pg.evaluate("() => document.getElementById('view-help').textContent"))
        ids = pg.evaluate("() => [!!document.getElementById('view-dashboard'), !!document.querySelector('nav button[data-tab=dashboard]'), settings.tab]")
        check("the internal ids and the saved tab name stay 'dashboard'", ids == [True, True, "dashboard"], ids)
        c.close()
        pg, c = load(browser, 390, 844, settings={"tab": "dashboard"})
        check("a saved tab of 'dashboard' opens Nexus", pg.is_visible("#view-dashboard") and pg.evaluate("settings.tab") == "dashboard")
        c.close()

        # 6. Phones, dark and light, Classic and another look
        for w, h, appearance, theme in ((390, 844, "dark", "classic"), (390, 844, "light", "forge"), (360, 640, "light", "classic"), (360, 640, "dark", "bench"),
                                        (320, 568, "dark", "classic"), (320, 568, "light", "forge")):
            pg, c = load(browser, w, h, appearance=appearance, theme=theme)
            tag = f"{w}x{h} {appearance} {theme}"
            fit = pg.evaluate("""() => ({ side: document.documentElement.scrollWidth > innerWidth + 1,
              labels: [...document.querySelectorAll('nav.tabs button[data-tab]')].every(b => b.scrollWidth <= b.clientWidth + 1),
              ringText: (() => { const tx = document.querySelector('#overall-chart svg text'); const f = getComputedStyle(tx).fill; return f; })(),
              stageH: document.querySelector('#headline-card .card-fold-button').getBoundingClientRect().height })""")
            check(f"{tag}: no sideways scroll, the Nexus label fits its button, the Stages row is 44 px or more",
                  not fit["side"] and fit["labels"] and fit["stageH"] >= 44, fit)
            check(f"{tag}: the ring text has a colour", fit["ringText"] not in ("none", "rgba(0, 0, 0, 0)"), fit["ringText"])
            if (w, h) == (390, 844) and appearance == "dark":
                stage = pg.evaluate(BOX, "#headline-card")
                check("390x844: the ring, both tiles and the Stages row show without scrolling", stage["bottom"] <= 844, stage)
            c.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
