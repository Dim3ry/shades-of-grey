"""Chunk FX2 tests for Minifolio: pasting notes or an army list stops creating wrong data. New behaviour only.

1. Paste recipes: "Mark these paints as Owned" starts unticked, and Save with it unticked leaves the Shopping list alone.
2. A paint name taken from pasted text loses stray quote marks and punctuation at its ends, but keeps a mark inside the name.
3. The quick New recipe box: "Armour:" then "Metal:" saves as two recipes, each with its own part, and no line is lost.
4. Army list import: a title or points-only line is never a unit (the real Tyranid export still reads 17 units, 75 models).
5. On a phone (390 dark, 360 light): the quick box note and the Paste recipes bar fit, no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_40K = open(os.path.join(HERE, "real_40k_tyranids.txt"), encoding="utf-8").read()
SETTINGS = {"tab": "recipes", "recipeView": "recipes", "examplesChecked": True}
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read_notes(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("text=Read notes")
    page.wait_for_selector("#import-save")

def mentions(page, text):
    """[[typed, status, paint name] ...] for every paint the paste reader finds."""
    return page.evaluate("""(txt) => parseRecipeText(txt).schemes.flatMap(s => s.parts.flatMap(p => p.steps.flatMap(st =>
        st.paints.map(m => [m.typed, m.status, m.paint && m.paint.name]))))""", text)

def army(page, text):
    return page.evaluate("""(x) => { const r = parseWarhammerList(x); return r && { name: r.listName, units: r.units.map(u => u.name + ':' + u.count) }; }""", text)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.dismiss())
        t.load(page, settings=SETTINGS)

        print("\n--- 1. Mark these paints as Owned starts unticked ---")
        read_notes(page, "Dark\n\nArmour:\nZorblax Goo\nNuln Oil")
        check("the tick starts unticked", page.get_attribute("#import-owned", "aria-checked") == "false"
              and page.evaluate("importDraft.markOwned") is False)
        page.click("#import-save")
        page.wait_for_function("() => !importDraft")
        owned = page.evaluate("book.paints.filter(p => ['Zorblax Goo', 'Nuln Oil'].includes(p.name)).map(p => paintStatus(p))")
        check("saved with it unticked: no paint is made Owned", all(s != "owned" for s in owned), owned)
        read_notes(page, "Dark\n\nArmour:\nGlorp Slime\nNuln Oil")
        page.click("#import-owned")
        check("ticking it works", page.get_attribute("#import-owned", "aria-checked") == "true")
        page.click("#import-save")
        page.wait_for_function("() => !importDraft")
        check("saved with it ticked: the new paint is Owned",
              page.evaluate("paintStatus(book.paints.find(p => p.name === 'Glorp Slime'))") == "owned")

        print("\n--- 2. Stray marks at the ends of a name ---")
        got = mentions(page, "Prime\n'Ardcoat\n‘Ardcoat’, Dryad Bark.\nGal Vorbak\n\"Dryad Bark\"")
        check("quotes, comma and full stop are trimmed from what was typed",
              [m[0] for m in got] == ["Ardcoat", "Ardcoat", "Dryad Bark", "Gal Vorbak", "Dryad Bark"], got)
        check("they still match the catalogue paint", got[0][1] == "sure" and got[0][2] == "'Ardcoat" and got[2][2] == "Dryad Bark", got)
        got = mentions(page, "Armour:\n'Quibble Wump.,'\nNurgle's Rot\nQuixle's Zorbo Glow.")
        check("a new paint is kept without the stray marks, an inner apostrophe stays",
              got[0][2] == "Quibble Wump" and got[1][2] == "Nurgle's Rot" and got[2][2] == "Quixle's Zorbo Glow", got)

        print("\n--- 3. Two headings in the quick box ---")
        page.evaluate("startQuickRecipe()")
        page.fill("#quick-lines", "Armour: Macragge Blue\nMetal: Leadbelcher")
        page.wait_for_timeout(500)
        note = page.evaluate("(document.querySelector('.quick-parts-note') || {}).textContent || ''")
        check("the preview says it saves as two recipes", note == "Saves as 2 recipes: Armour, Metal.", note)
        before = page.evaluate("book.recipes.length")
        page.click("#quick-save")
        page.wait_for_timeout(300)
        made = page.evaluate("book.recipes.slice(%d).map(r => [r.part, r.steps.map(s => s.paints.length)])" % before)
        check("two recipes saved, one step each, each under its own part", made == [["Armour", [1]], ["Metal", [1]]], made)
        names = page.evaluate("book.recipes.slice(%d).map(r => r.steps.map(s => book.paints.find(p => p.id === s.paints[0].paint).name))" % before)
        check("the second line (Leadbelcher) is not lost", names == [["Macragge Blue"], ["Leadbelcher"]], names)
        page.evaluate("startQuickRecipe()")
        page.fill("#quick-lines", "Eyes: Yriel Yellow")
        page.wait_for_timeout(500)
        check("one heading: no 'Saves as' line", page.locator(".quick-parts-note").count() == 0)
        page.evaluate("recipeDraft = null; renderRecipes()")

        print("\n--- 4. Army list titles ---")
        r = army(page, "Space Marines (2000 pts)\nSpace Marines (2000 pts)\n10x Intercessors\nCaptain")
        check("the title written twice is not a unit", r and r["units"] == ["Intercessors:10", "Captain:1"], r)
        r = army(page, "Space Marines\n2000 pts\nIntercessors x10\nCaptain")
        check("a points-only line is not a unit", r and r["units"] == ["Intercessors:10", "Captain:1"], r)
        r = army(page, "Space Marines (2000 pts)\nIntercessors x10\nCaptain\nBladeguard Veterans x5")
        check("a title with points is the list name, every real unit stays",
              r and r["name"] == "Space Marines" and r["units"] == ["Intercessors:10", "Captain:1", "Bladeguard Veterans:5"], r)
        r = page.evaluate("(x) => { const r = parseWarhammerList(x); return [r.units.length, r.units.reduce((a, u) => a + u.count, 0)]; }", REAL_40K)
        check("the real Tyranid export still reads 17 units, 75 models", r == [17, 75], r)

        print("\n--- 5. On a phone ---")
        for w, h, mode in [(390, 844, "dark"), (360, 640, "light")]:
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, settings={**SETTINGS, "appearance": mode})
            page.evaluate("startQuickRecipe()")
            page.fill("#quick-lines", "Armour: Macragge Blue\nMetal: Leadbelcher")
            page.wait_for_timeout(500)
            m = page.evaluate("""() => ({ sideways: document.documentElement.scrollWidth > innerWidth,
                note: !!document.querySelector('.quick-parts-note'), save: document.getElementById('quick-save').getBoundingClientRect().height })""")
            check(f"{w} {mode}: quick box note shows, no sideways scroll, Save 44 px", m["note"] and not m["sideways"] and m["save"] >= 44, m)
            page.evaluate("recipeDraft = null; renderRecipes()")   # leave the quick box first, so the paste screen opens without a question
            read_notes(page, "Dark\n\nArmour:\nZorblax Goo\nNuln Oil")
            m = page.evaluate("""() => ({ sideways: document.documentElement.scrollWidth > innerWidth,
                tick: document.getElementById('import-owned').getBoundingClientRect().height })""")
            check(f"{w} {mode}: Paste recipes bar fits, tick 44 px", not m["sideways"] and m["tick"] >= 44, m)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
