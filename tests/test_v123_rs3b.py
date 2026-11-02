"""RS3b tests for Minifolio: the quick New recipe form and the "Do you own these?" sheet. New behaviour only:
1. + New recipe opens the quick form: one box with the cursor in it, no preview and a grey Save until there is a paint.
2. The box is read by the paste reader: a known part (capitals and a trailing s ignored), no part, one paint per line, "then",
   a mix ratio and (optional), a new part. The preview updates after a short wait and marks a paint that is not in the paint list.
3. A step title (technique) set by hand under More options stays when that step's paint changes; one nobody set follows the paint.
   The full editor keeps a hand-set technique too.
4. Save with no taps in More options makes the recipe and opens its page; saving does not change what is owned.
5. The Owned sheet: only paints in the paint list, ticks follow Owned, 44 px taps; Done and Skip; no sheet without a listed paint.
6. Edit steps and paints and a new recipe from a unit still open the full editor.
7. 390x844, 360x640, 360x400 (keyboard open) and 320 px, dark and light: no sideways scroll, taps 44 px, Save reachable.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNIT = {"id": 1, "name": "Squad", "hobby": "Game", "stage": 1, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]}

def start(page, mode="dark"):
    t.load(page, settings={"tab": "recipes", "recipeView": "recipes", "examplesChecked": True, "appearance": mode}, units=[UNIT])
    page.evaluate("() => { book.parts = ['Whole model', 'Armour', 'Eyes']; }")
    page.click("#new-recipe")
    quiet(page)

def type_lines(page, text, wait=450):
    page.fill("#quick-lines", text)
    page.wait_for_timeout(wait)

PREVIEW = """() => { const p = document.getElementById('quick-preview');
    return { hidden: p.hidden, meta: (p.querySelector('.quick-meta') || {}).textContent || '',
             rows: [...p.querySelectorAll('.quick-row')].map(r => ({ name: r.querySelector('.quick-name').textContent,
                 tech: (r.querySelector('.quick-tech') || {}).textContent || '', swatches: r.querySelectorAll('.swatch').length,
                 amber: r.classList.contains('quick-unknown') && getComputedStyle(r).borderTopColor === getComputedStyle(document.documentElement).getPropertyValue('--caution').trim().replace(/^#(..)(..)(..)$/, (m, a, b, c) => `rgb(${parseInt(a, 16)}, ${parseInt(b, 16)}, ${parseInt(c, 16)})`),
                 note: (r.querySelector('.quick-unknown-note') || {}).textContent || '' })),
             saveOff: document.getElementById('quick-save').disabled }; }"""

def preview(page):
    return page.evaluate(PREVIEW)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. The form ---")
        start(page)
        form = page.evaluate("""() => ({ title: document.querySelector('#recipe-page h2').textContent, focus: document.activeElement.id,
            label: document.getElementById('quick-lines').closest('label').firstChild.textContent,
            placeholder: document.getElementById('quick-lines').placeholder, more: document.querySelector('.quick-more .more-info-button').textContent,
            moreOpen: document.querySelector('.quick-more .more-info-button').getAttribute('aria-expanded'),
            order: [...document.querySelectorAll('#quick-lines, #quick-preview, .quick-more, #quick-save')].map(e => e.id || e.className.split(' ').pop()) })""")
        check("title New recipe, cursor in the box, label and example placeholder",
              form["title"] == "New recipe" and form["focus"] == "quick-lines" and form["label"] == "Type or paste lines"
              and form["placeholder"] == "Eyes: yriel yellow, then flash gitz yellow", form)
        check("box, preview, More options (closed), then Save, in that order",
              form["order"] == ["quick-lines", "quick-preview", "quick-more", "quick-save"] and form["moreOpen"] == "false" and form["more"].startswith("More options"), form)
        pv = preview(page)
        check("empty box: no preview, Save is grey", pv["hidden"] and pv["saveOff"], pv)

        print("\n--- 2. Reading the box ---")
        page.fill("#quick-lines", "eye: yriel yellow, then flash gitz yellow")
        page.wait_for_timeout(120)
        check("the preview waits until typing stops", preview(page)["hidden"])
        page.wait_for_timeout(350)
        pv = preview(page)
        check("a known part: 'eye' is Eyes from the Parts list, the name reads Eyes yellow glow",
              "Eyes" in pv["meta"] and "Eyes yellow glow" in pv["meta"] and page.evaluate("recipeDraft.part") == "Eyes", pv["meta"])
        check("comma then 'then': two numbered rows with a swatch and the paint name, nothing marked, Save is on",
              [r["name"] for r in pv["rows"]] == ["Yriel Yellow", "Flash Gitz Yellow"] and all(r["swatches"] == 1 and not r["amber"] and not r["note"] for r in pv["rows"])
              and not pv["saveOff"], pv)
        check("no technique shows when none was typed", all(not r["tech"] for r in pv["rows"]), pv["rows"])
        type_lines(page, "yriel yellow, flash gitz yellow")
        pv = preview(page)
        check("no part: two rows, no Part shown, a plain name", len(pv["rows"]) == 2 and "Part" not in pv["meta"] and "Yellow recipe" in pv["meta"]
              and page.evaluate("recipeDraft.part") == "", pv)
        type_lines(page, "macragge blue then nuln oil wash\nblorpo pink")
        pv = preview(page)
        check("one paint per line and 'then' with no comma: three rows", [r["name"] for r in pv["rows"]] == ["Macragge Blue", "Nuln Oil", "Blorpo Pink"], pv["rows"])
        check("a typed technique shows on its row", pv["rows"][1]["tech"] == "Wash" and not pv["rows"][0]["tech"], pv["rows"])
        check("a paint not in the paint list: amber outline and the one line, others unmarked",
              pv["rows"][2]["amber"] and pv["rows"][2]["note"] == "Not in the paint list. Kept as typed." and not pv["rows"][0]["amber"], pv["rows"])
        type_lines(page, "Armour: 2:1 macragge blue:contrast medium, nuln oil (optional)")
        st = page.evaluate("recipeDraft.steps.map(s => ({ n: s.paints.map(p => p.name), mix: s.paints.map(p => p.mix), r: s.ratio, o: s.optional }))")
        check("a 2:1 mix and (optional) read as in Paste recipes",
              st == [{"n": ["Macragge Blue", "Contrast Medium"], "mix": [67, 33], "r": "2:1", "o": False}, {"n": ["Nuln Oil"], "mix": [100], "r": "", "o": True}], st)
        type_lines(page, "Eyes:")
        check("a part and no paint: Save stays grey", preview(page)["saveOff"])
        type_lines(page, "", wait=50)
        check("emptying the box hides the preview again", preview(page)["hidden"] and preview(page)["saveOff"])

        print("\n--- 3. Step titles set by hand ---")
        type_lines(page, "Eyes: yriel yellow, flash gitz yellow")
        page.click(".quick-more .more-info-button")
        page.select_option('[data-key="quick-0-technique"]', "Base coat")
        page.wait_for_timeout(50)
        type_lines(page, "Eyes: nuln oil, agrax earthshade")
        tech = page.evaluate("recipeDraft.steps.map(s => s.technique)")
        auto = page.evaluate("""() => document.querySelector('[data-key="quick-1-technique"]').options[0].text""")
        check("a title set by hand stays when the paint changes", tech[0] == "Base coat" and preview(page)["rows"][0]["tech"] == "Base coat", tech)
        check("a title nobody set follows the paint (blank, Auto now guesses Wash)", tech[1] == "" and auto == "Auto: Wash", (tech, auto))
        page.click("#quick-save")
        quiet(page)
        page.click("#dialog-no")
        words = page.evaluate("() => [...document.querySelectorAll('#recipe-page .step-line-text')].map(e => e.textContent)")
        check("on the saved recipe step 1 keeps Base coat and step 2 follows its paint", words == ["1. Nuln Oil, Base coat", "2. Agrax Earthshade, Wash"], words)
        page.evaluate("() => startNewRecipe(null)")
        quiet(page)
        t.set_step_paint(page, 0, "Yriel Yellow")
        page.evaluate("() => { recipeDraft.steps[0].technique = 'Layer'; }")
        t.set_step_paint(page, 0, "Nuln Oil")
        check("the full editor keeps a hand-set technique when the paint changes", page.evaluate("recipeDraft.steps[0].technique") == "Layer")
        page.evaluate("() => { recipeDraft = null; renderRecipes(); }")

        print("\n--- 4. Save and the Owned sheet ---")
        start(page)
        before = page.evaluate("() => book.paints.map(p => p.name + ':' + paintStatus(p))")
        type_lines(page, "Banners: macragge blue, then nuln oil\nblorpo pink")
        page.click("#quick-save")
        quiet(page)
        rec = page.evaluate("() => { const r = book.recipes[book.recipes.length - 1]; return { open: openRecipeId === r.id, draft: recipeDraft, name: r.name, part: r.part, n: r.steps.map(s => paintById(s.paints[0].paint).name) }; }")
        check("Save with no taps in More options makes the recipe and opens its page",
              rec["open"] and rec["draft"] is None and rec["name"] == "Banners blue" and rec["n"] == ["Macragge Blue", "Nuln Oil", "Blorpo Pink"], rec)
        check("a new part joins the Parts list the way Paste recipes adds one", rec["part"] == "Banners" and "Banners" in page.evaluate("book.parts"))
        after = page.evaluate("() => book.paints.map(p => p.name + ':' + paintStatus(p))")
        check("saving changes nothing that is owned; the typed paint is in Your Palette with no status",
              after[:len(before)] == before and "Blorpo Pink:" in after and "Nuln Oil:" in after, after)
        sheet = page.evaluate("""() => { const d = document.getElementById('dialog').getBoundingClientRect();
            return { title: document.getElementById('dialog-message').textContent, sheet: document.getElementById('dialog-backdrop').classList.contains('dialog-sheet'),
              bottom: Math.round(innerHeight - d.bottom), rows: [...document.querySelectorAll('.own-sheet-row')].map(r => ({ name: r.querySelector('.own-sheet-name').textContent,
              ticked: r.querySelector('.pick-tick').getAttribute('aria-checked'), swatch: !!r.querySelector('.swatch'),
              tap: Math.min(r.querySelector('.pick-tick').getBoundingClientRect().width, r.querySelector('.pick-tick').getBoundingClientRect().height),
              box: r.querySelector('.pick-box').getBoundingClientRect().width })),
              buttons: [...document.querySelectorAll('#dialog-buttons button')].filter(b => b.offsetParent).map(b => b.textContent),
              behindRecipe: !document.getElementById('recipe-page').classList.contains('hidden') && !document.getElementById('quick-lines') }; }""")
        check("after Save, over the recipe page, a bottom sheet titled Do you own these?",
              sheet["title"] == "Do you own these?" and sheet["sheet"] and sheet["bottom"] == 0 and sheet["behindRecipe"], sheet)
        check("it lists only paints in the paint list, ticked if already Owned",
              [(r["name"], r["ticked"]) for r in sheet["rows"]] == [("Macragge Blue", "true"), ("Nuln Oil", "false")] and all(r["swatch"] for r in sheet["rows"]), sheet["rows"])
        check("tick boxes: 24 px box, 44 px tap; buttons Skip and Done",
              all(r["box"] == 24 and r["tap"] >= 44 for r in sheet["rows"]) and sheet["buttons"] == ["Skip", "Done"], sheet)
        page.click('.own-sheet-row:has-text("Nuln Oil") .pick-tick')
        page.click('.own-sheet-row:has-text("Macragge Blue") .own-sheet-name')
        page.click("#dialog-yes")
        quiet(page)
        st = page.evaluate("() => Object.fromEntries(book.paints.map(p => [p.name, paintStatus(p)]))")
        check("Done marks the ticked paint Owned and clears Owned from the unticked one",
              st["Nuln Oil"] == "owned" and st["Macragge Blue"] == "" and st["Blorpo Pink"] == "", st)
        page.evaluate("() => { openRecipeId = null; renderRecipes(); }")
        page.click("#new-recipe"); quiet(page)
        type_lines(page, "macragge blue, nuln oil")
        before = page.evaluate("() => JSON.stringify(book.paints.map(p => [p.name, p.status || '', !!p.owned]))")
        page.click("#quick-save"); quiet(page)
        page.click('.own-sheet-row:has-text("Macragge Blue") .pick-tick')
        page.click('.own-sheet-row:has-text("Nuln Oil") .pick-tick')
        page.click("#dialog-no"); quiet(page)
        check("Skip changes nothing", page.evaluate("() => JSON.stringify(book.paints.map(p => [p.name, p.status || '', !!p.owned]))") == before
              and page.locator("#dialog-backdrop.hidden").count() == 1)
        page.evaluate("() => { openRecipeId = null; renderRecipes(); }")
        page.click("#new-recipe"); quiet(page)
        type_lines(page, "zarbo teal\nquonk mauve")
        page.click("#quick-save"); quiet(page)
        check("no sheet when the recipe has no paint from the paint list",
              page.locator("#dialog-backdrop.hidden").count() == 1 and page.evaluate("openRecipeId") is not None)

        print("\n--- 5. Other routes keep the full editor ---")
        page.click("#recipe-page .recipe-menu-button"); page.click("#recipe-page >> text=Edit steps and paints")
        quiet(page)
        check("Edit steps and paints opens the full editor", page.inner_text("#recipe-page h2") == "Edit recipe" and page.locator("#quick-lines").count() == 0
              and page.locator("#recipe-page button.add-step").count() == 1)
        page.evaluate("() => { recipeDraft = null; startNewRecipe(1); }")
        quiet(page)
        check("a new recipe from a unit opens the full editor", page.locator("#quick-lines").count() == 0 and page.locator("#recipe-page button.add-step").count() == 1)
        page.evaluate("() => { recipeDraft = null; renderRecipes(); }")

        print("\n--- 6. Phone sizes, dark and light ---")
        for mode in ("dark", "light"):
            start(page, mode)
            for width, height in ((390, 844), (360, 640), (360, 400), (320, 640)):
                page.set_viewport_size({"width": width, "height": height})
                if width == 390:
                    type_lines(page, "Eyes: yriel yellow, then flash gitz yellow\nblorpo pink with a very long name that wraps")
                    page.click(".quick-more .more-info-button")
                page.focus("#quick-lines")
                quiet(page)
                label = f"{mode} {width}x{height}: "
                small = page.evaluate("""() => [...document.querySelectorAll('#recipe-page button, #recipe-page select, #recipe-page input')].filter(b => b.offsetParent)
                    .filter(b => b.getBoundingClientRect().height < 43.5).map(b => (b.textContent || b.dataset.key || b.id).trim().slice(0, 20))""")
                check(label + "no sideways scroll, taps 44 px or more", t.no_sideways(page) and not small, small)
                if (width, height) == (360, 400):
                    page.locator("#quick-save").scroll_into_view_if_needed()
                    box = page.locator("#quick-save").bounding_box()
                    check(label + "Save can be scrolled into view above the keyboard", box and box["y"] + box["height"] <= 400 and box["width"] >= 300, box)
                page.screenshot(path=os.path.join(t.SHOTS, f"rs3b_quick_{mode}_{width}x{height}.png"))
            page.set_viewport_size({"width": 360, "height": 640})
            page.click("#quick-save"); quiet(page)
            fit = page.evaluate("""() => { const d = document.getElementById('dialog').getBoundingClientRect();
                return d.left >= 0 && d.right <= innerWidth + 0.5 && d.top >= 0 && Math.round(d.bottom) === innerHeight && document.documentElement.scrollWidth <= innerWidth + 1; }""")
            check(f"{mode} 360x640: the sheet fits along the bottom", fit)
            page.screenshot(path=os.path.join(t.SHOTS, f"rs3b_sheet_{mode}_360.png"))
            page.click("#dialog-no")
        page.set_viewport_size({"width": 390, "height": 844})

        check("no browser pop-ups", not dialogs, dialogs)
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
