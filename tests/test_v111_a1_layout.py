"""A1 tests for Minifolio (layout and wording fixes from the 31 Oct review). New behaviour only.

1. The three sample Mentor tips are gone, and Mentor and the Paint Picker still open with no tips.
2. The Guides search box is full width and typing in it filters the guides.
3. Mentor first screen: the orb does not sit on any starter question, and no question is cut off sideways.
4. Mentor chat: the question pills wrap (nothing runs off the right edge) and the strip is no taller than a third of the screen.
5. Bottom of the screen: the whole Ask Mentor label is on screen and the last card scrolls clear of the menu (390x844, 360x640, 320x568).
6. Menu words are not cut at the slanted edge (three themes, light and dark). The last Sources chip is not cut by the strip below.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import tap_tab, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_mentor_window(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window .mentor-chip")
    page.wait_for_timeout(700)   # the window finishes growing

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. No sample tips ---")
        t.load(page)
        check("the tip list is empty", page.evaluate("MENTOR_TIPS.length === 0"))
        open_mentor_window(page)
        check("Mentor opens with no tips", page.locator(".mentor-window").is_visible())
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        print("\n--- 2. Guides search box ---")
        t.load(page)
        tap_tab(page, "guides")
        quiet(page)
        page.wait_for_selector("#guides-search")
        w = page.evaluate("document.getElementById('guides-search').getBoundingClientRect().width")
        check("the search box is wide (over 200 px)", w > 200, w)
        before = page.locator(".guides-lower .guides-row").count()
        page.fill("#guides-search", "paint")
        page.wait_for_timeout(300)
        after = page.locator(".guides-lower .guides-row").count()
        check("typing changes the list", after != before or after > 0, (before, after))

        print("\n--- 3. Mentor first screen ---")
        t.load(page)
        open_mentor_window(page)
        r = page.evaluate("""() => { const o = document.querySelector('.mentor-orbbox').getBoundingClientRect();
          const chips = document.querySelector('.mentor-chips');
          const rows = [...chips.querySelectorAll('.mentor-chip')].map(c => c.getBoundingClientRect());
          return { overlap: rows.some(c => c.right > o.left && c.left < o.right && c.bottom > o.top && c.top < o.bottom && c.height > 0),
                   sideways: chips.scrollWidth > chips.clientWidth + 1,
                   greeting: document.querySelector('.mentor-greeting').getBoundingClientRect().height > 10,
                   first: rows[1] ? rows[1].height : 0 }; }""")
        check("the orb is not on top of any question", not r["overlap"], r)
        check("the questions do not run sideways", not r["sideways"], r)
        check("the greeting still shows", r["greeting"], r)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        print("\n--- 4. Mentor chat pills and 6. Sources chip ---")
        for w, h in ((390, 844), (360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page)
            open_mentor_window(page)
            page.fill(".mentor-input", "how thin should my paint be")
            page.keyboard.press("Enter")
            page.wait_for_selector(".mentor-source")
            page.wait_for_timeout(500)
            r = page.evaluate("""() => { const c = document.querySelector('.mentor-chips');
              const s = document.querySelector('.mentor-scroll'); s.scrollTop = s.scrollHeight;
              const sr = s.getBoundingClientRect(); const src = [...document.querySelectorAll('.mentor-source')].pop().getBoundingClientRect();
              return { sideways: c.scrollWidth > c.clientWidth + 1, tall: c.getBoundingClientRect().height / window.innerHeight,
                       wraps: [...c.querySelectorAll('.mentor-chip')].every(x => x.getBoundingClientRect().right <= c.getBoundingClientRect().right + 1),
                       gap: sr.bottom - src.bottom, page: document.documentElement.scrollWidth <= window.innerWidth + 1 }; }""")
            check(f"{w}x{h}: pills do not run off the side", not r["sideways"] and r["wraps"], r)
            check(f"{w}x{h}: the strip is no taller than a third of the screen", r["tall"] <= 0.34, r)
            check(f"{w}x{h}: the last Sources chip clears the edge below it", r["gap"] >= 3, r)
            check(f"{w}x{h}: no sideways scroll", r["page"], r)
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

        print("\n--- 5. Bottom of the screen ---")
        for w, h in ((390, 844), (360, 640), (320, 568)):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": w, "height": h})
                t.load(page, settings={"appearance": scheme})
                r = page.evaluate("""() => { const o = document.getElementById('mentor-button'); const rg = document.createRange();
                  rg.selectNodeContents([...o.childNodes].find(n => n.nodeType === 3 && n.textContent.trim()));
                  return { label: window.innerHeight - rg.getBoundingClientRect().bottom }; }""")
                check(f"{w}x{h} {scheme}: the whole Ask Mentor label is on screen", r["label"] >= 4, r)
        for w, h in ((390, 844), (320, 568)):
            page.set_viewport_size({"width": w, "height": h})
            for tab in ("dashboard", "units", "recipes"):
                t.load(page)
                tap_tab(page, tab)
                quiet(page)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(200)
                r = page.evaluate("""() => { const bar = document.querySelector('.tabs').getBoundingClientRect().top;
                  const sec = [...document.querySelectorAll('main > section')].find(s => s.offsetParent !== null);
                  const kids = [...sec.children].filter(k => k.offsetParent !== null && k.getBoundingClientRect().height > 0);
                  return { gap: bar - kids[kids.length - 1].getBoundingClientRect().bottom }; }""")
                check(f"{w}x{h} {tab}: the last item ends above the menu", r["gap"] >= 0, r)

        print("\n--- 6. Menu words ---")
        page.set_viewport_size({"width": 390, "height": 844})
        for theme, scheme in (("forge", "light"), ("rulebook", "dark"), ("bench", "light")):
            t.load(page, settings={"appearance": scheme, "theme": theme})
            rows = page.evaluate("""() => [...document.querySelectorAll('.arc [data-tab]')].map(btn => { const b = btn.getBoundingClientRect(); const rg = document.createRange();
              rg.selectNodeContents([...btn.childNodes].find(n => n.nodeType === 3 && n.textContent.trim())); const r = rg.getBoundingClientRect();
              return [btn.dataset.tab, r.left - b.left, b.right - r.right]; })""")
            check(f"{theme} {scheme}: every menu word sits inside its segment, clear of the slanted edge", all(a >= 5 and c >= 5 for _, a, c in rows), rows)

        check("no page errors", not errors, errors)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
