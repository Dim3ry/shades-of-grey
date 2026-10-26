"""v59 tests for Minifolio (chunk 1.4: the AI-look wording cleanup, brought up to date).

What changed:
 PR #20 shortened the wording on empty screens, the feedback card and a few hints (and dropped a few hint lines that only
 repeated what the screen already shows). It was made at v56, before chunks 1.1 to 1.3, so it is carried over here as v59.
 Only words changed: the examples card (v56), the Save a backup? card (v57) and "Uses example paints" (v58) work as before.

Checks:
1. Versions, the v59 Updates entry, and the v56 entry is only chunk 1.1's.
2. The shorter words in index.html and app.js, and the old long ones are gone.
3. The empty screens on a real page: Units, Recipes, Your Palette, Shopping.
4. The newer cards still work: the examples card's Clear examples and Keep them, the backup card, Uses example paints.
5. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v44 as e   # fresh, main_tab, recipe_view

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def empty(page):
    """Something saved, but no units, recipes or paints (so no examples are seeded)."""
    t.load(page, paints=[], recipes=[], units=[])

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        e.fresh(page)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v59')")
        check("the entry says it is shorter wording only", entry and "Shorter wording" in " ".join(entry["changes"]), entry)

        # ---------- 2. The words ----------
        print("\n--- 2. The shorter words ---")
        check("Updates: the feedback line is short", page.text_content("#feedback-explain") == "About 2 minutes.", page.text_content("#feedback-explain"))
        check("Updates: the coming-soon line is short", page.text_content("#feedback-soon") == "Feedback form not available yet.")
        check("Help: no line above the topics", "Tap a topic to open it" not in html and page.locator("#view-help .help-intro .hint").count() == 0)
        check("Help: Getting started is still a topic", page.locator("#view-help .help summary", has_text="Getting started").count() == 1)
        check("Add unit: no 'Adding a whole army?' line, the import buttons are still there",
              "Adding a whole army?" not in html and page.locator("#add-import-buttons button").count() == 2)
        check("Your Palette: the scan button has no camera picture, and Help names it the same way",
              page.text_content("#scan-button").startswith("Scan a paint pot") and "<strong>📷 Scan a paint pot" not in html)
        hint = page.text_content("#restore-examples-hint")
        check("Settings: Restore example recipes has one short line and no heading repeating the button",
              page.locator("#restore-examples-section h3").count() == 0 and "never changed" in hint and len(hint) < 120, hint)
        check("the scheme check and the Compendium copy text share one guide line",
              page.evaluate("SCHEME_ONLY_A_GUIDE === COMPENDIUM_TEXT_FOOT && SCHEME_ONLY_A_GUIDE.startsWith('Colours on a screen are only a guide')"))
        check("the Compendium's 'Pick a group above' line is gone", "Pick a group above" not in app and "function groupNone" not in app)

        # ---------- 3. Empty screens ----------
        print("\n--- 3. The empty screens ---")
        empty(page)
        e.main_tab(page, "units")
        check("Units: 'No units yet.' with Paste army list and Import CSV right there",
              page.inner_text("#units-empty").startswith("No units yet.") and page.locator("#units-empty #empty-wh").count() == 1 and page.locator("#units-empty #empty-csv").count() == 1,
              page.inner_text("#units-empty"))
        e.main_tab(page, "recipes")
        e.recipe_view(page, "recipes")
        check("Recipes: 'No recipes yet.'", page.locator("#recipe-list li.empty", has_text="No recipes yet.").count() == 1, page.inner_text("#recipe-list"))
        e.recipe_view(page, "palette")
        check("Your Palette: 'No paints yet.'", page.inner_text("#paint-list").strip() == "No paints yet.", page.inner_text("#paint-list"))
        e.recipe_view(page, "shopping")
        check("Shopping: 'Nothing to buy.'", "Nothing to buy." in page.inner_text("#view-recipes"))

        # ---------- 4. The newer cards ----------
        print("\n--- 4. The v56 to v58 cards still work ---")
        e.fresh(page)
        e.main_tab(page, "recipes")
        e.recipe_view(page, "recipes")
        check("a brand-new start shows the examples card with Clear examples and Keep them",
              page.locator("#examples-card-recipes .clear-recipe-examples").count() == 1 and page.locator("#examples-card-recipes .keep-recipe-examples").count() == 1)
        page.click("#examples-card-recipes .keep-recipe-examples")
        page.wait_for_timeout(300)
        # The status line on a card only shows once some paint has a status (v50), so give one real paint a status.
        page.evaluate("() => { applyPaintStatus(findOrAddPaint('Test Paints', 'Real Blue', '#2244aa'), 'owned'); render(); }")
        status = page.evaluate("() => [...document.querySelectorAll('#recipe-list .recipe-status')].map(s => s.textContent)")
        check("after Keep them, an example-only recipe still says Uses example paints (v58)", "Uses example paints" in status, status)
        check("made-up paints are still kept off the shopping list (v58)",
              not any(n.startswith("Example ") for n in page.evaluate("() => shoppingItems().map(i => i.paint.name)")))
        check("the Save a backup? card is still built (v57)", "backup-nudge-save" in app and page.locator("#backup-nudge").count() == 1
              and "Save a backup?" in (page.text_content("#help-backup-nudge") or ""))

        # ---------- 5. Safety ----------
        print("\n--- 5. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
