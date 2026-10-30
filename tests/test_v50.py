"""v50 tests for Minifolio (declutter chunk D4: the Recipes tab).

What changed:
 (a) Recipe list cards are collapsed: the name, the colour dots and (once you have marked paints) a short Have all / Missing line.
     The part, step count and units sit behind More info.
 (b) A recipe's steps (in the editor and when reading) are one line each: number, technique and the paints as small swatches.
     Tap the line to open the step. Technique, coats, mix ratio, note and optional sit under More options inside the open step.
     + Add step and Save recipe stay in view.
 (c) Have / Missing are the small status marks (tick, cross) with a one-line key, not word badges.
     The "What can I paint now?" hint, the Parts and techniques note, the examples card text and the "Do you own these?" explanation
     sit behind More info.

Checks:
1. Versions and the v50 Updates entry; the new code has no innerHTML and sits outside the v36/v37 scanned code.
2. Recipe list: collapsed cards, More info closed, 44 px, opens and closes, state kept while the app is open (not after a reload),
   the short status, the hint behind More info.
3. Reading a recipe: one-line steps, closed to start, swatches, tap opens, marks and key (no word badges), More options, no paint
   names in aria-labels, the optional step is shown without losing text contrast.
4. The editor: folded steps, open a step to edit paints, More options holds the five step options, a new step starts open, state is
   kept when the editor redraws, saving still keeps every value, nothing saved just by opening and folding.
5. Phone and desktop widths (360, 390, 900), dark and light: no sideways scroll, 44 px targets, text contrast 4.5 or more.
6. No page errors, no browser pop-ups, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import quiet

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def box(loc):
    return loc.bounding_box()

# Made-up paints with a mix of statuses (the first three are owned, 30 is not, 31 has no status).
PAINTS = [
    {"id": 1, "brand": "Test Paints", "name": "Deep Test Blue", "colour": "#0d2a5c", "status": "owned"},
    {"id": 2, "brand": "Test Paints", "name": "Mid Test Blue", "colour": "#3b6fb0", "status": "owned"},
    {"id": 3, "brand": "Test Paints", "name": "Test Orange", "colour": "#e8802a", "status": "low"},
    {"id": 30, "brand": "Test Paints", "name": "Wish Violet", "colour": "#7a3fb0", "status": "wishlist"},
    {"id": 31, "brand": "Test Paints", "name": "Plain Teal", "colour": "#1f9e9a"},
]
NAMES = [p["name"] for p in PAINTS]

def step(paints, technique="Base coat", coats=1, ratio="", note="", optional=False):
    return {"technique": technique, "coats": coats, "paints": [{"paint": pid, "mix": mix} for pid, mix in paints],
            "ratio": ratio, "note": note, "optional": optional}

RECIPES = [
    {"id": 201, "name": "Blue armour", "part": "Armour", "notes": "",
     "steps": [step([(1, None)], "Base coat", 2, note="thin coats"), step([(1, 50), (2, 50)], "Layer", 1, ratio="1:1"),
               step([(3, None)], "Glaze", 1, optional=True)]},
    {"id": 202, "name": "Violet cloak", "part": "Whole model", "notes": "", "steps": [step([(30, None)]), step([(2, None)], "Layer")]},
    {"id": 203, "name": "Empty recipe", "part": "Armour", "notes": "", "steps": []},
]
UNITS = [{"id": 1, "name": "Troop A", "hobby": "Test game", "faction": "Test Host", "stage": 2, "count": 5, "recipes": [201]}]
NO_STATUS = [dict((k, v) for k, v in p.items() if k != "status") for p in PAINTS]

def tab_recipes(page):
    t.blur(page)
    page.click('nav button[data-tab="recipes"]')
    quiet(page)

def saved_recipes(page):
    return page.evaluate("() => localStorage.getItem('shades-of-grey-recipes')")

def main():
    errors, csp, popups = [], [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)

        # ---------- 1. Versions and code ----------
        print("\n--- 1. Versions and code ---")
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        new_code = app[app.index("v50: the Recipes tab, decluttered"):app.index("function renderRecipeList(")]
        new_code += app[app.index("function buildStepEditor("):app.index("function buildPaintEditor(")]
        check("the new code builds nothing with innerHTML or insertAdjacentHTML", not re.search(r"innerHTML|insertAdjacentHTML", new_code))
        wheel = (app.index("v36: THE COLOUR WHEEL"), app.index("function renderGuides("))
        v37 = (app.index("v37: the group buttons"), app.index("v35: door = where this is shown"))
        helpers = [app.index("function foldStep("), app.index("function buildHaveKey("), app.index("function stepFold(")]
        check("the new helpers sit outside the code the v36 and v37 tests scan",
              all(not (wheel[0] <= h <= wheel[1]) and not (v37[0] <= h <= v37[1]) for h in helpers))

        # ---------- 2. Recipe list ----------
        print("\n--- 2. Recipe list ---")
        tab_recipes(page)
        cards = page.locator("#recipe-list li.recipe-card")
        check("three recipe cards", cards.count() == 3, cards.count())
        first = cards.filter(has_text="Blue armour")
        check("a card shows the name and colour dots", first.locator(".recipe-item .name").inner_text() == "Blue armour"
              and first.locator(".recipe-item .swatch").count() >= 2)
        more = first.locator(".more-info-button")
        check("More info starts closed", more.get_attribute("aria-expanded") == "false")
        check("the part and step count are hidden while it is closed", not first.locator(".meta").is_visible())
        check("More info is at least 44 px tall", box(more)["height"] >= 43.5, box(more))
        check("the card has no long sentence showing", len(first.inner_text().replace("More info", "").strip()) < 60, first.inner_text())
        more.click()
        check("tapping More info shows the part, steps and units", "Armour" in first.locator(".meta").inner_text()
              and "3 steps" in first.locator(".meta").inner_text() and "1 unit" in first.locator(".meta").inner_text(), first.locator(".meta").inner_text())
        check("the words change to Less info", "Less info" in more.inner_text())
        tab_recipes(page); page.click('nav button[data-tab="dashboard"]'); page.click('nav button[data-tab="recipes"]'); page.wait_for_timeout(200)
        check("an open More info stays open while the app is open", page.locator("#recipe-list li.recipe-card", has_text="Blue armour").locator(".meta").is_visible())
        more.click()
        check("tapping again closes it", not first.locator(".meta").is_visible())
        check("the status line says Have all or Missing", first.locator(".recipe-status").inner_text().strip() == "Have all"
              and cards.filter(has_text="Violet cloak").locator(".recipe-status").inner_text().strip() == "Missing 1",
              [c.locator(".recipe-status").all_inner_texts() for c in [first, cards.filter(has_text="Violet cloak")]])
        check("the status line carries a mark (shape) as well as words", first.locator(".recipe-status .status-marker svg").count() == 1)
        check("a recipe with no steps has no status line", cards.filter(has_text="Empty recipe").locator(".recipe-status").count() == 0)
        first.locator(".recipe-item").click()
        page.wait_for_timeout(200)
        check("tapping the card still opens the recipe", page.locator("#recipe-page h2", has_text="Blue armour").count() == 1)
        page.click("#recipe-page >> text=← All recipes"); page.wait_for_timeout(150)

        # open state is not kept after a reload
        page.locator("#recipe-list li.recipe-card", has_text="Blue armour").locator(".more-info-button").click()
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        tab_recipes(page)
        check("More info is closed again after a reload", not page.locator("#recipe-list .meta").first.is_visible())

        # the hint behind More info (no statuses set)
        t.load(page, paints=NO_STATUS, recipes=RECIPES, units=UNITS)
        tab_recipes(page)
        check("no status line on the cards until a paint has a status", page.locator("#recipe-list .recipe-status").count() == 0)
        page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
        page.wait_for_timeout(150)
        check("v59: no More info hint is added any more (the empty state says it)", page.locator("#can-paint-hint .more-info-button").count() == 0)
        check("What can I paint now? still filters", page.locator("#recipe-list li.recipe-card").count() == 0
              or page.locator("#recipe-list li.empty").count() == 1)
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        tab_recipes(page)
        page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
        page.wait_for_timeout(150)
        names = page.locator("#recipe-list .recipe-item .name").all_text_contents()
        check("What can I paint now? shows only recipes you can paint", names == ["Blue armour"], names)
        check("no hint shows when the filter has statuses to use", page.locator("#can-paint-hint .more-info-button").count() == 0)
        page.locator("#can-paint-box .chip", has_text="What can I paint now?").click()
        lists = page.locator("#recipe-lists")
        lists.locator("summary").click()
        check("v59: Parts and techniques has no note or More info inside it", lists.locator(".more-info-button").count() == 0)

        # ---------- 3. Reading a recipe ----------
        print("\n--- 3. Reading a recipe ---")
        page.locator("#recipe-list li.recipe-card", has_text="Blue armour").locator(".recipe-item").click()
        page.wait_for_timeout(250)
        lines = page.locator("#recipe-page ol.recipe-steps > li > .step-line")
        check("three steps, each one line", lines.count() == 3, lines.count())
        check("each line says its number and technique", [l.locator(".step-line-text").inner_text() for l in [lines.nth(i) for i in range(3)]]
              == ["1. Base coat", "2. Layer", "3. Glaze"], lines.all_inner_texts())
        check("every step starts closed", all(lines.nth(i).get_attribute("aria-expanded") == "false" for i in range(3)))
        check("step lines show small swatches (1, 2 and 1)", [lines.nth(i).locator(".swatch").count() for i in range(3)] == [1, 2, 1])
        check("step lines are at least 44 px tall", all(box(lines.nth(i))["height"] >= 43.5 for i in range(3)), [box(lines.nth(i)) for i in range(3)])
        check("a closed step hides its paints", not page.locator("#rstep-0").is_visible())
        check("the one-line key shows Have and Missing once statuses are set", page.locator("#recipe-page .have-key").inner_text().replace("\n", " ").split() == ["Have", "Missing"],
              page.locator("#recipe-page .have-key").inner_text())
        check("the key uses the shared status marks", page.locator("#recipe-page .have-key .status-marker").count() == 2)
        check("no word badges (Have / Missing pills) are drawn", page.locator(".have-badge").count() == 0)
        lines.nth(1).click()
        check("tapping a step opens it", lines.nth(1).get_attribute("aria-expanded") == "true" and page.locator("#rstep-1").is_visible())
        pl = page.locator("#rstep-1 .paint-line")
        check("the open step lists its paints", pl.count() == 2 and "Deep Test Blue" in pl.nth(0).inner_text() and "50%" in pl.nth(0).inner_text(), pl.all_inner_texts())
        check("each paint has a Have or Missing mark with a label", page.locator("#rstep-1 .have-mark[role=img]").evaluate_all("els => els.map(e => e.getAttribute('aria-label'))") == ["Have", "Have"])
        lines.nth(1).click()
        check("tapping again closes it", not page.locator("#rstep-1").is_visible())
        lines.nth(0).click()
        mi = page.locator("[aria-controls=rstep-0-more]")
        check("coats and note are behind More options", mi.inner_text().strip().startswith("More options") and not page.locator("#rstep-0-more .step-facts").is_visible())
        check("More options is at least 44 px tall", box(mi)["height"] >= 43.5, box(mi))
        mi.click()
        check("More options shows coats and the note", "2 coats" in page.locator("#rstep-0-more .step-facts").inner_text()
              and "thin coats" in page.locator("#rstep-0-more .step-note").inner_text())
        check("the words change to Fewer options", "Fewer options" in mi.inner_text())
        lines.nth(1).click(); page.locator("[aria-controls=rstep-1-more]").click()
        check("a mix ratio shows under More options", "mix 1:1" in page.locator("#rstep-1-more .step-facts").inner_text())
        check("the optional step is marked by its bar, and its text keeps full opacity",
              page.locator("li.optional-step").count() == 1 and page.evaluate("() => getComputedStyle(document.querySelector('li.optional-step')).opacity") == "1")
        lines.nth(2).click(); page.locator("[aria-controls=rstep-2-more]").click()
        check("optional is shown behind More options", "optional" in page.locator("#rstep-2-more .step-facts").inner_text())
        labels = page.evaluate("() => [...document.querySelectorAll('#recipe-page [aria-label], #recipe-list [aria-label]')].map(e => e.getAttribute('aria-label')).join(' | ')")
        check("no paint names in any aria-label", not any(n.lower() in labels.lower() for n in NAMES), labels)
        # a step with a missing paint shows a mark on its closed line
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        tab_recipes(page)
        page.locator("#recipe-list li.recipe-card", has_text="Violet cloak").locator(".recipe-item").click(); page.wait_for_timeout(200)
        vl = page.locator("#recipe-page ol.recipe-steps > li > .step-line")
        check("a closed step with a missing paint shows the cross mark", vl.nth(0).locator(".have-mark.missing").count() == 1 and vl.nth(1).locator(".have-mark").count() == 0)
        page.locator("#recipe-page >> text=← All recipes").click(); page.wait_for_timeout(100)
        t.load(page, paints=NO_STATUS, recipes=RECIPES, units=UNITS)
        tab_recipes(page)
        page.locator("#recipe-list li.recipe-card", has_text="Blue armour").locator(".recipe-item").click(); page.wait_for_timeout(200)
        check("with no statuses there is no key and no marks", page.locator(".have-key").count() == 0 and page.locator(".have-mark").count() == 0)

        # ---------- 4. The editor ----------
        print("\n--- 4. The editor ---")
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        before = saved_recipes(page)
        t.edit_recipe(page, 201)
        el = page.locator("#recipe-page li.step-edit")
        check("the editor shows three folded steps", el.count() == 3 and all(el.nth(i).locator(".step-line").get_attribute("aria-expanded") == "false" for i in range(3)))
        check("the folded lines show number, technique and swatches", el.nth(1).locator(".step-line-text").inner_text() == "2. Layer" and el.nth(1).locator(".step-line .swatch").count() == 2)
        check("the paint boxes are hidden while folded", not page.locator('[data-key="step-0-paint-0"]').is_visible())
        check("the technique and coats are not in view while folded", not el.nth(0).locator("select").first.is_visible())
        el.nth(0).locator(".step-line").click()
        check("opening a step shows its paint box", page.locator('[data-key="step-0-paint-0"]').is_visible() and page.input_value('[data-key="step-0-paint-0"]') == "Deep Test Blue")
        check("technique, coats, note and optional are behind More options", not el.nth(0).locator("select").first.is_visible()
              and el.nth(0).locator(".more-info-button").inner_text().strip().startswith("More options"))
        el.nth(0).locator(".more-info-button").click()
        check("More options holds the technique, coats, note and optional", el.nth(0).locator("select").first.is_visible()
              and el.nth(0).locator("input[type=number]").first.is_visible()
              and el.nth(0).locator("input[placeholder='e.g. heavier on the top']").is_visible()
              and el.nth(0).locator("input[type=checkbox]").is_visible())
        check("a single-paint step has no mix ratio box", el.nth(0).locator("input[aria-label='Mix ratio']").count() == 0)
        el.nth(1).locator(".step-line").click(); el.nth(1).locator(".more-info-button").click()
        check("a mixed step has its mix ratio under More options", el.nth(1).locator("input[aria-label='Mix ratio']").is_visible()
              and el.nth(1).locator("input[aria-label='Mix ratio']").input_value() == "1:1")
        check("targets in the open steps are at least 44 px", all(box(loc)["height"] >= 43.5 for loc in
              [el.nth(0).locator(".step-line"), el.nth(0).locator(".more-info-button"), el.nth(0).locator(".icon-button").first]))
        check("opening and folding saved nothing", saved_recipes(page) == before)
        # Add step: prominent, and the new step starts open with the cursor in its paint box
        add = page.locator("#recipe-page button.add-step")
        check("+ Add step is a full-width button at least 44 px tall", add.count() == 1 and box(add)["height"] >= 43.5 and box(add)["width"] > 250, box(add))
        add.click(); page.wait_for_timeout(250)
        check("a new step is added and starts open", page.locator("#recipe-page li.step-edit").count() == 4
              and page.locator('[data-key="step-3-paint-0"]').is_visible())
        check("the steps opened before are still open after the redraw", el.nth(0).locator(".step-line").get_attribute("aria-expanded") == "true"
              and el.nth(1).locator(".more-info-button").get_attribute("aria-expanded") == "true")
        page.fill('[data-key="step-3-paint-0"]', "Plain Teal"); page.keyboard.press("Tab")
        el.nth(3).locator(".step-line").click()
        check("a folded line is updated with what you typed", el.nth(3).locator(".step-line-text").inner_text().startswith("4.") and el.nth(3).locator(".step-line .swatch").count() == 1,
              el.nth(3).locator(".step-line").inner_text())
        # editing inside More options is saved
        el.nth(0).locator("input[placeholder='e.g. heavier on the top']").fill("two thin coats")
        save = page.locator("#recipe-page button.primary-button", has_text="Save recipe")
        check("Save recipe is a prominent button at least 44 px tall", save.count() == 1 and box(save)["height"] >= 43.5, box(save))
        save.click(); page.wait_for_timeout(300)
        saved = json.loads(saved_recipes(page))
        r201 = next(r for r in saved["recipes"] if r["id"] == 201)
        check("saving keeps every value, including the note typed under More options",
              r201["steps"][0]["note"] == "two thin coats" and r201["steps"][0]["coats"] == 2 and r201["steps"][1]["ratio"] == "1:1"
              and r201["steps"][2]["optional"] is True and len(r201["steps"]) == 4 and r201["steps"][3]["paints"][0]["paint"] == 31, r201)
        # a brand-new recipe starts with its first step open
        t.open_editor(page)
        check("a new recipe starts with the first step open", page.locator('[data-key="step-0-paint-0"]').is_visible())
        page.click("#recipe-page >> text=Cancel"); page.wait_for_timeout(200)
        labels = page.evaluate("() => [...document.querySelectorAll('#recipe-page [aria-label]')].map(e => e.getAttribute('aria-label')).join(' | ')")
        check("no paint names in the editor's aria-labels", not any(n.lower() in labels.lower() for n in NAMES), labels)

        # the examples card and the "Do you own these?" card keep their buttons in view and the long text behind More info
        t.load(page, paints=PAINTS, recipes=[dict(RECIPES[0], example=True)], units=UNITS)
        tab_recipes(page)
        ex = page.locator("#examples-card-recipes")
        check("the examples card: the title and both buttons show, the long text is behind More info",
              ex.locator("strong").is_visible() and ex.locator(".clear-recipe-examples").is_visible() and ex.locator(".keep-recipe-examples").is_visible()
              and ex.locator(".more-info-button").count() == 1 and not ex.locator(".hint").is_visible())
        ex.locator(".more-info-button").click()
        check("the examples card: opening shows the explanation", "stays yours" in ex.locator(".hint").inner_text())
        t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        t.open_editor(page)
        page.fill('[data-key="step-0-paint-0"]', "Brand New Paint"); page.keyboard.press("Tab"); page.wait_for_timeout(250)
        own = page.locator("#recipe-own")
        check("Do you own these?: All, None and Let me pick show; the explanation is behind More info",
              own.locator(".chip").count() == 3 and own.locator(".more-info-button").count() == 1 and not own.locator(".hint").first.is_visible(), own.inner_text())
        own.locator(".more-info-button").click()
        check("Do you own these?: opening shows the explanation", "shopping list" in own.locator(".hint").first.inner_text())
        own.locator(".chip", has_text="None").click(); page.wait_for_timeout(100)
        check("Do you own these?: the explanation stays open after you pick", own.locator(".hint").first.is_visible())
        page.click("#recipe-page >> text=Cancel"); page.wait_for_timeout(150)

        # ---------- 5. Widths, dark and light ----------
        print("\n--- 5. Widths, dark and light ---")
        for appearance in ("dark", "light"):
            for width in (360, 390, 900):
                page.set_viewport_size({"width": width, "height": 844})
                t.load(page, paints=PAINTS, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                tag = f"{appearance} {width}px"
                tab_recipes(page)
                check(f"[{tag}] list: no sideways scroll", t.no_sideways(page))
                t.shot(page, f"v50-list-{appearance}-{width}.png")
                bg = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('li.recipe-card')).backgroundColor"))
                col = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('.recipe-status')).color"))
                check(f"[{tag}] list: status text contrast 4.5 or more", t.contrast(col, bg) >= 4.5, round(t.contrast(col, bg), 2))
                mc = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('li.recipe-card .more-info-button')).color"))
                check(f"[{tag}] list: More info text contrast 4.5 or more", t.contrast(mc, bg) >= 4.5, round(t.contrast(mc, bg), 2))
                page.locator("#recipe-list li.recipe-card", has_text="Blue armour").locator(".recipe-item").click(); page.wait_for_timeout(200)
                page.locator("#recipe-page ol.recipe-steps > li > .step-line").nth(1).click()
                page.locator("[aria-controls=rstep-1-more]").click()
                check(f"[{tag}] reading: no sideways scroll", t.no_sideways(page))
                t.shot(page, f"v50-read-{appearance}-{width}.png")
                card_bg = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('#recipe-page .card')).backgroundColor"))
                lc = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('.step-line-text')).color"))
                check(f"[{tag}] reading: step line contrast 4.5 or more", t.contrast(lc, card_bg) >= 4.5, round(t.contrast(lc, card_bg), 2))
                fc = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('.step-facts')).color"))
                check(f"[{tag}] reading: step facts contrast 4.5 or more", t.contrast(fc, card_bg) >= 4.5, round(t.contrast(fc, card_bg), 2))
                kc = t.rgb(page.evaluate("() => getComputedStyle(document.querySelector('.have-key')).color"))
                check(f"[{tag}] reading: key contrast 4.5 or more", t.contrast(kc, card_bg) >= 4.5, round(t.contrast(kc, card_bg), 2))
                page.locator("#recipe-page button", has_text="Edit").first.click(); page.wait_for_timeout(300)
                page.locator("#recipe-page li.step-edit .step-line").nth(1).click()
                page.locator("#recipe-page li.step-edit").nth(1).locator(".more-info-button").click()
                check(f"[{tag}] editor: no sideways scroll", t.no_sideways(page))
                t.shot(page, f"v50-edit-{appearance}-{width}.png")
                sizes = page.evaluate("""() => [...document.querySelectorAll('#recipe-page button')]
                    .filter(e => e.offsetParent !== null && !e.closest('#colour-ideas')).map(e => { const r = e.getBoundingClientRect(); return [e.className || e.tagName, Math.round(r.height)]; })""")
                small = [s for s in sizes if s[1] < 43]
                check(f"[{tag}] editor: every visible button is at least 44 px tall", not small, small[:6])

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not popups, popups)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
