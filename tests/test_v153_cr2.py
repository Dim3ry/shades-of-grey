"""CR2 tests for Minifolio (the Thanks section on About, under Credits). New behaviour only:
1. The section shows; the intro line and the small print match word for word; the fold button is closed by default and 44 px tall.
2. Two groups, YouTube (18) and Websites (7), each sorted A to Z ignoring a leading "The"; every link is https and opens safely in a new tab.
3. The list stays hidden while THANKS is empty; a name with <b> in it shows as text.
4. 390x844 and 360x640, dark and light, fold open: no sideways scroll and every link at least 44 px tall.
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

INTRO = "Mentor's advice was shaped by learning from painters and creators who generously share what they know. Go and check them out below."
SMALL = "Listed as thanks only. No creator is affiliated with or endorses Minifolio."

def key(n):
    n = n.lower()
    return n[4:] if n.startswith("the ") else n

def go(page, w=390, h=844, theme=None):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, settings={"examplesChecked": True, **({"appearance": theme} if theme else {})}, launch=True)
    page.click('.tabs button[data-tab="guides"]')
    wait_settled(page)
    page.click('#more-seg button[data-page="about"]')
    wait_settled(page)
    page.click('#about-credits-link')
    wait_settled(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        go(page)

        print("\n--- 1. Wording and fold ---")
        check("the Thanks section shows with heading Thanks", page.locator("#credits-thanks h3").inner_text() == "Thanks")
        ps = page.locator("#credits-thanks > p")
        check("intro line word for word", ps.first.inner_text() == INTRO, ps.first.inner_text())
        check("small print word for word, under the list", ps.last.inner_text() == SMALL and page.evaluate(
            "() => { const f = document.querySelector('#credits-thanks details'), s = document.querySelector('#credits-thanks > p:last-child'); return !!(f.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING); }"), ps.last.inner_text())
        check("the fold is closed by default and its button reads Show all", page.evaluate(
            "() => { const f = document.querySelector('#credits-thanks details'); return !f.open && f.querySelector('summary').textContent.trim() === 'Show all'; }"))
        h = page.evaluate("() => document.querySelector('#credits-thanks summary').getBoundingClientRect().height")
        check("the fold button is at least 44 px tall", h >= 43.5, h)
        page.focus("#credits-thanks summary")
        page.keyboard.press("Enter")
        check("the keyboard opens it", page.evaluate("() => document.querySelector('#credits-thanks details').open"))
        page.keyboard.press("Space")
        check("and closes it", page.evaluate("() => !document.querySelector('#credits-thanks details').open"))
        page.click("#credits-thanks summary")
        check("a tap opens it", page.evaluate("() => document.querySelector('#credits-thanks details').open"))

        print("\n--- 2. Groups, order, links ---")
        data = page.evaluate("() => [...document.querySelectorAll('#credits-thanks .thanks-group')].map(g => [g.textContent, [...g.nextElementSibling.querySelectorAll('a')].map(a => [a.textContent, a.href, a.target, a.rel])])")
        check("two groups, YouTube then Websites", [d[0] for d in data] == ["YouTube", "Websites"], [d[0] for d in data])
        check("18 YouTube and 7 website entries", [len(d[1]) for d in data] == [18, 7], [len(d[1]) for d in data])
        for g, rows in data:
            names = [r[0] for r in rows]
            check(f"{g} is alphabetical, ignoring a leading The", names == sorted(names, key=key), names)
        links = [r for d in data for r in d[1]]
        check("every link is https, opens in a new tab, noopener noreferrer", all(r[1].startswith("https://") and r[2] == "_blank" and r[3] == "noopener noreferrer" for r in links))
        check("the Painting Phase sits under P and the Painter's Portal under P", [r[0] for r in data[0][1]][8] == "The Painting Phase" and [r[0] for r in data[1][1]][4].startswith("The Painter"))
        check("each name is a plain link, one per row", page.evaluate("() => [...document.querySelectorAll('#credits-thanks li')].every(li => li.children.length === 1 && li.firstElementChild.tagName === 'A')"))
        check("no creator is named anywhere else in the app", page.evaluate(
            "() => !/Ninjon|Miniac|Zumikito|Trovarion/.test([...document.querySelectorAll('#view-help, #view-guides, #mentor-window')].map(e => e.textContent).join(' '))"))

        print("\n--- 3. Empty list and text-only names ---")
        for body, label in (("[]", "empty"), ('[{ group: "YouTube", name: "A <b>Bold</b> One", link: "https://example.com/a" }]', "bold")):
            c2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
            p2 = c2.new_page()
            p2.on("pageerror", lambda x: errors.append(str(x)))
            def swap(route, body=body):
                r = route.fetch()
                route.fulfill(response=r, body=re.sub(r"const THANKS = \[.*?\n    \];", lambda m: "const THANKS = " + body + ";", r.text(), count=1, flags=re.S))
            p2.route(re.compile(r".*/app\.js.*"), lambda route, request, f=swap: f(route))
            go(p2)
            if label == "empty":
                check("empty list: no Thanks section at all", p2.locator("#credits-thanks").evaluate("e => e.offsetParent === null && e.children.length === 0") and "Thanks" not in p2.inner_text("#view-credits"))
            else:
                p2.click("#credits-thanks summary")
                check("a name containing <b> shows as text", p2.locator("#credits-thanks a").inner_text() == "A <b>Bold</b> One" and p2.locator("#credits-thanks b").count() == 0)
            c2.close()

        print("\n--- 4. Small screens, dark and light ---")
        for w, hh in [(390, 844), (360, 640)]:
            for theme in ("dark", "light"):
                go(page, w, hh, theme)
                page.click("#credits-thanks summary")
                r = page.evaluate("() => [document.documentElement.scrollWidth <= window.innerWidth, Math.min(...[...document.querySelectorAll('#credits-thanks a')].map(a => a.getBoundingClientRect().height)),"
                                  " getComputedStyle(document.body).backgroundColor.match(/\\d+/g).slice(0, 3).reduce((a, b) => a + +b, 0)]")
                check(f"{w}x{hh} {theme}: no sideways scroll, every link 44 px or more", r[0] and r[1] >= 43.5 and ((r[2] < 300) == (theme == "dark")), r)   # r[2]: page colour total, low = dark
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
