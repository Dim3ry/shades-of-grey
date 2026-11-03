"""LG1 tests for Minifolio (small legal tidy). New behaviour only:
1. Help > About has one plain link to the font licences, and the file it opens loads, with IM Fell English's real copyright line.
2. Help has one short safety line: general hobby tips, follow the maker's label.
3. The short unofficial note on the Updates page is checked in test_v18_1 (updated there for "or endorsed by").
4. A COPYRIGHT file at the repo root, and the README points to it.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import open_settings, wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    with open(os.path.join(HERE, "..", name), encoding="utf-8") as f:
        return f.read()

SAFETY = "Guides and Mentor give general hobby tips, not professional safety advice. Always follow the maker's label and safety sheet."

def main():
    print("--- Files ---")
    licences = read("fonts/LICENSES.md")
    fell = licences.split("## IM Fell English", 1)[1][:200]
    check("IM Fell English credits Igino Marini, not Google Inc.",
          "Copyright (c) 2010, Igino Marini" in fell and "Google Inc." not in fell, fell)
    cr = read("COPYRIGHT")
    check("COPYRIGHT: all rights reserved by George, code and knowledge base included",
          "George Atter-Dimery" in cr and "All rights reserved" in cr and "knowledge-base/" in cr, cr[:200])
    check("COPYRIGHT: the paint list and fonts are exceptions under their own licences",
          "LICENSE-paint-list.txt" in cr and "fonts/LICENSES.md" in cr)
    check("README points to COPYRIGHT", "`COPYRIGHT`" in read("README.md"))

    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.load(page, settings={"examplesChecked": True}, launch=True)
        open_settings(page)
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)

        print("\n--- Help > About: font licences link ---")
        page.evaluate("document.getElementById('about').open = true")
        link = page.locator("#about #about-fonts a")
        check("one font licences link in About", link.count() == 1 and page.locator("#about a[href='fonts/LICENSES.md']").count() == 1)
        check("the link reads Font licences and opens safely in a new tab",
              link.inner_text().strip() == "Font licences" and link.get_attribute("target") == "_blank"
              and "noopener" in (link.get_attribute("rel") or ""), link.inner_text())
        check("the link is visible", link.is_visible())
        res = page.request.get(t.BASE + "fonts/LICENSES.md")
        check("the licences file it opens loads", res.ok and "SIL Open Font License" in res.text(), res.status)

        print("\n--- Help: safety line ---")
        safety = page.locator("#help-safety")
        check("Help has the safety line once, with the agreed words",
              safety.count() == 1 and " ".join(safety.text_content().split()) == SAFETY, safety.text_content() if safety.count() else "")
        check("it sits with the Guides help", page.evaluate("document.getElementById('help-safety').previousElementSibling.id") == "help-guides")
        check("no sideways scroll at 360 px", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
