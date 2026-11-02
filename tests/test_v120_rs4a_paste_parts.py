"""Chunk RS4a tests for Minifolio: paste import. New behaviour only.

1. A pasted heading that matches a Part you already have (capitals, spaces, a trailing "s" ignored) uses that Part; no new Part is made.
2. A heading that matches none adds one new Part, in the same capital-letter style, once (a second heading with the same words reuses it).
3. A section under a part ("Bases – Rocks") belongs to the part's own heading ("Base"); recipe names are unchanged.
4. Stray quote marks round a typed paint name that matches nothing are dropped; the catalogue paint 'Ardcoat is still found.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def paste_and_save(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("text=Read notes")
    page.wait_for_timeout(200)
    page.click("#import-save")
    page.wait_for_timeout(300)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        t.load(page, settings={"tab": "recipes", "recipeView": "recipes", "examplesChecked": True})
        page.evaluate("() => { book.parts = DEFAULT_PARTS.slice(); }")
        parts_before = page.evaluate("book.parts.slice()")

        # 1. Headings that match Parts you have.
        paste_and_save(page, "Tyranids\n\nCLOTH:\nAbaddon Black\n\nArmours:\nRetributor Armour\n\nWhole model:\nCorvus Black")
        recipes = page.evaluate("book.recipes.map(r => [r.name, r.part])")
        check("existing Parts used, capitals and trailing s ignored", [r[1] for r in recipes] == ["Cloth", "Armour", "Whole model"], recipes)
        check("recipe names kept as typed", [r[0] for r in recipes] == ["CLOTH", "Armours", "Whole model"], recipes)
        check("no new Part made", page.evaluate("book.parts") == parts_before, page.evaluate("book.parts"))

        # 2. A heading that matches none: one new Part, made once.
        paste_and_save(page, "Hive fleet\n\nglowy TENTACLES:\nAbaddon Black\n\nGlowy tentacle:\nRetributor Armour")
        parts = page.evaluate("book.parts")
        added = [x for x in parts if x not in parts_before]
        check("one new Part added, not two", added == ["Glowy tentacles"], added)
        newest = page.evaluate("book.recipes.slice(-2).map(r => r.part)")
        check("both recipes use the new Part", newest == ["Glowy tentacles", "Glowy tentacles"], newest)
        check("Part filter shows it once", page.evaluate("uniqueSorted(book.recipes.map(r => r.part)).filter(x => /glowy/i.test(x)).length") == 1)

        # 3. A section under a part belongs to the part's heading.
        paste_and_save(page, "T'au\n\nBases:\nRocks = Mechrite Red\nDirt = Rhinox Hide")
        sub = page.evaluate("book.recipes.slice(-2).map(r => [r.name, r.part])")
        check("sections under Bases use the Part Base", [s[1] for s in sub] == ["Base", "Base"], sub)
        check("section recipe names keep the heading", [s[0] for s in sub] == ["Bases – Rocks", "Bases – Dirt"], sub)
        check("still only the one new Part", len([x for x in page.evaluate("book.parts") if x not in parts_before]) == 1)

        # 4. Quote marks.
        m = lambda s: page.evaluate("t => matchPaint(t, {})", s)
        for typed in ["'Foo Bar'", "“Foo Bar”", "‘Foo Bar’", '"Foo Bar"']:
            r = m(typed)
            check("stray quotes dropped from " + typed, r["status"] == "new" and r["paint"]["name"] == "Foo Bar", r)
        for typed in ["Gloss", "'Ardcoat", "‘Ardcoat’", "Ardcoat"]:
            r = m(typed)
            check("catalogue paint found for " + typed, r["status"] == "sure" and r["paint"]["name"] == "'Ardcoat", r)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
