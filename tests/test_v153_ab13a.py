"""AB13a test for Minifolio (Guides entries: no numbers on entry pages, glossary link on the Guides home, two answer leads). New behaviour only."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

WASH = "A wash runs into the recesses. A glaze sits on top and tints."
EYES = "Paint the socket dark. Add an off-white eyeball with a dark rim. Put a pupil on, touching the lids. Add a tiny glint if you like."

def main():
    d = json.load(open(os.path.join(ROOT, "knowledge-base", "data", "k2-techniques.json"), encoding="utf-8"))
    by = {g["key"]: g for g in d["guides"]}
    check("wash or glaze lead is the approved pair", by["wash-vs-glaze"]["summary"] == WASH, by["wash-vs-glaze"]["summary"])
    check("eyes lead is the steps in order, within 140 characters", by["painting-eyes"]["summary"] == EYES and len(EYES) <= 140)
    check("both entries keep their title and body", by["wash-vs-glaze"]["title"] == "Wash or glaze" and len(by["wash-vs-glaze"]["body"]) == 7
          and by["painting-eyes"]["title"] == "Painting eyes on faces" and len(by["painting-eyes"]["body"]) == 8)
    gd = open(os.path.join(ROOT, "guides-data.js"), encoding="utf-8").read()
    check("guides-data.js carries both leads and not the old ones", WASH in gd and EYES in gd and "is meant to run into recesses" not in gd and "Dark socket, off-white" not in gd)

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
            page.wait_for_function("() => typeof guideGroupsOf === 'function'")
            tap_tab(page, "guides")
            wait_settled(page)
            g = page.locator(".guides-glossary-link")
            check(f"{w}px: the glossary link is on the Guides home, named as the entry, 44 px or more",
                  g.count() == 1 and g.inner_text() == "Common hobby and painting terms" and g.bounding_box()["height"] >= 44, g.count())
            check(f"{w}px: no sideways scroll on the Guides home", not page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"))
            g.click()
            page.wait_for_selector(".guides-entry")
            check(f"{w}px: the glossary link opens the glossary entry, and Back returns to Guides",
                  page.get_attribute(".guides-entry", "id") == "guide-painting-terms-glossary" and page.inner_text("#guides-back").startswith("Back"))
            for key in ("painting-terms-glossary", "wash-vs-glaze", "painting-eyes"):   # a sample of entries, one of them numbered in the lists
                page.evaluate("(k) => openGuide(k)", key)
                page.wait_for_selector(f"#guide-{key}")
                check(f"{w}px: {key} shows no number on its page",
                      page.locator(".guides-entry .guides-num").count() == 0 and page.locator(".guides-entry .guides-entry-head").count() == 0
                      and not page.evaluate("() => /\\b\\d+\\.\\d+(\\.\\d+)?\\b/.test(document.querySelector('.guides-entry h3').parentElement.textContent.slice(0, 80))"))
            page.evaluate("(k) => openGuide(k)", "wash-vs-glaze")
            page.wait_for_selector("#guide-wash-vs-glaze")
            check(f"{w}px: the entry page for the wash lead still has its text and no sideways scroll",
                  page.locator(".guides-entry p").count() >= 8 and not page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"))
            ctx.close()
        # the lists keep their numbers
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
        page.wait_for_function("() => typeof guideGroupsOf === 'function'")
        tap_tab(page, "guides")
        page.click('.guides-cats [data-cat="techniques"]')
        wait_settled(page)
        page.click(".guides-main .guides-row >> nth=0")
        wait_settled(page)
        check("a topic group's rows still carry their numbers", page.locator(".guides-main .guides-num").count() > 0)
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
