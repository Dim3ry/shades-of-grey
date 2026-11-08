"""CR1 tests for Minifolio (the Credits page). New behaviour only:
1. Credits sits straight after About in the Tools and Settings switch, and About links to it.
2. Every font family the app loads is listed with a licence; the pot-label reader and the paint list are listed too.
3. Every licence link points to a file that ships with the app (and the service worker saves them) or to an https address.
4. The Thanks section is not drawn while the THANKS list is empty; with two fake entries (added here, never committed) it shows
   the heading, the exact line, plain-text names and https links only.
5. The page fits 390, 360 and 320 px wide with no sideways scroll, and links are at least 44 px tall.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# CR2: the intro line is new wording, entries need a group, and the list is no longer empty (the real Thanks list is in; the full wording and
# list are checked in test_v153_cr2.py). The fake list below still replaces the real one, to prove names are text and bad links are left out.
LINE = "Mentor's advice was shaped by learning from painters and creators who generously share what they know. Go and check them out below."
FAKE = '[{ group: "YouTube", name: "Painter <b>One</b>", link: "https://example.com/one" }, { group: "YouTube", name: "Painter Two", link: "https://example.com/two" }, ' \
       '{ group: "YouTube", name: "Bad Link", link: "http://example.com/bad" }, { group: "YouTube", name: "Script Link", link: "javascript:alert(1)" }]'

def go(page, w=390, h=844):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings={"examplesChecked": True}, launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click('#more-seg button[data-page="about"]')
    wait_settled(page)

def main():
    errors = []
    html = t.read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Placement ---")
        go(page)
        labels = page.evaluate("() => [...document.querySelectorAll('#more-seg button')].map(b => b.textContent.trim())")
        # FB3: Credits is no longer a sub-tab; it is a section at the foot of About, so the switch has five pages
        check("the switch has no Credits tab (it is a section of About now)", labels == ["About", "Guides", "Settings", "How it works", "Updates"], labels)
        links = page.locator("#view-about #about-credits-link")
        check("About has one Credits link", links.count() == 1)
        links.click()
        wait_settled(page)
        check("it scrolls to the Credits section on About, lit as selected", page.is_visible("#view-credits")
              and page.get_attribute('#more-seg [data-page="about"]', "aria-selected") == "true"
              and page.evaluate("() => document.querySelector('#view-credits h2').getBoundingClientRect().top < innerHeight"))

        print("\n--- 2. Everything third-party is listed ---")
        families = sorted(set(re.findall(r"@font-face \{ font-family: '([^']+)'", html)))
        families = [f for f in families if not f.endswith(" Fallback") and not f.endswith(" Theme Name")]
        names = page.evaluate("() => [...document.querySelectorAll('#credits-fonts li strong')].map(e => e.textContent.trim())")
        check("every font family the app loads is on the page", set(families) == set(names), (families, names))
        rows = page.evaluate("() => [...document.querySelectorAll('#view-credits .credits-list li')].map(li => [li.querySelector('strong').textContent, li.querySelector('.cr-by').textContent.trim(), li.querySelector('a').textContent.trim()])")
        check("every row has a name, a maker and a licence name", all(all(c for c in r) for r in rows) and len(rows) == len(families) + 4, rows)
        check("the pot-label reader and the paint list are listed with a licence",
              page.locator("#credits-reader a").first.inner_text() == "Apache License 2.0" and page.locator("#credits-paints a").inner_text() == "MIT License")  # LC1: the reader list now has three links, so the first (Tesseract) is checked
        heads = page.evaluate("() => [...document.querySelectorAll('#view-credits h3')].map(h => h.textContent.trim())")
        check("small headings group the rows", heads == ["Fonts", "Pot-label reader", "Paint list", "Thanks"], heads)   # CR2: Thanks is drawn now

        print("\n--- 3. Licence links ---")
        hrefs = page.evaluate("() => [...document.querySelectorAll('#view-credits a')].map(a => [a.getAttribute('href'), a.target, a.rel])")
        ok = True
        for href, target, rel in hrefs:
            if href.startswith("https://"):
                continue
            # LP1: "privacy" is the host's clean address for privacy.html, a file that ships with the app
            ok = ok and os.path.isfile(os.path.join(t.ROOT, "privacy.html" if href == "privacy" else href))
        check("every link is an https address or a file that ships with the app", ok, hrefs)
        check("links open in a new tab safely", all(h[1] == "_blank" and "noopener" in h[2] and "noreferrer" in h[2] for h in hrefs), hrefs)

        print("\n--- 4. Thanks ---")
        # CR2: the list is filled, so the section shows (it stays hidden only while the list is empty; checked below with an empty list)
        check("filled list: the Thanks section is drawn", page.locator("#credits-thanks h3").inner_text() == "Thanks")
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        p2 = ctx2.new_page()
        p2.on("pageerror", lambda x: errors.append(str(x)))
        p2.route(re.compile(r".*/app\.js.*"), lambda route: route.fulfill(
            response=route.fetch(), body=route.fetch().text().replace(re.search(r"const THANKS = \[.*?\n    \];", route.fetch().text(), re.S).group(0), "const THANKS = " + FAKE + ";", 1)))
        go(p2)
        p2.click('#about-credits-link')   # FB3
        wait_settled(p2)
        check("with entries: heading Thanks", p2.locator("#credits-thanks h3").inner_text() == "Thanks")
        check("the line is word for word", p2.locator("#credits-thanks p").first.inner_text() == LINE, p2.locator("#credits-thanks p").first.inner_text())   # CR2: first p; the small print is the second
        got = p2.evaluate("() => [...document.querySelectorAll('#credits-thanks a')].map(a => [a.textContent, a.href, a.target, a.rel])")
        # CR2: the real list is replaced by the fake one with a regex now (the real list has many lines)
        check("only the two https entries are drawn, names as plain text",
              [g[0] for g in got] == ["Painter <b>One</b>", "Painter Two"] and p2.locator("#credits-thanks b").count() == 0, got)
        check("each is a safe new-tab link", all(g[2] == "_blank" and g[3] == "noopener noreferrer" and g[1].startswith("https://") for g in got), got)
        ctx2.close()

        print("\n--- 5. Small screens and keyboard ---")
        for w, h in [(390, 844), (360, 640), (320, 568)]:
            go(page, w, h)
            page.click('#about-credits-link')   # FB3: the section is on About
            wait_settled(page)
            r = page.evaluate("() => [document.documentElement.scrollWidth <= window.innerWidth, Math.min(...[...document.querySelectorAll('#view-credits a, #more-seg button')].map(a => a.getBoundingClientRect().height))]")
            check(f"{w}x{h}: no sideways scroll, links and switch at least 44 px tall", r[0] and r[1] >= 43.5, r)
        page.focus('#about-credits-link')   # FB3
        for _ in range(8):
            page.keyboard.press("Tab")
            if page.evaluate("() => document.activeElement.matches('#credits-fonts a')"):
                break
        out = page.evaluate("() => { const s = getComputedStyle(document.activeElement); return [s.outlineStyle, parseFloat(s.outlineWidth)]; }")
        check("a link shows a focus outline", out[0] != "none" and out[1] >= 2, out)
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
