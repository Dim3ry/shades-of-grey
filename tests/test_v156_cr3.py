"""CR3 tests for Minifolio (Credits tidy). New behaviour only:
1. Fonts, Pot-label reader, Paint list and Thanks each fold, start closed, open and close by tap and by keyboard.
2. Thanks keeps its intro (new wording), the "Show all" fold (closed) and the small print; opening Credits again closes them all.
3. The Mission text has no link to Credits (the "their own licences" words stay as plain text); Help still has its link.
4. 390x844, 360x640 and 320x568, dark and light: no sideways scroll, fold buttons 44 px or more.
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

INTRO = "These creators inspired Minifolio. Thank you to them, and they're well worth checking out:"
FOLDS = "#view-credits .credits-fold"

def go(page, w=390, h=844, theme=None):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings={"examplesChecked": True, **({"appearance": theme} if theme else {})}, launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click('#more-seg button[data-page="about"]')
    wait_settled(page)

def states(page):
    # the fold's aria-expanded follows the native toggle event, which arrives a moment after the tap: wait for it to settle
    page.wait_for_function("() => [...document.querySelectorAll('#view-credits .credits-fold')].every(d => d.querySelector(':scope > summary').getAttribute('aria-expanded') === String(d.open))")
    return page.evaluate("() => [...document.querySelectorAll('#view-credits .credits-fold')].map(d => [d.querySelector(':scope > summary h3').textContent.trim(), d.open, d.querySelector(':scope > summary').getAttribute('aria-expanded')])")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        go(page)

        print("\n--- 1. Folds ---")
        st = states(page)
        check("four sections, in order", [s[0] for s in st] == ["Fonts", "Pot-label reader", "Paint list", "Thanks"], st)
        check("all start closed with aria-expanded false", all(s[1] is False and s[2] == "false" for s in st), st)
        check("About and Mission do not fold", page.locator("#view-about .about-card details").count() == 0)
        heights = page.evaluate("() => [...document.querySelectorAll('#view-credits .credits-fold > summary')].map(s => s.getBoundingClientRect().height)")
        check("each fold button is 44 px or more", all(h >= 43.5 for h in heights), heights)
        for i, name in enumerate(["Fonts", "Pot-label reader", "Paint list", "Thanks"][:3]):
            page.locator(f"{FOLDS} > summary").nth(i).click()
            s = states(page)[i]
            check(f"a tap opens {name}", s[1] is True and s[2] == "true", s)
            check(f"{name} content is visible when open", page.locator(f"{FOLDS}").nth(i).locator("li a").first.is_visible())
            page.locator(f"{FOLDS} > summary").nth(i).click()
            check(f"a second tap closes {name}", states(page)[i][1] is False)
        sm = page.locator(f"{FOLDS} > summary").nth(0)
        sm.focus()
        page.keyboard.press("Enter")
        check("Enter opens Fonts", states(page)[0][1] is True)
        page.keyboard.press("Space")
        check("Space closes Fonts", states(page)[0][1] is False)

        print("\n--- 2. Thanks ---")
        page.locator(f"{FOLDS} > summary").nth(3).click()
        check("Thanks opens by tap", states(page)[3][1] is True)
        check("the intro line is exact", page.locator("#credits-thanks .credits-fold > p").first.inner_text() == INTRO, page.locator("#credits-thanks .credits-fold > p").first.inner_text())
        check("Show all is there and closed", page.evaluate("() => { const f = document.querySelector('#credits-thanks .thanks-fold'); return !f.open && f.querySelector(':scope > summary').textContent.trim() === 'Show all' && f.querySelector(':scope > summary').getAttribute('aria-expanded') === 'false'; }"))
        check("the small print is still there", "Listed as thanks only" in page.locator("#credits-thanks .credits-fold > p.hint").inner_text())
        page.click("#credits-thanks .thanks-fold > summary")
        check("Show all opens the two groups", page.locator("#credits-thanks .thanks-group").count() == 2 and page.locator("#credits-thanks .thanks-group").first.is_visible())
        page.click('#more-seg button[data-page="settings"]')
        wait_settled(page)
        page.click('#more-seg button[data-page="about"]')
        wait_settled(page)
        check("coming back to About, every section is closed again", all(s[1] is False for s in states(page)) and not page.evaluate("() => document.querySelector('#credits-thanks .thanks-fold').open"), states(page))

        print("\n--- 3. No link from Mission to Credits ---")
        check("no Credits button or 'their own licences' link in the About card", page.locator("#view-about .about-card button").count() == 0 and page.locator("#about-credits-link, #about-rights-credits").count() == 0)
        check("the words 'their own licences' stay as plain text", "are used under their own licences." in page.inner_text("#about-rights"))
        check("the Privacy link stays", page.locator("#about-privacy-link").count() == 1)
        check("the Credits section is still on the page below", page.is_visible("#view-credits h2"))
        page.click('.tabs button[data-tab="guides"]')
        page.click('#more-seg button[data-page="help"]')
        page.evaluate("() => document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
        wait_settled(page)
        page.locator("#help-credits-link").scroll_into_view_if_needed()
        page.click("#help-credits-link")
        wait_settled(page)
        check("the Help link still opens About at Credits", page.is_visible("#view-about") and page.is_visible("#view-credits h2"))

        print("\n--- 4. Small screens, dark and light ---")
        for w, h in [(390, 844), (360, 640), (320, 568)]:
            for theme in ("dark", "light"):
                go(page, w, h, theme)
                page.evaluate("() => document.querySelectorAll('#view-credits details').forEach(d => d.open = true)")
                r = page.evaluate("() => [document.documentElement.scrollWidth <= window.innerWidth, Math.min(...[...document.querySelectorAll('#view-credits .credits-fold > summary')].map(s => s.getBoundingClientRect().height))]")
                check(f"{w}x{h} {theme}: all open, no sideways scroll, fold buttons 44 px or more", r[0] and r[1] >= 43.5, r)
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
