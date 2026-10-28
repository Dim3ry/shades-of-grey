"""v85 tests for Minifolio (chunk M2: model rows with a stepper, Detailed and Simple view).

New behaviour only:
1. Details of a unit tracked model by model: Move all models to stage, Track as one batch, the rows, then (Paints, ...) Edit details.
2. Detailed row: name, date line (only when the diary knows), back, stage name in words, thin bar, up. Back off at the first stage, up at the last.
3. Back / up move one model with Undo that restores stages and diary exactly; focus stays on the tapped button.
4. Move all models to stage and Undo. Track as one batch: asks when the stages differ, switches at once when they match, both with Undo.
5. Simple view: no date line, no bar. One saved choice (Detailed by default) for every card; the switch shows only when a unit is tracked model by model.
6. More than 8 models: rows grouped by stage, furthest-behind group open, the group a model lands in opens and the one it left stays open. 100 models open quickly.
7. 390 and 360 px, dark and light, and 900 / 1280 / 1920 px (side pane): no sideways scroll, tap targets 44 px or more, long stage names fit.
8. The new CSS has no hard-coded colours.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys, time
from playwright.sync_api import sync_playwright
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def spread(n):
    """n stages across 0..7, skipping 2, 4 and 6, in a scrambled order."""
    pool = [0, 0, 0, 1, 1, 1, 1, 3, 3, 5, 5, 7]
    base = [pool[i % len(pool)] for i in range(n)]
    return [base[(i * 7) % n] for i in range(n)]

def unit(uid, name, stages, log=None, each=True):
    u = {"id": uid, "name": name, "hobby": "40K", "stage": min(stages), "count": len(stages), "added": "2026-01-01",
         "log": log or [["2026-01-01", min(stages)]]}
    if each:
        u["each"] = True
        u["stages"] = stages
    else:
        u["stage"] = stages[0]
    return u

def card(page, uid):
    return page.locator(f"li.unit[data-id='{uid}']")

def saved(page, uid):
    return page.evaluate("(i) => { const m = models.find(x => x.id === i); return { each: m.each, stage: m.stage, stages: m.stages, log: m.log }; }", uid)

def undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(250)

def open_details(page, uid):
    page.click(f"li.unit[data-id='{uid}'] .details-toggle")
    page.wait_for_timeout(250)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        load(page)
        STAGES = page.evaluate("STAGES")
        year = page.evaluate("new Date().getFullYear()")
        today = page.evaluate("todayISO()")
        jan2 = f"{year}-01-02"
        TOP = len(STAGES) - 1

        SQUAD = unit(1, "Squad", [2, 2, 3, 3, 0, TOP], log=[[jan2, 2], [f"{year}-01-03", 0, 4], [today, 3, 2]])
        BATCH = unit(2, "Batch", [2, 2, 2, 2], each=False)
        BIG = unit(3, "Big unit", spread(30))
        HUGE = unit(4, "Huge unit", [i % len(STAGES) for i in range(100)])
        SAME = unit(5, "Same stage", [1, 1, 1])
        UNITS = [SQUAD, BATCH, BIG, HUGE, SAME]

        def start(units=None, **kw):
            load(page, units=units or UNITS, **kw)
            page.click('nav button[data-tab="units"]')
            page.wait_for_timeout(250)

        print("\n--- 1. The switch and the panel ---")
        start(units=[BATCH])
        check("the Detailed / Simple switch is hidden when no unit is tracked model by model", not page.locator("#model-rows-switch").is_visible())
        start()
        sw = page.locator("#model-rows-switch")
        check("…and shown when one is, Detailed pressed by default",
              sw.is_visible() and sw.locator("[data-rows=detailed]").get_attribute("aria-pressed") == "true"
              and sw.locator("[data-rows=simple]").get_attribute("aria-pressed") == "false")
        open_details(page, 1)
        order = page.evaluate("""() => [...document.querySelectorAll('li.unit[data-id="1"] .panel > *')].map(e =>
            e.querySelector && e.querySelector('select.jump-stage') ? 'move' : e.classList.contains('track-each') ? 'track'
            : e.classList.contains('each-list') ? 'rows' : e.classList.contains('edit-details') ? 'edit' : '').filter(Boolean)""")
        check("order: Move all models, Track as one batch, the rows, then Edit details", order == ["move", "track", "rows", "edit"], order)
        check("Move all models to stage is the only stage menu", card(page, 1).locator("select").evaluate_all(
              "els => els.filter(e => e.classList.contains('stage-pick')).length") == 1
              and "Move all models to stage" in card(page, 1).locator(".panel > label").first.inner_text())
        sizes = page.evaluate("""() => ['select.jump-stage', 'button.track-each'].map(s => { const r = document.querySelector('li.unit[data-id="1"] ' + s).getBoundingClientRect();
            return [Math.round(r.width), Math.round(r.height)]; })""")
        panel_w = page.evaluate("document.querySelector('li.unit[data-id=\"1\"] .panel').getBoundingClientRect().width")
        check("both are full width and 48 px tall", all(h >= 48 and w >= panel_w - 40 for w, h in sizes), (sizes, panel_w))

        print("\n--- 2. A Detailed row ---")
        rows = card(page, 1).locator(".each-list li")
        since = [rows.nth(i).locator(".each-since").inner_text() if rows.nth(i).locator(".each-since").count() else None for i in range(6)]
        check("date line: from the diary; none where the diary cannot say",
              since == ["Since 2 Jan", "Since 2 Jan", "Today", None, "Since 3 Jan", None], since)
        r2 = rows.nth(2)
        check("the row has the name, back, the stage in words, a bar of one segment per stage and up",
              r2.locator(".each-label").inner_text() == "Model 3" and r2.locator(".each-stage-name").inner_text() == STAGES[3]
              and r2.locator(".pip").count() == len(STAGES) and r2.locator(".pip.filled").count() == 4
              and r2.locator(".each-back").count() == 1 and r2.locator(".each-up").count() == 1)
        check("labels name the model and the stage",
              r2.locator(".each-back").get_attribute("aria-label") == f"Model 3, back to {STAGES[2]}"
              and r2.locator(".each-up").get_attribute("aria-label") == f"Model 3, up to {STAGES[4]}")
        check("back is off at the first stage, up at the last",
              rows.nth(4).locator(".each-back").is_disabled() and not rows.nth(4).locator(".each-up").is_disabled()
              and rows.nth(5).locator(".each-up").is_disabled() and not rows.nth(5).locator(".each-back").is_disabled())
        colours = page.evaluate("""() => { const r = document.querySelectorAll('li.unit[data-id="1"] .each-list li')[2];
            return [getComputedStyle(r.querySelector('.each-stage-name')).color, getComputedStyle(r.querySelector('.each-up')).backgroundColor]; }""")
        check("the stage name is in the stage colour (the same as the up button)", colours[0] == colours[1], colours)

        print("\n--- 3. One model, with Undo ---")
        before = saved(page, 1)
        rows.nth(2).locator(".each-up").click()
        page.wait_for_timeout(250)
        after = saved(page, 1)
        check("up moves just that model one stage and the diary notes it", after["stages"] == [2, 2, 4, 3, 0, TOP] and after["log"][-1] == [today, 4, 2], after)
        focus = page.evaluate("[document.activeElement.dataset.eachRow, document.activeElement.dataset.dir]")
        check("keyboard focus stays on the tapped button", focus == ["1:2", "up"], focus)
        undo(page)
        check("Undo puts stages and diary back exactly", saved(page, 1) == before, saved(page, 1))
        card(page, 1).locator(".each-list li").nth(0).locator(".each-back").click()
        page.wait_for_timeout(250)
        check("back moves one model back one stage", saved(page, 1)["stages"][0] == 1)
        undo(page)

        print("\n--- 4. Move all, and Track as one batch ---")
        page.select_option("li.unit[data-id='1'] select.jump-stage", "5")
        page.wait_for_timeout(250)
        check("Move all models to stage moves every model", saved(page, 1)["stages"] == [5] * 6, saved(page, 1))
        undo(page)
        check("Undo puts every model and the diary back", saved(page, 1) == before, saved(page, 1))
        card(page, 1).locator("button.track-each").click()
        page.wait_for_timeout(250)
        msg = page.inner_text("#dialog-box") if page.locator("#dialog-box").count() else page.inner_text("body")
        check("different stages: it asks first, naming the furthest-behind stage", STAGES[0] in msg and "furthest-behind" in msg, msg[:120])
        page.click("#dialog-yes")
        page.wait_for_timeout(250)
        s = saved(page, 1)
        check("Yes switches to one batch at that stage", not s["each"] and s["stage"] == 0 and s["stages"] is None, s)
        undo(page)
        check("Undo brings back each model's stage and the diary exactly", saved(page, 1) == before, saved(page, 1))
        open_details(page, 5)
        card(page, 5).locator("button.track-each").click()
        page.wait_for_timeout(250)
        check("all at the same stage: it switches at once, no question",
              not page.locator("#dialog-yes").is_visible() and not saved(page, 5)["each"] and saved(page, 5)["stage"] == 1)
        undo(page)
        check("…with an Undo", saved(page, 5)["each"] and saved(page, 5)["stages"] == [1, 1, 1])

        print("\n--- 5. Simple view ---")
        page.click("#model-rows-switch [data-rows=simple]")
        page.wait_for_timeout(250)
        simple = page.evaluate("""() => { const rows = [...document.querySelectorAll('li.unit .each-list li')];
            return { n: rows.length, since: rows.filter(r => r.querySelector('.each-since')).length, pips: rows.filter(r => r.querySelector('.pips')).length,
                     names: rows.filter(r => r.querySelector('.each-stage-name')).length, h: Math.max(...rows.map(r => r.getBoundingClientRect().height)) }; }""")
        check("no date line and no bar, but the stage name and buttons stay; rows are shorter",
              simple["n"] >= 9 and simple["since"] == 0 and simple["pips"] == 0 and simple["names"] == simple["n"] and simple["h"] <= 58, simple)
        check("the choice is saved as a setting", page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-settings')).modelRows") == "simple")
        check("it applies to every card at once", page.locator("li.unit .each-list li .each-since, li.unit .each-list li .pips").count() == 0
              and page.locator("li.unit[data-id='5'] .each-list li").count() == 3)
        check("it is a view-only setting", page.evaluate("VIEW_ONLY_SETTINGS.includes('modelRows')"))
        page.reload()
        page.wait_for_timeout(500)
        leave_launch(page)   # U4b: tap through the start page
        page.click('nav button[data-tab="units"]')
        check("it survives a reload", page.locator("#model-rows-switch [data-rows=simple]").get_attribute("aria-pressed") == "true")
        page.click("#model-rows-switch [data-rows=detailed]")
        open_details(page, 1)   # open units are not remembered over a reload
        check("Detailed brings the date lines back", page.locator("li.unit[data-id='1'] .each-since").count() == 4)

        print("\n--- 6. Long units ---")
        check("8 models or fewer: a flat list, no group headers", page.locator("li.unit[data-id='1'] .each-group-head").count() == 0)
        open_details(page, 3)
        heads = card(page, 3).locator(".each-group-head")
        names = [heads.nth(i).locator(".each-group-stage").inner_text() for i in range(heads.count())]
        want = [STAGES[k] for k in sorted(set(saved(page, 3)["stages"]))]
        check("30 models: one header per stage in use, in stage order, empty stages left out", names == want, names)
        exp = [heads.nth(i).get_attribute("aria-expanded") for i in range(heads.count())]
        check("the furthest-behind group is open, the rest are collapsed", exp[0] == "true" and set(exp[1:]) == {"false"}, exp)
        check("a header says how many models", re.fullmatch(r"\d+ models?", heads.nth(0).locator(".each-group-count").inner_text()) is not None)
        n0 = int(heads.nth(0).locator(".each-group-count").inner_text().split()[0])
        check("only the open group's rows are drawn", card(page, 3).locator(".each-list li").count() == n0)
        before3 = saved(page, 3)
        card(page, 3).locator(".each-list li").first.locator(".each-up").click()
        page.wait_for_timeout(250)
        heads = card(page, 3).locator(".each-group-head")
        exp = {heads.nth(i).locator(".each-group-stage").inner_text(): heads.nth(i).get_attribute("aria-expanded") for i in range(heads.count())}
        check("a moved model's new group opens and the group it left stays open", exp[STAGES[0]] == "true" and exp[STAGES[1]] == "true", exp)
        undo(page)
        check("Undo puts it back exactly", saved(page, 3) == before3)
        heads = card(page, 3).locator(".each-group-head")
        heads.nth(2).click()
        page.wait_for_timeout(250)
        check("tapping a header opens it, with the focus kept there",
              card(page, 3).locator(".each-group-head").nth(2).get_attribute("aria-expanded") == "true"
              and page.evaluate("document.activeElement.classList.contains('each-group-head')"))
        page.evaluate("openIds.add(4)")
        ms = page.evaluate("() => { const t0 = performance.now(); render(); return performance.now() - t0; }")
        open_rows = card(page, 4).locator(".each-list li").count()
        print(f"     100 models: redraw took {ms:.0f} ms, {open_rows} rows drawn")
        check("a unit of 100 models draws quickly and only draws the open group", ms < 1500 and 0 < open_rows <= 13, (ms, open_rows))

        print("\n--- 7. Looks ---")
        page.evaluate("openIds.clear()")
        for scheme in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 900})
                start(units=[unit(1, "Squad", [0, TOP, 1, 3], log=[[jan2, 0]]), BIG], settings={"appearance": scheme, "modelRows": "detailed"})
                open_details(page, 1)
                open_details(page, 3)
                geo = page.evaluate("""() => {
                    const R = e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
                    const rows = [...document.querySelectorAll('li.unit .each-list li')], ends = [STAGES[0], STAGES[STAGES.length - 1]];
                    return { btn: rows.flatMap(r => [...r.querySelectorAll('button')].map(R)),
                             fit: rows.every(r => { const n = r.querySelector('.each-stage-name'), s = r.querySelector('.each-step');
                                 return n.scrollWidth <= n.clientWidth + 1 && (!ends.includes(n.textContent) || n.getBoundingClientRect().height < 20) && s.getBoundingClientRect().right <= r.getBoundingClientRect().right
                                     && r.scrollWidth <= r.clientWidth + 1; }),
                             heads: [...document.querySelectorAll('.each-group-head')].map(R),
                             sw: [...document.querySelectorAll('#model-rows-switch button')].map(R) }; }""")
                ok = (no_sideways(page) and len(geo["btn"]) >= 8 and all(a >= 44 and b >= 44 for a, b in geo["btn"] + geo["sw"])
                      and all(b >= 44 for a, b in geo["heads"]) and geo["heads"])
                check(f"{width} px {scheme}: no sideways scroll, tap targets 44 px or more, Unassembled and {STAGES[TOP]} fit", ok and geo["fit"], geo)
        for width in (900, 1280, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            start(units=[unit(1, "Squad", [0, TOP, 1, 3], log=[[jan2, 0]])])
            card(page, 1).locator(".details-toggle").click()
            page.wait_for_timeout(300)
            fit = page.evaluate("""() => { const side = document.getElementById('unit-side');
                return side.offsetParent !== null && [...side.querySelectorAll('.each-list li')].length === 4 &&
                    [...side.querySelectorAll('.each-list li')].every(r => r.scrollWidth <= r.clientWidth + 1 && r.getBoundingClientRect().right <= side.getBoundingClientRect().right + 1); }""")
            check(f"{width} px: the rows sit in the side pane and fit", fit and no_sideways(page))

        print("\n--- 8. Colours ---")
        css = open(os.path.join(HERE, "..", "index.html"), encoding="utf-8").read()
        block = css[css.index("/* M2: model rows."):css.index('/* v21: "Jump to stage" menus')]
        bad = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|(?<![\w-])(?:white|black|red|green|blue|grey|gray)(?![\w-])", block)
        check("the new CSS uses theme variables only, no hard-coded colours", len(block) > 1500 and not bad, bad)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
