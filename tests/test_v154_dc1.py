"""DC1 tests for Minifolio (George's 9 Nov decisions). New behaviour only:
1. Mentor: an everyday non-hobby question ("fix my car") gets the plain "I do not know that yet." with no chips; hobby questions are untouched.
2. Settings has no "What's sent" fold, and no note under the Counting visits switch.
3. Appearance and Themes starts folded every time Settings opens.
4. The "All rights reserved" line is in the app once (About), not in How it works.
(Item 5, "Why Done?", did not match anything in the app, so there is nothing to test.)
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ASK = """(qs) => qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
    return { q, kind: a.kind, lead: a.lead, chips: (a.suggestions || []).length + (a.choices || []).length + (a.didYouMean ? 1 : 0) }; })"""

def open_page(page, which, w=390, h=844):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings={"examplesChecked": True}, launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click(f'#more-seg button[data-page="{which}"]')
    wait_settled(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Mentor and off-topic words ---")
        open_page(page, "settings")
        a = {r["q"]: r for r in page.evaluate(ASK, ["fix my car", "how much tax do I pay", "who won the football", "best mortgage rates",
                                                     "how do I paint a grey cloak", "my brush is split", "what is a scheme"])}
        for q in ("fix my car", "how much tax do I pay", "who won the football", "best mortgage rates"):
            check(f"'{q}': plain do-not-know and no chips", a[q]["kind"] == "none" and a[q]["lead"] == "I do not know that yet." and a[q]["chips"] == 0, a[q])
        for q in ("how do I paint a grey cloak", "my brush is split", "what is a scheme"):
            check(f"'{q}' still gets an answer or chips as before", a[q]["kind"] == "answer" or a[q]["chips"] > 0, a[q])

        print("\n--- 2. What's sent is gone ---")
        text = page.evaluate("() => document.getElementById('view-settings').textContent")
        check("Settings has no 'What's sent' fold", "What's sent" not in text and page.locator('[aria-controls="more-counting"]').count() == 0)
        check("the Counting visits tick box and the Privacy link stay",
              page.locator("#count-visits").count() == 1 and page.locator("#settings-privacy-link").count() == 1)
        check("the privacy page says when a counting change takes effect",
              "A change takes effect the next time the app opens." in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "privacy.html"), encoding="utf-8").read())

        print("\n--- 3. Appearance and Themes starts folded ---")
        btn = page.locator("#card-fold-appearance-themes-button")
        check("folded when Settings first opens", btn.get_attribute("aria-expanded") == "false")
        btn.click()
        page.wait_for_selector("#card-fold-appearance-themes-panel:not([hidden])")
        page.click('.tabs button[data-tab="units"]')
        wait_settled(page)
        page.click('.tabs button[data-tab="guides"]')
        wait_settled(page)
        page.click('#more-seg button[data-page="settings"]')
        wait_settled(page)
        check("folded again after leaving Settings and coming back", btn.get_attribute("aria-expanded") == "false")
        check("opening it still works", (btn.click(), btn.get_attribute("aria-expanded"))[1] == "true")

        print("\n--- 4. One rights line ---")
        open_page(page, "about")
        check("About has the rights line once", page.locator("#about-rights").count() == 1 and page.inner_text("#view-about").count("All rights reserved") == 1)
        open_page(page, "help")
        page.evaluate("() => document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
        help_text = page.inner_text("#view-help")
        check("How it works has no rights line", "All rights reserved" not in help_text and page.locator("#help-rights").count() == 0)
        check("no errors in the page", not errors, errors[:2])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
