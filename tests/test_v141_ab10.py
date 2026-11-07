"""AB10 tests for Minifolio (fold labels and error messages, from the approved AI-tells items AT-23 and AT-47). New behaviour only:
1. No fold is labelled "More info" or "Less info" (Settings, Models, Painting, Updates), and the fixed names are in place.
2. Whole-row folds (Help topics, Updates entries) show only the arrow and keep an accessible name.
3. The rewritten error messages carry neither "Sorry" nor "Nothing has changed", except where the AB10 table keeps them
   (the two "full backup couldn't be made" messages, where the app itself failed). Read from the source, because most of these
   messages need a full device to appear.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fold_opener   # Settings cards fold shut since v53
import test_v44 as e   # fresh, existing, main_tab, sub_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fold_words(page):
    """The visible words of every fold button on the page (shown or not), as the person would read them."""
    return page.evaluate("""() => [...document.querySelectorAll('.more-info-button')].map(b => (b.textContent || '').trim())""")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        fold_opener.open_cards_on_load(page)

        print("\n--- 1. Fold names ---")
        e.fresh(page)
        e.main_tab(page, "units")
        words = fold_words(page)
        check("Models: the examples strip fold is 'What's in it'", "What's in it" in words, words)
        e.main_tab(page, "settings")
        page.wait_for_timeout(200)
        words = fold_words(page)
        for fixed in ("Which one?", "What's sent", "Who gets what"):
            check(f"Settings has a fold called '{fixed}'", fixed in words, words)
        check("Settings: no fold says More info or Less info", not any(w in ("More info", "Less info") for w in words), words)
        which = page.locator('.more-info-button[aria-controls="more-backups"]')
        check("the Backups fold is the 'Which one?' one and starts shut",
              which.count() == 1 and which.inner_text().strip() == "Which one?" and which.get_attribute("aria-expanded") == "false")
        which.click()
        check("opening it keeps the name and flips aria-expanded", which.inner_text().strip() == "Which one?" and which.get_attribute("aria-expanded") == "true")

        empty_book = {"parts": ["Whole model"], "techniques": ["Layer"], "v15": True, "shorthand": {}, "paints": [], "recipes": [], "schemes": []}
        e.existing(page, [], empty_book)
        e.main_tab(page, "recipes")
        e.recipe_view(page, "schemes")
        words = fold_words(page)
        check("an empty Schemes page folds 'What's a scheme?'", "What's a scheme?" in words, words)
        check("an empty Recipes page folds 'What's a recipe?'", "What's a recipe?" in words, words)
        check("the 'Recipe or scheme? What's the difference' fold is untouched (AT-49 was skipped)", any(w.startswith("Recipe or scheme?") for w in words), words)

        print("\n--- 2. Whole-row folds show only the arrow ---")
        e.main_tab(page, "settings")
        e.sub_tab(page, "help")
        topic = page.locator("#view-help .help details > summary").first
        css = page.evaluate("""() => { const s = document.querySelector('#view-help .help details > summary');
            return { after: getComputedStyle(s, '::after').content, before: getComputedStyle(s, '::before').content }; }""")
        check("a Help topic shows no 'More info' word", css["after"] in ("none", "normal", '""'), css)
        check("a Help topic still has its arrow", css["before"] == '""', css)
        check("a Help topic keeps its name (the title text)", len(topic.inner_text().strip()) > 3)
        e.sub_tab(page, "updates")
        btns = page.locator('#view-updates .more-info-button[aria-controls^="more-release-"]')
        check("Updates entries have fold buttons", btns.count() >= 1)
        first = btns.first
        check("an Updates entry button shows no words, only the arrow",
              first.inner_text().strip() == "" and first.locator(".fold-mark").count() == 1)
        check("…and keeps an accessible name that says what it opens", (first.get_attribute("aria-label") or "").startswith("What changed in v"), first.get_attribute("aria-label"))
        check("…and the newest entry starts open", first.get_attribute("aria-expanded") == "true")
        check("fold buttons stay 44 px tall", first.bounding_box()["height"] >= 44, first.bounding_box())

        check("no page errors", not errors, errors)
        browser.close()

    print("\n--- 3. Error wording ---")
    src = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
    check("no message says 'Nothing has changed' or 'so nothing has changed'", not re.search(r"[Nn]othing has changed\.|so nothing has changed", src))
    sorry = re.findall(r'"Sorry[^"]*"', src)
    check("'Sorry' is left only on the two 'full backup' failures", len(sorry) == 2 and all("full backup" in s for s in sorry), sorry)
    for needle in ("No room for a safety copy of your units, so the restore stopped. Save a backup first.",
                   "That image couldn't be read. Try a different photo.",
                   "so it was not restored."):
        check(f"the rewrite is there: {needle[:40]}…", needle in src)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
