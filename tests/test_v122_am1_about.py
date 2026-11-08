"""AM1 tests for Minifolio (About, Mission and the start-page tagline). New behaviour only:
1. Tools and Settings has an About page, first in the switch, with the two headings and the agreed wording, straight text only.
2. The start page line reads "Track. Paint. Learn." (small capitals, muted theme colour) and the old line is gone.
3. The tagline shows on the start page only; it hangs under the name without crowding the circle, and hides on screens under 700 px high.
4. The tagline is readable (4.5 to 1) in light and dark in every theme.
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

ABOUT = "Minifolio is a hobby tracker made by a nerd, for nerds. It began as one painter’s side project to track their own models and learn to code, and it grew arms, legs and a few tentacles. It’s still mostly one person, so thanks for your patience."
MISSION = "To give every painter a mentor in their pocket: a place to track your progress, get advice, and find the right colours."
TAGLINE = "Track. Paint. Learn."
OLD_LINE = "Track your miniature painting"
UNIT = {"id": 1, "name": "Squad", "hobby": "40K", "stage": 1, "count": 5, "added": "2026-10-01", "log": [["2026-10-01", 1]]}

# the tagline's colour against the page behind it, as drawn (the page background, with the card colour as a fallback)
CONTRAST = """() => { const lum = (c) => { const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
    const fg = getComputedStyle(document.getElementById('start-line')).color, bg = getComputedStyle(document.body).backgroundColor;
    const a = lum(fg), b = lum(bg); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }"""

def start(page, w=390, h=844, **settings):
    page.set_viewport_size({"width": w, "height": h})
    t.load(page, units=[UNIT], settings=dict({"examplesChecked": True}, **settings), launch=True)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. About and Mission ---")
        start(page)
        page.click('.tabs button[data-tab="guides"]')
        wait_settled(page)
        labels = page.evaluate("() => [...document.querySelectorAll('#more-seg button')].map(b => b.textContent.trim())")
        check("About is the first page in the Tools and Settings switch", labels[0] == "About", labels)
        page.click('#more-seg button[data-page="about"]')
        wait_settled(page)
        heads = page.evaluate("() => [...document.querySelectorAll('#view-about h2')].map(h => h.textContent.trim())")
        paras = page.evaluate("() => [...document.querySelectorAll('#view-about p')].map(p => p.textContent.trim())")
        check("two headings: About and Mission", heads == ["About", "Mission"], heads)
        check("the About text is exact", paras[:1] == [ABOUT], paras[:1])
        check("the Mission text is exact", paras[1:2] == [MISSION], paras[1:2])
        # CR1: About now has one plain Credits button (#about-credits-link); nothing else is allowed in the card
        # LP1: About also carries the rights line (a third paragraph, #about-rights, with "their own licences" as a second button) and one plain
        # link to the privacy page (#about-privacy-link, the only a allowed). The AM1 paragraphs checked above stay exact; the rest is still plain text.
        check("straight text only: the two paragraphs, the rights line, the Credits button and one privacy link, nothing else in the card",
              len(paras) == 3 and page.locator("#view-about :is(img, svg, ul, h3, .pill, .badge)").count() == 0
              and page.locator("#view-about a").count() == 1 and page.locator("#about-privacy-link").count() == 1
              and page.locator("#view-about button").count() == 2 and page.locator("#about-credits-link").count() == 1 and page.locator("#about-rights-credits").count() == 1)
        check("the About page is the only page showing, and it is lit as selected",
              page.is_visible("#view-about") and page.locator("main > section:visible").count() == 1
              and page.get_attribute('#more-seg [data-page="about"]', "aria-selected") == "true")
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)
        check("leaving About closes it cleanly", not page.is_visible("#view-about") and page.is_visible("#view-help"))

        print("\n--- 2. The tagline ---")
        start(page)
        check("the start page line reads the tagline", page.text_content("#start-line").strip() == TAGLINE, page.text_content("#start-line"))
        look = page.evaluate("() => { const s = getComputedStyle(document.getElementById('start-line')); return [s.textTransform, parseFloat(s.letterSpacing) > 1, s.animationName, s.transitionDuration]; }")
        check("capitals, wide spacing, no animation", look[0] == "uppercase" and look[1] and look[2] == "none" and look[3] == "0s", look)
        check("the old line is gone from the start page", OLD_LINE not in page.inner_text("body") and OLD_LINE not in page.content().split("<meta name=\"description\"")[0].split("<body")[-1])
        r = page.evaluate("() => { const l = document.getElementById('start-line').getBoundingClientRect(), n = document.getElementById('home-button').getBoundingClientRect(), m = document.getElementById('mentor-button').getBoundingClientRect(); return [Math.abs((l.left + l.width / 2) - window.innerWidth / 2), l.top - n.bottom, m.top - l.bottom]; }")
        check("centred, just under the name, clear of the circle at 390x844", r[0] < 2 and 0 <= r[1] < 30 and r[2] > 0, r)

        print("\n--- 3. Only on the start page ---")
        shown = []
        for tab in ["dashboard", "units", "recipes", "guides"]:
            page.evaluate("(t) => document.querySelector('.tabs button[data-tab=' + t + ']').click()", tab)
            wait_settled(page)
            shown.append(page.evaluate("() => { const e = document.getElementById('start-line'); return e.offsetParent !== null && e.getBoundingClientRect().height > 0; }"))
        check("hidden on every section", not any(shown), shown)
        others = page.evaluate("""(T) => [...document.querySelectorAll('main > section, nav, #version-tag')].filter(e => e.textContent.includes(T)).map(e => e.id || e.tagName)""", TAGLINE)
        check("the tagline text is on no other screen or in the bar", others == [], others)
        title = page.title()
        check("not in the page title", TAGLINE not in title and "Track. Paint" not in title, title)

        print("\n--- 4. Small screens ---")
        for w, h in [(360, 640), (360, 720), (320, 568)]:
            start(page, w, h)
            vis = page.evaluate("() => getComputedStyle(document.getElementById('start-line')).display !== 'none'")
            arc = page.evaluate("() => { const r = document.getElementById('mentor-button').getBoundingClientRect(); return [r.left >= 0 && r.right <= window.innerWidth, r.top >= 0 && r.bottom <= window.innerHeight]; }")
            if h < 700:
                check(f"{w}x{h}: the tagline is hidden and the circle fits", not vis and all(arc), [vis, arc])
            else:
                lt = page.evaluate("() => { const l = document.getElementById('start-line').getBoundingClientRect(); const top = Math.min(...[...document.querySelectorAll('.arc [data-tab]')].map(b => b.getBoundingClientRect().top)); return top - l.bottom; }")
                check(f"{w}x{h}: the tagline shows and does not touch the circle", vis and lt >= 0 and all(arc), [vis, lt, arc])
            check(f"{w}x{h}: no sideways scroll", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        start(page, 320, 640)
        page.click('.tabs button[data-tab="guides"]')
        wait_settled(page)
        sw = page.evaluate("""() => [...document.querySelectorAll('#more-seg button')].map(b => [b.scrollWidth <= b.clientWidth + 1, b.getBoundingClientRect().height])""")
        check("320 px: the five switch labels fit and are 44 px high or more", all(ok and h >= 44 for ok, h in sw), sw)

        print("\n--- 5. Contrast in every theme ---")
        bad = []
        for theme in ["classic", "parchment", "forge", "bench"]:   # TH1: Blueprint and Rulebook were removed, so four themes are left
            for mode in ["light", "dark"]:
                start(page, theme=theme, appearance=mode)
                c = page.evaluate(CONTRAST)
                if c < 4.5:
                    bad.append((theme, mode, round(c, 2)))
        check("the tagline is 4.5 to 1 or better in light and dark in every theme", not bad, bad)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
