"""AB3 tests for Minifolio (the Help page, from the approved AI-tells items). New behaviour only:
1. Help no longer calls Dark the usual look; Match my phone is where the app starts.
2. "The basics": four plain bullets (no numbered list), the Mentor line says it looks things up in the guides.
3. Mentor's "is this AI" answer uses the new line.
4. No card around the "How to use Minifolio" heading.
5. The Mentor paragraph in Help is three points; the version history sentences are gone; the looks sentence sits in Appearance.
6. Help's human lines are still there.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=[])
        page.evaluate("() => document.querySelector('#more-seg button[data-page=\"help\"]') && document.querySelector('#more-seg button[data-page=\"help\"]').click()")
        page.wait_for_timeout(300)
        text = page.evaluate("() => document.getElementById('view-help').textContent")
        flat = " ".join(text.split())

        print("\n--- 1. Appearance ---")
        ap = " ".join(page.evaluate("() => document.getElementById('help-appearance').textContent").split())
        check("Dark is not called the usual look", "Dark (the usual look)" not in ap and "Dark</strong> (the usual look" not in ap, ap[:200])
        check("Match my phone is named as where you start", "Match my phone (where you start)" in ap, ap[:300])

        print("\n--- 2. The basics ---")
        check("heading is The basics", page.inner_text("#help-five h2").strip() == "The basics")
        items = page.eval_on_selector_all("#help-five ul > li", "els => els.map(e => e.textContent.trim())")
        check("four bullets", len(items) == 4, items)
        check("no numbered list", page.locator("#help-five ol").count() == 0)
        check("Mentor line", "Mentor looks things up in the guides on your phone. Works offline." in items, items)
        check("Colour Lab is folded into the Painting line", "Colour Lab suggests paints" in items[1], items)

        print("\n--- 3. Mentor's answer ---")
        eng = t.read("mentor-engine.js")
        check("engine line changed", "It looks things up in the guides on this phone and works offline." in eng and "It isn't AI" not in eng)

        print("\n--- 4. The heading above the topics ---")
        check("h2 sits straight in the page, not in a card", page.evaluate("() => { const h = [...document.querySelectorAll('#view-help > h2')].map(e => e.textContent.trim()); return h.join('|'); }") == "How to use Minifolio")
        check("no card holds only a heading", page.evaluate("() => [...document.querySelectorAll('#view-help .card')].every(c => c.children.length > 1)"))

        print("\n--- 5. Mentor paragraph and history ---")
        mp = " ".join(page.evaluate("() => document.getElementById('help-mentor').textContent").split())
        check("three points: tap the circle, type or tap a question, a guide link opens the guide", "Tap the round Ask Mentor button." in mp and "Type a question" in mp and "a guide link opens that guide" in mp, mp)
        check("the Mentor paragraph is short", len(mp.split()) < 40, len(mp.split()))
        check("no version history in Help", "Up to v61" not in flat and "since v4" not in flat)
        check("Mentor look is in Appearance", "Mentor look" in ap)
        check("no bold Term: lead-ins in Dashboard or Models topics", page.locator("#view-help li > strong:first-child").filter(has_text="Track models separately:").count() == 0)

        print("\n--- 6. Human lines are still there ---")
        for line in ["my dark green scheme is an Armour recipe, a Trim recipe", "Got recipes in Google Keep, a phone note or a Reddit post?", "a typo twin like", "New phone? Save a backup on the old one", "Paste recipes from your notes"]:
            check("kept: " + line[:40], line in flat, line)

        check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
