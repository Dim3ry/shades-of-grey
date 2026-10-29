"""v66 tests for Minifolio (chunk 3.5b-1: Similar paints, Your closest and the Best / Yours tabs).

What changed:
 The Similar paints pop-up gets a second card, Your closest: the nearest paints you own, for the same Lighter / Close / Darker target,
 with the fit words of the 3.4c rule. The paint itself, example and made-up paints and the not-a-colour list are left out.
 One card, not the same paint twice: if the top Best match is already yours, only Best match shows; if you own paints but none is a
 Good or Okay fit, Your closest shows one short line and no rows; if you own no paints, only Best match shows.
 Below 700 px the two cards are tabs (Best, Yours; arrow keys, aria-selected); from 700 px they sit side by side and the pop-up is wider.
 Swapping into a recipe step and the button on recipe steps come in the next part. No paint content file changed.

Checks:
1. Versions, the v66 Updates entry, Help line, no em dash.
2. Which cards show: empty collection, top match yours, nothing close, something close.
3. Your closest rows: nearest first, fit words, nothing left out that should be, no Add button, the paint itself and examples never shown.
4. Lighter / Darker move Your closest too.
5. Tabs on a phone: tab list, aria-selected, one tab stop, arrow keys, Home / End, one card at a time, panels named by their tab.
6. Side by side at 800 px and live when the window is resized; the pop-up is wider.
7. Escape, Back, focus return and the Tab trap with the tabs.
8. 390 px and 360 px, dark and light, tabs and side by side, and another theme: no sideways scroll, tap targets 44 px or more.
9. Content files unchanged, no network use, no page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, subprocess, sys
from playwright.sync_api import sync_playwright
from launch_helpers import quiet

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v39 as h

read, load, no_sideways = t.read, t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def P(id, brand, name, colour, **more):
    return dict({"id": id, "brand": brand, "name": name, "colour": colour}, **more)

SOURCE = P(1, "Test Paints", "Probe Source", "#3a6ea5", status="notowned")
OKAY = P(2, "Alpha Paints", "Owned Okay", "#4a7cb4", status="owned")        # a little different from the source, and yours
FAR = P(3, "Alpha Paints", "Owned Far", "#aa2222", status="owned")          # a different colour, and yours
TWIN = P(4, "Alpha Paints", "Owned Twin", "#3a6fa5", status="owned")        # almost the same colour, and yours
GHOST = P(5, "", "Ghost Owned", "#3a6ea6", status="owned", example=True)   # an example paint: never offered

FITS = ("Good fit", "Okay fit", "Poor fit", "Yours, poor fit")

def popup_open(page):
    return page.evaluate("() => !!document.querySelector('.similar-backdrop')")

def open_for(page, index=0):
    page.evaluate(f"() => openSimilarPaints(book.paints[{index}], null)")
    quiet(page)

def cards(page, paints):
    """What similarCards decides for the first paint: names of Best match, and Your closest (None, or a list of names)."""
    load(page, paints=paints)
    return page.evaluate("""() => { const c = similarCards(book.paints[0], 0);
        return { best: c.best.map(x => [x.paint.name, x.owned]), yours: c.yours ? c.yours.hits.map(x => [x.paint.name, x.quality, x.owned]) : null }; }""")

def rows_in(page, key):
    return page.evaluate(f"""() => [...document.querySelectorAll('#similar-card-{key} .similar-row')].map(li => ({{
        name: li.querySelector('.similar-name').childNodes[0].textContent,
        fit: li.querySelector('.similar-fit').textContent,
        own: !!li.querySelector('.similar-own'), add: !!li.querySelector('.similar-add') }}))""")

def visible(page, sel):
    return page.evaluate(f"() => {{ const e = document.querySelector('{sel}'); return !!e && e.offsetParent !== null; }}")

def tab_state(page):
    return page.evaluate("""() => [...document.querySelectorAll('.similar-tabs [role=tab]')].map(b =>
        [b.textContent, b.getAttribute('aria-selected'), b.tabIndex])""")

def main():
    errors, dialogs, requests = [], [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("http://localhost", "data:", "blob:")) else None)
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        load(page, paints=h.JUST_BLUE)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v66')")
        joined = " ".join(entry["changes"]) if entry else ""
        check("the entry names Your closest, Best match, tabs and side by side",
              all(w in joined for w in ["Your closest", "Best match", "tabs", "side by side"]), joined)
        help_text = page.evaluate("() => (document.getElementById('help-similar-paints') || {}).textContent || ''")
        check("Help describes Your closest, the Best and Yours tabs and side by side",
              all(w in help_text for w in ["Your closest", "Best", "Yours", "side by side"]), help_text)
        check("no em dash in the Help line", "—" not in help_text)

        # ---------- 2. Which cards show ----------
        print("\n--- 2. Which cards show ---")
        got = cards(page, [SOURCE])
        check("you own no paints: only Best match", got["yours"] is None and len(got["best"]) == 3, got)
        got = cards(page, [SOURCE, TWIN])
        check("the top Best match is already yours: only Best match (no paint twice)",
              got["yours"] is None and got["best"][0][0] == "Owned Twin" and got["best"][0][1] is True, got)
        got = cards(page, [SOURCE, FAR])
        check("you own paints but none is close: Your closest with no rows", got["yours"] == [] and got["best"][0][1] is False, got)
        got = cards(page, [SOURCE, OKAY])
        check("you own a close paint that is not the top match: Your closest lists it",
              got["best"][0][1] is False and got["yours"] and got["yours"][0][0] == "Owned Okay" and got["yours"][0][1] in ("good", "close"), got)
        check("the owned paints only: every row in Your closest is yours", all(x[2] is True for x in got["yours"]), got)
        got = cards(page, [SOURCE, GHOST])
        check("an example paint you 'own' does not count as owning paints", got["yours"] is None, got)
        got = cards(page, [dict(SOURCE, status="owned")])
        check("the paint itself, owned, is not offered in Your closest (and so counts as owning nothing else)", got["yours"] is None, got)
        got = cards(page, [SOURCE, OKAY, FAR])
        check("closest first, and the far paint comes after the close one", [x[0] for x in got["yours"]][:2] == ["Owned Okay", "Owned Far"], got)
        check("at most three rows", len(got["yours"]) <= 3)
        skip = page.evaluate("""() => { const t = Object.entries(NOT_A_COLOUR_TABLE)[0]; const [brand, names] = t;
            book.paints.push({ id: 99, brand, name: names[0], colour: '#3a6ea6', status: 'owned' });
            return similarYourClosest(book.paints[0], 0).hits.some(h => h.paint.name === names[0]); }""")
        check("a paint on the not-a-colour list is never offered, even if you own it", skip is False)

        # ---------- 3. The rows on screen ----------
        print("\n--- 3. The rows ---")
        load(page, paints=[SOURCE, OKAY, FAR])
        open_for(page)
        check("the card is called Your closest and the tab list is Best, Yours",
              page.inner_text("#similar-card-yours h3").strip() == "Your closest" and [x[0] for x in tab_state(page)] == ["Best", "Yours"])
        page.click("#similar-tab-yours")
        got = rows_in(page, "yours")
        check("two rows, each with a fit word; the far one says Yours, poor fit",
              len(got) == 2 and all(r["fit"] in FITS for r in got) and got[0]["name"] == "Owned Okay" and got[1]["fit"] == "Yours, poor fit", got)
        check("no Add button and no 'You own this' line in Your closest (all of it is yours)", all(not r["add"] and not r["own"] for r in got), got)
        check("the paint itself is not a row", all(r["name"] != "Probe Source" for r in got))
        check("the note is still there, once", page.locator(".similar-note").count() == 1 and "only a guide" in page.inner_text(".similar-note"))
        page.keyboard.press("Escape")
        load(page, paints=[SOURCE, FAR])
        open_for(page)
        page.click("#similar-tab-yours")
        check("nothing close: one short line and no rows",
              page.inner_text("#similar-card-yours .similar-none") == "Nothing close in your paints." and len(rows_in(page, "yours")) == 0
              and visible(page, "#similar-card-yours .similar-none"))
        page.keyboard.press("Escape")
        load(page, paints=[SOURCE])
        open_for(page)
        check("no paints of your own: no tabs and no Your closest card", not visible(page, ".similar-tabs") and not visible(page, "#similar-card-yours")
              and visible(page, "#similar-card-best") and page.evaluate("() => !document.querySelector('.similar').classList.contains('two')"))
        page.keyboard.press("Escape")

        # ---------- 4. Lighter and Darker ----------
        print("\n--- 4. Lighter and Darker ---")
        load(page, paints=[SOURCE, OKAY, FAR, P(6, "Beta Paints", "Owned Pale", "#7fa6d6", status="owned")])
        open_for(page)
        page.click("#similar-tab-yours")
        close_rows = [r["name"] for r in rows_in(page, "yours")]
        page.click(".similar-shift button:has-text('Lighter')")
        page.wait_for_timeout(150)
        light_rows = [r["name"] for r in rows_in(page, "yours")]
        page.click(".similar-shift button:has-text('Darker')")
        page.wait_for_timeout(150)
        dark_rows = [r["name"] for r in rows_in(page, "yours")]
        check("Your closest follows Lighter and Darker", len({tuple(close_rows), tuple(light_rows), tuple(dark_rows)}) >= 2, (close_rows, light_rows, dark_rows))
        check("the paler paint ranks better under Lighter than under Darker",
              light_rows.index("Owned Pale") < (dark_rows.index("Owned Pale") if "Owned Pale" in dark_rows else 99), (light_rows, dark_rows))
        check("the tab you are on stays when you change Lighter / Close / Darker", page.get_attribute("#similar-tab-yours", "aria-selected") == "true")
        page.keyboard.press("Escape")

        # ---------- 5. Tabs on a phone ----------
        print("\n--- 5. Tabs ---")
        load(page, paints=[SOURCE, OKAY, FAR])
        open_for(page)
        check("a tab list with two tabs, Best selected", page.get_attribute(".similar-tabs", "role") == "tablist" and tab_state(page) == [["Best", "true", 0], ["Yours", "false", -1]], tab_state(page))
        check("one card at a time: Best shows, Your closest is hidden", visible(page, "#similar-card-best") and not visible(page, "#similar-card-yours"))
        check("each card is a tab panel named by its tab",
              page.evaluate("() => ['best', 'yours'].every(k => { const c = document.getElementById('similar-card-' + k); return c.getAttribute('role') === 'tabpanel' && c.getAttribute('aria-labelledby') === 'similar-tab-' + k; })"))
        check("the tabs say which card they control", page.get_attribute("#similar-tab-yours", "aria-controls") == "similar-card-yours")
        page.focus("#similar-tab-best")
        page.keyboard.press("ArrowRight")
        check("Right arrow selects Yours and moves focus to it", tab_state(page) == [["Best", "false", -1], ["Yours", "true", 0]]
              and page.evaluate("() => document.activeElement.id") == "similar-tab-yours" and visible(page, "#similar-card-yours") and not visible(page, "#similar-card-best"), tab_state(page))
        page.keyboard.press("ArrowLeft")
        check("Left arrow goes back to Best", tab_state(page)[0][1] == "true" and page.evaluate("() => document.activeElement.id") == "similar-tab-best")
        page.keyboard.press("End")
        check("End goes to the last tab", tab_state(page)[1][1] == "true")
        page.keyboard.press("Home")
        check("Home goes to the first tab", tab_state(page)[0][1] == "true")
        page.keyboard.press("ArrowLeft")
        check("the arrows wrap round", tab_state(page)[1][1] == "true")
        page.click("#similar-tab-best")
        check("tapping a tab selects it", tab_state(page)[0][1] == "true" and visible(page, "#similar-card-best"))
        check("the tab not in use is not a tab stop (the arrow keys reach it)", tab_state(page)[1][2] == -1)
        check("the card headings are kept for screen readers only while tabbed", page.evaluate("() => document.querySelector('#similar-card-best h3').classList.contains('sr-only')"))
        check("no previous or next arrows, no Sample label", "Sample" not in page.inner_text(".similar") and page.locator(".similar button", has_text=re.compile("^[‹›←→]$")).count() == 0)
        check("the tab buttons have no paint name in them", all("Probe" not in (b.get_attribute("aria-label") or "") for b in page.locator(".similar button").all()))
        page.keyboard.press("Escape")

        # ---------- 6. Side by side ----------
        print("\n--- 6. Side by side ---")
        page.set_viewport_size({"width": 800, "height": 900})
        load(page, paints=[SOURCE, OKAY, FAR])
        open_for(page)
        pos = page.evaluate("""() => { const a = document.getElementById('similar-card-best').getBoundingClientRect(), b = document.getElementById('similar-card-yours').getBoundingClientRect();
            return { aLeft: a.left, bLeft: b.left, aTop: a.top, bTop: b.top, aRight: a.right, box: document.querySelector('.similar').getBoundingClientRect().width,
                     tabs: !!document.querySelector('.similar-tabs').offsetParent, roleA: document.getElementById('similar-card-best').getAttribute('role') }; }""")
        check("at 800 px both cards show side by side, at the same height", pos["bLeft"] > pos["aRight"] - 1 and abs(pos["aTop"] - pos["bTop"]) < 2, pos)
        check("the tabs are gone and the cards are plain sections", not pos["tabs"] and pos["roleA"] is None, pos)
        check("the pop-up is wider than before (more than 480 px)", pos["box"] > 480, pos["box"])
        check("no sideways scroll at 800 px", no_sideways(page))
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(200)
        check("making the window narrow turns them into tabs again, live", visible(page, ".similar-tabs") and not visible(page, "#similar-card-yours") and popup_open(page))
        page.set_viewport_size({"width": 700, "height": 844})
        page.wait_for_timeout(200)
        check("700 px is the first side-by-side width", not visible(page, ".similar-tabs") and visible(page, "#similar-card-yours"))
        page.set_viewport_size({"width": 699, "height": 844})
        page.wait_for_timeout(200)
        check("699 px still has the tabs", visible(page, ".similar-tabs"))
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 800, "height": 900})
        load(page, paints=[SOURCE])
        open_for(page)
        check("with only Best match the pop-up stays the narrow size at 800 px", page.evaluate("() => document.querySelector('.similar').getBoundingClientRect().width") <= 480)
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Closing and focus ----------
        print("\n--- 7. Closing, focus and Tab ---")
        load(page, paints=[SOURCE, OKAY, FAR])
        page.evaluate("() => { window.__opener = document.createElement('button'); window.__opener.id = 'fake-opener'; window.__opener.textContent = 'Similar paints'; document.body.appendChild(window.__opener); }")
        page.evaluate("() => openSimilarPaints(book.paints[0], window.__opener)")
        page.wait_for_timeout(200)
        page.click("#similar-tab-yours")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Escape from the Yours tab closes it and focus returns to the opener", not popup_open(page) and page.evaluate("() => document.activeElement.id") == "fake-opener")
        open_for(page)
        seen = set()
        for _ in range(14):
            page.keyboard.press("Tab")
            seen.add(page.evaluate("() => { const a = document.activeElement; return a.closest('.similar') ? (a.id || a.textContent) : 'OUTSIDE'; }"))
        check("Tab stays inside the pop-up and only visits the tab in use", "OUTSIDE" not in seen and "similar-tab-yours" not in seen and "similar-tab-best" in seen, seen)
        page.keyboard.press("Shift+Tab")
        check("Shift+Tab stays inside too", page.evaluate("() => !!document.activeElement.closest('.similar')"))
        page.go_back()
        page.wait_for_timeout(300)
        open_for(page)
        open_for(page)
        check("only one pop-up at a time", page.locator(".similar-backdrop").count() == 1)
        page.keyboard.press("Escape")
        page.evaluate("() => { document.getElementById('fake-opener').remove(); }")

        # ---------- 8. Phones, dark and light, another theme ----------
        print("\n--- 8. Phones, dark and light ---")
        def sizes_ok(width, scheme, label):
            # Mo1: the pop-up now rises into place over 240 ms; measure it once it has settled (mid-rise the box sits a fraction of a pixel off, so a 44 px button reads 43.99999).
            page.wait_for_timeout(500)
            sizes = page.evaluate("() => [...document.querySelectorAll('.similar button')].filter(b => b.offsetParent).map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })")
            inside = page.evaluate("() => { const b = document.querySelector('.similar'); return b.scrollWidth <= b.clientWidth + 1 && b.getBoundingClientRect().left >= 15 && b.getBoundingClientRect().right <= window.innerWidth - 15; }")
            check(f"{label}: no sideways scroll, 16 px side margins, every button 44 px or more", no_sideways(page) and inside and sizes and all(w >= 44 and hh >= 44 for w, hh in sizes), (sizes, inside))
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                page.emulate_media(color_scheme=scheme)
                load(page, paints=[SOURCE, OKAY, FAR], settings={"appearance": scheme})   # the app's own Light / Dark setting (it defaults to dark)
                open_for(page)
                sizes_ok(width, scheme, f"{width} px {scheme}, Best tab")
                page.click("#similar-tab-yours")
                sizes_ok(width, scheme, f"{width} px {scheme}, Yours tab")
                if os.path.isdir(t.SHOTS):
                    page.screenshot(path=os.path.join(t.SHOTS, f"v66-similar-{width}-{scheme}-yours.png"))
                page.keyboard.press("Escape")
        for scheme in ("dark", "light"):
            page.set_viewport_size({"width": 800, "height": 900})
            page.emulate_media(color_scheme=scheme)
            load(page, paints=[SOURCE, OKAY, FAR], settings={"appearance": scheme})
            open_for(page)
            sizes_ok(800, scheme, f"800 px {scheme}, side by side")
            if os.path.isdir(t.SHOTS):
                page.screenshot(path=os.path.join(t.SHOTS, f"v66-similar-800-{scheme}.png"))
            page.keyboard.press("Escape")
        for width, scheme in ((390, "dark"), (800, "dark"), (390, "light")):
            page.set_viewport_size({"width": width, "height": 900})
            load(page, paints=[SOURCE, OKAY, FAR], settings={"theme": "forge", "appearance": scheme})
            theme = page.evaluate("() => currentTheme()")
            open_for(page)
            sizes_ok(width, scheme, f"{width} px {scheme}, theme {theme}")
            contrast = page.evaluate("() => [getComputedStyle(document.querySelector('.similar-none, .similar-note')).color, getComputedStyle(document.querySelector('.similar')).backgroundColor]")
            lc, bc = t.luminance(t.rgb(contrast[0])), t.luminance(t.rgb(contrast[1]))
            check(f"{width} px {scheme}, theme {theme}: the small text is readable against the card (contrast 4.5 or more)", (max(lc, bc) + 0.05) / (min(lc, bc) + 0.05) >= 4.5, contrast)
            if os.path.isdir(t.SHOTS):
                page.screenshot(path=os.path.join(t.SHOTS, f"v66-similar-{width}-{theme}-{scheme}.png"))
            page.keyboard.press("Escape")
        page.set_viewport_size({"width": 390, "height": 844})
        css = html[html.index("v65: the Similar paints pop-up"):html.index("/* ----- v14: banners at the top of the screen")]
        check("no colour is written into the pop-up's styles: only the theme's variables",
              not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|\b(white|black|red|blue|green|grey|gray)\b", re.sub(r"/\*.*?\*/", "", css, flags=re.S)))
        code = app[app.index("v65: SIMILAR PAINTS"):app.index("---- v36: THE COLOUR WHEEL")]
        check("no colour is written into the pop-up's code either", not re.search(r"#[0-9a-fA-F]{6}\b|rgba?\(", code))

        # ---------- 9. Errors ----------
        print("\n--- 9. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
