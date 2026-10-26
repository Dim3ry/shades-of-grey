"""v53 tests for Minifolio (declutter chunk D6 part 2: the clean-up after the review sweep).

What changed:
 F1  Base controls (plain, primary and danger buttons, chips, text boxes, menus, the Paste recipes swap buttons) are 44 px tall.
 F2  Small tap targets are 44 px: the Dashboard stage bars, link buttons, the Faction colours link, Open recipe / Go to chips, Unlink,
     Use suggested colour, the short "All" chip, the Faction colours buttons. The basket has a real 44 px hit area (invisible).
 F3  aria-expanded on Parts and techniques, Edit details, Colour ideas and the Add unit button.
 F4  Those three native folds get the Help look (title, then More info / Less info and the arrow) from the same CSS. Same structure.
 F6  Help starts with every topic closed.
 F7  Four short notes sit behind More info: the Paste recipes introduction, what a scheme is (the empty Schemes page keeps "No schemes yet."),
     the colour wheel caption, the light mode note in Settings, Colours.
 F9  The save-failed banner uses theme variables.
 F10 The always-dark surfaces (photo viewer, question box backdrop, viewer arrows, camera) are named variables.
 F13 The iPhone card keeps the warning and the reason in view; the Add to Home Screen steps are behind More info.
 F14 Faction colours and Paint brands fold shut as whole cards (the heading is a 44 px button with aria-expanded).
 Also: the three v34 checks about the Recipes examples card were brought up to date (the card text sits behind More info).

Checks:
1. Versions and the v53 Updates entry.
2. F1: base controls are 44 px (made on the spot, and every control on every page below).
3. F2 and F1 across pages: no tap target under 44 px (360 px light, 390 px dark, 1000 px dark), nothing scrolls sideways; the basket hit area.
4. F3 and F4: aria-expanded and the Help look on the folds, the same structure as before.
5. F6: Help starts closed.
6. F7: the four notes.
7. F9 and F10: banner and always-dark variables.
8. F13: the iPhone card.
9. F14: the two folded cards (closed on open, state only while the app is open, nothing saved, the Dashboard link opens one).
10. What the new code is (and is not) allowed to contain.
11. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v42 as w   # load
import test_v52 as v52   # tab, more_page, press, paints_with_needs

URL, read = t.URL, t.read
results = []
IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

tab, more_page, press = v52.tab, v52.more_page, v52.press

# Every visible control that is under 44 px in either direction. Left out on purpose: the basket (its hit area is checked on its own), the
# greyed do-nothing Add to shopping list button (smaller by design since D1), and links written inside a sentence.
SMALL_JS = """() => {
  const vis = (e) => { if (!e.getClientRects().length) return false; if (getComputedStyle(e).visibility === 'hidden') return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const out = [];
  document.querySelectorAll('button, a[href], summary, select, input:not([type=hidden]), textarea, [role=button], [role=checkbox], [role=tab], [role=switch], [role=radio]').forEach((e) => {
    if (!vis(e) || e.closest('[aria-hidden=true]')) return;
    if (e.id === 'basket-button' || e.classList.contains('shop-idle-button')) return;
    let r = e.getBoundingClientRect();
    if (e.type === 'checkbox' || e.type === 'radio') { const lab = e.closest('label') || (e.id && document.querySelector('label[for="' + e.id + '"]')); if (lab && vis(lab)) r = lab.getBoundingClientRect(); }
    if (e.tagName === 'A' && e.parentElement && e.parentElement.textContent.trim().length > e.textContent.trim().length + 5) return;
    if (r.width < 43.5 || r.height < 43.5) {
      let d = e.tagName.toLowerCase(); if (e.id) d += '#' + e.id; if (e.className && typeof e.className === 'string') d += '.' + e.className.trim().split(/\\s+/).slice(0, 2).join('.');
      out.push(d + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    }
  });
  return out;
}"""

def parse_colour(text):
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    return nums[:3], (nums[3] if len(nums) > 3 else 1.0)

def blend(top, alpha, bottom):
    return [a * alpha + b * (1 - alpha) for a, b in zip(top, bottom)]

def scan(page, label):
    small = page.evaluate(SMALL_JS)
    check(f"{label}: every tap target is 44 px or more", not small, small[:8])
    check(f"{label}: nothing scrolls sideways", t.no_sideways(page))

def storage_dump(page):
    return page.evaluate("() => JSON.stringify(Object.keys(localStorage).sort().map(k => [k, localStorage.getItem(k)]))")

def open_card_folds(page):
    page.evaluate("() => document.querySelectorAll('.card-fold-button[aria-expanded=\"false\"]').forEach(b => b.click())")
    page.wait_for_timeout(120)

def run_pages(page, width, mode):
    tag = f"{width} px {mode}"
    page.set_viewport_size({"width": width, "height": 844})
    w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
    tab(page, "dashboard")
    scan(page, f"{tag}, Dashboard")
    tab(page, "units")
    scan(page, f"{tag}, Units")
    page.evaluate("() => document.getElementById('toggle-add').click()")
    page.wait_for_timeout(150)
    scan(page, f"{tag}, Units with Add unit open")
    page.evaluate("() => document.getElementById('toggle-add').click()")
    page.evaluate("() => document.querySelector('#view-units li.unit .info').click()")
    page.wait_for_timeout(250)
    page.evaluate("() => { const d = document.querySelector('#view-units details.edit-details'); if (d) d.open = true; }")
    page.wait_for_timeout(150)
    scan(page, f"{tag}, an open unit with Edit details open")
    tab(page, "recipes")
    page.evaluate("() => { document.getElementById('recipe-lists').open = true; }")
    page.wait_for_timeout(120)
    scan(page, f"{tag}, Recipes with Parts and techniques open")
    for view in ("palette", "shopping", "recipes"):
        page.evaluate("(v) => document.querySelector('#recipe-seg button[data-view=\"' + v + '\"]').click()", view)
        page.wait_for_timeout(200)
        scan(page, f"{tag}, Recipes, {view}")
    page.evaluate("() => document.querySelector('#recipe-list .recipe-item').click()")
    page.wait_for_timeout(250)
    scan(page, f"{tag}, a recipe")
    t.edit_recipe(page, 101)
    t.open_panel(page)
    scan(page, f"{tag}, the recipe editor with Colour ideas open")
    tab(page, "compendium")
    page.evaluate("""() => { for (const k of ['ideas', 'history', 'starter', 'detail', 'basing']) { const b = document.getElementById('cmp-fold-' + k + '-button'); if (b && b.getAttribute('aria-expanded') !== 'true') b.click(); } }""")
    page.wait_for_timeout(200)
    scan(page, f"{tag}, Compendium with every part open")
    more_page(page, "settings")
    open_card_folds(page)
    scan(page, f"{tag}, Settings with the folded cards open")
    more_page(page, "help")
    scan(page, f"{tag}, Help")
    more_page(page, "updates")
    scan(page, f"{tag}, Updates")

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and wording ---")
        w.load(page, paints=[])
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v53 or later", float(version[1:]) >= 53, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', read("sw.js"))
        check("sw.js VERSION matches", m and "v" + m.group(1) == version)
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the version number", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v53')")
        check("the v53 Updates entry exists (v54 to v69 may sit above it)", bool(entry) and page.evaluate("CHANGELOG[0].version") in ("v53", "v54", "v55", "v56", "v57", "v58", "v59", "v60", "v61", "v62", "v63", "v64", "v65", "v66", "v67", "v68", "v69"))
        check("the v53 entry has no em dashes", entry and not any("—" in x for x in entry["changes"]))
        check("the v53 entry mentions 44 px, More info, Help, Settings and the banner",
              entry and all(any(word in x for x in entry["changes"]) for word in ("44 px", "More info", "Help", "Settings", "banner")))
        check("the new Help line about the folded cards is there and has no em dash",
              "help-card-folds" in html and "—" not in html[html.index('id="help-card-folds"'):html.index('id="help-card-folds"') + 400])

        # ---------- 2. F1: base controls made on the spot ----------
        print("\n--- 2. F1: base controls are 44 px ---")
        heights = page.evaluate("""() => {
          const make = (tag, cls, type) => { const e = document.createElement(tag); if (cls) e.className = cls; if (type) e.type = type; e.textContent = tag === 'button' ? 'Test' : ''; document.body.appendChild(e); return e; };
          const out = {};
          for (const [k, tag, cls, type] of [['plain', 'button', 'plain-button'], ['primary', 'button', 'primary-button'], ['danger', 'button', 'danger-button'],
                                            ['chip', 'button', 'chip'], ['link', 'button', 'link-button'], ['swap', 'button', 'import-swap'], ['swapUse', 'button', 'import-swap-use'],
                                            ['swapCancel', 'button', 'import-swap-cancel'], ['text', 'input', '', 'text'], ['search', 'input', '', 'search'],
                                            ['number', 'input', '', 'number'], ['select', 'select', '']]) {
            const e = make(tag, cls, type); out[k] = Math.round(e.getBoundingClientRect().height * 10) / 10; e.remove();
          }
          return out; }""")
        for name, h in heights.items():
            check(f"a bare {name} control is at least 44 px tall", h >= 43.9, h)
        check("tick boxes keep their own size (the 44 px rule is not forced on them)",
              page.evaluate("() => { const e = document.createElement('input'); e.type = 'checkbox'; document.body.appendChild(e); const h = e.getBoundingClientRect().height; e.remove(); return h < 40; }"))

        # ---------- 3. F2 and F1 across the pages ----------
        print("\n--- 3. Tap targets on every page ---")
        for width, mode in ((390, "dark"), (360, "light"), (1000, "dark")):
            run_pages(page, width, mode)
        print("\n--- 3b. The basket's hit area ---")
        for width in (390, 1000):
            page.set_viewport_size({"width": width, "height": 844})
            w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
            tab(page, "dashboard")
            hit = page.evaluate("""() => {
              const b = document.getElementById('basket-button'); const r = b.getBoundingClientRect(); const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
              const on = (x, y) => { const e = document.elementFromPoint(x, y); return !!e && (e === b || b.contains(e)); };
              return { shown: r.width > 0, h: r.height, up: on(cx, cy - 21), down: on(cx, cy + 21), left: on(cx - 21, cy), right: on(cx + 21, cy), centre: on(cx, cy) }; }""")
            check(f"{width} px: the basket is still a small pill to look at", hit["shown"] and hit["h"] <= 30, hit)
            check(f"{width} px: but a tap 21 px above, below, left or right of its centre still lands on it (a 44 by 44 px hit area)",
                  hit["centre"] and hit["up"] and hit["down"] and hit["left"] and hit["right"], hit)

        # ---------- 4. F3 and F4: aria-expanded and the Help look ----------
        print("\n--- 4. Folds: aria-expanded and the Help look ---")
        page.set_viewport_size({"width": 390, "height": 844})
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        tab(page, "recipes")
        parts = "#recipe-lists > summary"
        info = lambda sel: page.evaluate("""(s) => { const e = document.querySelector(s); const d = e.parentElement; return { exp: e.getAttribute('aria-expanded'), open: d.open, tag: d.tagName, sum: e.tagName,
              after: getComputedStyle(e, '::after').content, h: Math.round(e.getBoundingClientRect().height), look: d.classList.contains('help-look') }; }""", sel)
        i = info(parts)
        check("Parts and techniques: still a native fold (details and summary) in the Help look, shut, aria-expanded false, 44 px, says More info",
              i["tag"] == "DETAILS" and i["sum"] == "SUMMARY" and i["look"] and i["exp"] == "false" and not i["open"] and i["after"] == '"More info"' and i["h"] >= 44, i)
        press(page, page.locator(parts))
        i = info(parts)
        check("tapping it opens it: aria-expanded true and the word turns to Less info", i["open"] and i["exp"] == "true" and i["after"] == '"Less info"', i)
        page.evaluate("() => { document.getElementById('recipe-lists').open = false; }")
        page.wait_for_timeout(100)
        check("shutting it by code sets aria-expanded false", info(parts)["exp"] == "false")
        page.evaluate("() => { document.getElementById('recipe-lists').open = true; }")
        page.wait_for_timeout(100)
        check("opening it by code sets aria-expanded true", info(parts)["exp"] == "true")
        check("Parts and techniques still holds the part and technique chips", page.locator("#recipe-lists #part-chips .chip").count() > 0)

        tab(page, "units")
        toggle = page.locator("#toggle-add")
        check("Add unit: aria-expanded false and controls the add form at the start",
              toggle.get_attribute("aria-expanded") == "false" and toggle.get_attribute("aria-controls") == "add-form")
        press(page, toggle)
        check("Add unit turns into Close with aria-expanded true", toggle.inner_text().strip() == "Close" and toggle.get_attribute("aria-expanded") == "true")
        press(page, toggle)
        check("pressing Close puts it back: Add unit, aria-expanded false", toggle.inner_text().strip() == "+ Add unit" and toggle.get_attribute("aria-expanded") == "false")

        page.evaluate("() => document.querySelector('#view-units li.unit .info').click()")
        page.wait_for_timeout(250)
        edit = "#view-units details.edit-details > summary"
        i = info(edit)
        check("Edit details: native fold in the Help look, shut, aria-expanded false, at least 44 px, says More info",
              i["tag"] == "DETAILS" and i["look"] and i["exp"] == "false" and i["after"] == '"More info"' and i["h"] >= 44, i)
        check("Edit details still begins with its own words", page.locator(edit).inner_text().strip().startswith("Edit details"))
        press(page, page.locator(edit).first)
        i = info(edit)
        check("tapping Edit details opens it: aria-expanded true, Less info", i["open"] and i["exp"] == "true" and i["after"] == '"Less info"', i)

        t.edit_recipe(page, 101)
        ideas = "#colour-ideas > summary"
        i = info(ideas)
        check("Colour ideas: native fold in the Help look, shut, aria-expanded false, at least 44 px, says More info",
              i["tag"] == "DETAILS" and i["look"] and i["exp"] == "false" and i["after"] == '"More info"' and i["h"] >= 44, i)
        check("Colour ideas still shows its title and Pro preview", "Colour ideas" in page.locator(ideas).inner_text() and "Pro preview" in page.locator(ideas).inner_text())
        press(page, page.locator(ideas))
        i = info(ideas)
        check("tapping Colour ideas opens it: aria-expanded true, Less info", i["open"] and i["exp"] == "true" and i["after"] == '"Less info"', i)
        for mode in ("dark", "light"):
            w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
            tab(page, "recipes")
            c = page.evaluate("""() => { const s = document.querySelector('#recipe-lists > summary'); const a = getComputedStyle(s, '::after').color;
                const d = document.createElement('div'); d.style.background = 'var(--card)'; document.body.appendChild(d); const bg = getComputedStyle(d).backgroundColor; d.remove();
                const t = getComputedStyle(s).color; return [a, t, bg]; }""")
            check(f"{mode}: the More info word and the title are readable on the card (4.5:1)",
                  min(t.contrast(t.rgb(c[0]), t.rgb(c[2])), t.contrast(t.rgb(c[1]), t.rgb(c[2]))) >= 4.5, c)

        # ---------- 5. F6: Help starts closed ----------
        print("\n--- 5. Help starts closed ---")
        w.load(page, paints=[], recipes=[], units=t.UNITS)
        more_page(page, "help")
        state = page.evaluate("() => [...document.querySelectorAll('#view-help .help details')].map(d => [d.open, d.querySelector(':scope > summary').getAttribute('aria-expanded')])")
        check("every Help topic starts closed (including Getting started)", len(state) >= 12 and all(o is False and e == "false" for o, e in state), state[:3])
        check("Getting started is still a Help topic (v59: the line above the topics is gone)", "Getting started" in page.inner_text("#view-help"))
        tab(page, "dashboard")
        more_page(page, "help")
        check("still closed after going to another tab and back", page.evaluate("() => document.querySelectorAll('#view-help .help details[open]').length") == 0)
        page.evaluate("() => { document.querySelector('#view-help .help details').open = true; }")
        page.wait_for_timeout(100)
        check("Getting started opens by code (links and Back still work)", page.evaluate("() => document.querySelector('#view-help .help details > summary').getAttribute('aria-expanded')") == "true")

        # ---------- 6. F7: four short notes behind More info ----------
        print("\n--- 6. F7: notes behind More info ---")
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        tab(page, "recipes")
        page.evaluate("() => document.getElementById('paste-recipes').click()")
        page.wait_for_timeout(200)
        intro = "Paste your notes (from Google Keep"
        check("Paste recipes: the heading and the box show, the introduction is behind More info (not on show)",
              "Paste recipes" in page.inner_text("#import-page") and intro not in page.inner_text("#import-page") and page.locator("#import-text").is_visible())
        check("...the introduction text is still in the page, complete", intro in page.text_content("#more-paste-intro") and "preview before anything is saved" in page.text_content("#more-paste-intro"))
        btn = page.locator("#import-page .more-info-button").first
        check("...More info: aria-expanded false, controls the panel, 44 px",
              btn.get_attribute("aria-expanded") == "false" and btn.get_attribute("aria-controls") == "more-paste-intro" and btn.bounding_box()["height"] >= 43.5)
        press(page, btn)
        check("...tapping it shows the introduction with its bold examples (Eyes:, 2:1 Baal:CM, 50/50)",
              intro in page.inner_text("#import-page") and page.locator("#more-paste-intro b").count() == 3 and btn.get_attribute("aria-expanded") == "true")
        page.evaluate("() => { document.querySelector('#import-page .link-button').click(); }")
        page.wait_for_timeout(150)
        page.evaluate("() => document.getElementById('paste-recipes').click()")
        page.wait_for_timeout(200)
        check("...it stays open while the app is open (shut the page and come back)", intro in page.inner_text("#import-page"))
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        tab(page, "recipes")
        page.evaluate("() => document.getElementById('paste-recipes').click()")
        page.wait_for_timeout(200)
        check("...and it is shut again when the app is opened afresh", intro not in page.inner_text("#import-page"))

        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        tab(page, "recipes")
        page.evaluate("() => document.querySelector('#recipe-seg button[data-view=\"schemes\"]').click()")
        page.wait_for_timeout(200)
        shown_text = page.inner_text("#scheme-list")
        check("Schemes with none yet: \"No schemes yet.\" stays in view and the explanation does not",
              "No schemes yet." in shown_text and "A scheme groups" not in shown_text, shown_text)
        check("...the explanation is in the page behind More info", "A scheme groups the recipes you use for one faction" in page.text_content("#more-schemes-empty"))
        btn = page.locator("#scheme-list .more-info-button").first
        check("...More info there: aria-expanded false and 44 px", btn.get_attribute("aria-expanded") == "false" and btn.bounding_box()["height"] >= 43.5)
        press(page, btn)
        check("...tapping it shows what a scheme is", "A scheme groups the recipes" in page.inner_text("#scheme-list"))

        tab(page, "compendium")
        check("Compendium: the colour wheel caption is not on show", not page.locator(".wheel-caption").is_visible())
        check("...but is in the page, whole", "whites, greys, blacks and metallics" in page.text_content("#more-wheel-caption"))
        btn = page.locator("button[aria-controls=\"more-wheel-caption\"]")
        check("...its More info: aria-expanded false", btn.get_attribute("aria-expanded") == "false")
        press(page, btn)
        check("...tapping it shows the caption", page.locator(".wheel-caption").is_visible() and "whites, greys, blacks and metallics" in page.inner_text(".wheel-caption"))

        for mode in ("dark", "light"):
            w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
            more_page(page, "settings")
            wrap = page.evaluate("() => { const n = document.getElementById('palette-light-note'); const w = n.closest('.more-info'); return { has: !!w, hidden: w ? w.hidden : null, vis: !!(w && w.getClientRects().length) }; }")
            if mode == "dark":
                check("dark: the Colours card has no More info (nothing to say in dark mode)", wrap["has"] and wrap["hidden"] and not wrap["vis"], wrap)
            else:
                check("light: the Colours card shows a More info, and the note is not on show", wrap["has"] and wrap["vis"]
                      and "pale stage colours" not in page.inner_text("#view-settings") and "pale stage colours" in page.text_content("#more-colours"), wrap)
                btn = page.locator("button[aria-controls=\"more-colours\"]")
                check("light: its More info has aria-expanded false, 44 px", btn.get_attribute("aria-expanded") == "false" and btn.bounding_box()["height"] >= 43.5)
                press(page, btn)
                check("light: tapping it shows the note", "pale stage colours are shown a little deeper" in page.inner_text("#view-settings"))
        page.evaluate("() => document.querySelector('[data-appearance-choice=\"dark\"]').click()")
        page.wait_for_timeout(150)
        check("switching to dark hides that More info again, and back to light brings it back",
              page.evaluate("() => document.getElementById('palette-light-note').closest('.more-info').hidden === true"))
        page.evaluate("() => document.querySelector('[data-appearance-choice=\"light\"]').click()")
        page.wait_for_timeout(150)
        check("...and light brings it back", page.evaluate("() => document.getElementById('palette-light-note').closest('.more-info').hidden === false"))

        # ---------- 7. F9 and F10 ----------
        print("\n--- 7. F9 and F10: colours ---")
        for old in ("#3b1220", "#fecdd3", "#fda4af"):
            check(f"the save banner no longer holds the fixed colour {old}", old not in html)
        for mode in ("dark", "light"):
            w.load(page, paints=[], settings={"appearance": mode})
            page.evaluate("() => document.getElementById('save-banner').classList.remove('hidden')")
            c = page.evaluate("""() => { const mk = (v) => { const d = document.createElement('div'); d.style.background = 'var(' + v + ')'; document.body.appendChild(d); const c = getComputedStyle(d).backgroundColor; d.remove(); return c; };
                const b = document.getElementById('save-banner'); return { card: mk('--card'), wash: mk('--bad-wash'), danger: mk('--danger'), text: getComputedStyle(b).color,
                  btn: getComputedStyle(b.querySelector('button')).color, btnBorder: getComputedStyle(b.querySelector('button')).borderTopColor, line: getComputedStyle(b).borderBottomColor, h: Math.round(b.querySelector('button').getBoundingClientRect().height) }; }""")
            card, _ = parse_colour(c["card"]); wash, alpha = parse_colour(c["wash"])
            ground = blend(wash, alpha, card)
            check(f"{mode}: the banner text is readable on its theme-colour background (4.5:1)", t.contrast(parse_colour(c["text"])[0], ground) >= 4.5, c)
            check(f"{mode}: the Try again button text and border use the danger colour, readable (4.5:1) and 44 px tall",
                  parse_colour(c["btn"])[0] == parse_colour(c["danger"])[0] and parse_colour(c["btnBorder"])[0] == parse_colour(c["danger"])[0]
                  and t.contrast(parse_colour(c["btn"])[0], ground) >= 4.5 and c["h"] >= 44, c)
            check(f"{mode}: the banner's line is the danger colour", parse_colour(c["line"])[0] == parse_colour(c["danger"])[0], c)
        for var in ("--photo-bg", "--scrim", "--arrow-bg", "--camera-bg", "--camera-shade"):
            check(f"{var} is named once in the style sheet and used through var()", html.count(var + ":") == 1 and f"var({var})" in html)
        for fixed in ("#050911", "rgba(5, 9, 17", "rgba(20, 29, 47, 0.8)", "background: #000;", "rgba(11, 18, 32, 0.55)"):
            check(f"the fixed value {fixed} is only in the variable block now", html.count(fixed) <= 1, html.count(fixed))
        for mode in ("dark", "light"):
            w.load(page, paints=[], settings={"appearance": mode})
            c = page.evaluate("""() => { const mk = (cls, tag) => { const e = document.createElement(tag || 'div'); e.className = cls; document.body.appendChild(e); return e; };
                const v = mk('viewer'), s = mk('dialog-backdrop'), a = mk('viewer-arrow', 'button'), cam = document.getElementById('scan-camera') || mk('');
                const madeCam = !cam.id; if (madeCam) cam.id = 'scan-camera';
                const out = { viewer: getComputedStyle(v).backgroundColor, scrim: getComputedStyle(s).backgroundColor, arrow: getComputedStyle(a).backgroundColor, camera: getComputedStyle(cam).backgroundColor };
                v.remove(); s.remove(); a.remove(); if (madeCam) cam.remove(); return out; }""")
            check(f"{mode}: the photo viewer, the question backdrop and the camera stay dark in both modes",
                  c["viewer"] == "rgb(5, 9, 17)" and c["scrim"] == "rgba(5, 9, 17, 0.72)" and c["arrow"] == "rgba(20, 29, 47, 0.8)" and c["camera"] == "rgb(0, 0, 0)", c)

        # ---------- 8. F13: the iPhone card ----------
        print("\n--- 8. F13: the iPhone card ---")
        for width in (360, 390):
            ip_ctx = browser.new_context(viewport={"width": width, "height": 800}, service_workers="block", user_agent=IPHONE_UA, is_mobile=True, has_touch=True)
            ip = ip_ctx.new_page()
            ip.on("pageerror", lambda e: errors.append(f"iphone pageerror: {e}"))
            w.load(ip, paints=[], recipes=[], units=t.UNITS)
            tab(ip, "dashboard")
            card = ip.locator("#iphone-warning")
            check(f"{width} px: the card shows on an iPhone in Safari", card.is_visible())
            seen = ip.inner_text("#iphone-warning")
            check(f"{width} px: the warning and the reason stay in view", "Keep your data safe on iPhone." in seen and "Safari can delete this app's saved units and photos if you don't open it for 7 days" in seen
                  and "Add it to your Home Screen to stop that." in seen, seen)
            check(f"{width} px: the Add to Home Screen steps are behind More info", "Share button" not in seen and "Share button" in ip.text_content("#iphone-steps"))
            btn = ip.locator("#iphone-warning .more-info-button")
            check(f"{width} px: More info there has aria-expanded false and is 44 px", btn.get_attribute("aria-expanded") == "false" and btn.bounding_box()["height"] >= 43.5)
            old_height = {360: 225, 390: 205}[width]   # measured on v52 (the sweep)
            check(f"{width} px: the card is at least 30 px shorter than the old {old_height} px (closed)", card.bounding_box()["height"] <= old_height - 30, card.bounding_box()["height"])
            row = ip.evaluate("() => { const a = document.querySelector('#iphone-warning .more-info-button').getBoundingClientRect(), b = document.getElementById('iphone-warning-ok').getBoundingClientRect(); return [Math.abs(a.top - b.top) < 6, a.right <= b.left + 1]; }")
            check(f"{width} px: More info and Got it share one row", row == [True, True], row)
            check(f"{width} px: Got it is a full 44 px target", ip.locator("#iphone-warning-ok").bounding_box()["height"] >= 43.5)
            press(ip, btn)
            check(f"{width} px: More info shows the steps", "Tap Safari's Share button, then Add to Home Screen, and open it from there." in ip.inner_text("#iphone-warning"))
            ip.locator("#iphone-warning-ok").click()
            ip.wait_for_timeout(150)
            check(f"{width} px: Got it still hides the card", not ip.locator("#iphone-warning").is_visible())
            t.no_sideways(ip)
            ip_ctx.close()

        # ---------- 9. F14: the two folded cards ----------
        print("\n--- 9. F14: Faction colours and Paint brands fold shut ---")
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        more_page(page, "settings")
        for key, card, panel_content in (("faction-colours", "#faction-colours-card", "#faction-colour-list"), ("paint-brands", "#brands-card", "#brand-toggles")):
            btn = page.locator(f"{card} > h2 > button.card-fold-button")
            check(f"{key}: the heading is a real button inside the h2, aria-expanded false, controls its panel, at least 44 px",
                  btn.count() == 1 and btn.get_attribute("aria-expanded") == "false" and btn.get_attribute("aria-controls") == f"card-fold-{key}-panel"
                  and btn.bounding_box()["height"] >= 43.5 and page.locator(f"{card} > h2").count() == 1)
            check(f"{key}: it carries the same chevron as the Compendium folds", page.locator(f"{card} .card-fold-button .fold-mark").count() == 1)
            check(f"{key}: shut at the start, its contents are not on show", not page.locator(panel_content).first.is_visible())
        before = storage_dump(page)
        fc = page.locator("#faction-colours-card .card-fold-button")
        press(page, fc)
        check("Faction colours: tapping the heading opens it (aria-expanded true) and the list shows",
              fc.get_attribute("aria-expanded") == "true" and page.locator("#faction-colour-list li").first.is_visible())
        check("Faction colours: its explanation is still behind its own More info inside the card", page.locator("#faction-colours-card .more-info-button").count() == 1)
        pb = page.locator("#brands-card .card-fold-button")
        press(page, pb)
        check("Paint brands: tapping the heading opens it and the brand buttons show", pb.get_attribute("aria-expanded") == "true" and page.locator("#brand-toggles .chip").first.is_visible())
        first_brand = page.locator("#brand-toggles .chip").first
        was = first_brand.get_attribute("aria-pressed")
        press(page, first_brand)
        check("Paint brands: its buttons still work once open", first_brand.get_attribute("aria-pressed") != was)
        press(page, first_brand)   # back to how it was
        press(page, fc); press(page, pb)
        check("tapping the headings again shuts both", fc.get_attribute("aria-expanded") == "false" and pb.get_attribute("aria-expanded") == "false"
              and not page.locator("#faction-colour-list").is_visible() and not page.locator("#brand-toggles").is_visible())
        check("opening and shutting them saved nothing (every stored value is the same)", storage_dump(page) == before)
        press(page, fc)
        tab(page, "dashboard")
        more_page(page, "settings")
        check("an open card stays open while the app is open (to another tab and back)", fc.get_attribute("aria-expanded") == "true" and page.locator("#faction-colour-list").is_visible())
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'"); page.wait_for_timeout(300)
        more_page(page, "settings")
        check("both cards are shut again when the app is opened afresh",
              page.locator("#faction-colours-card .card-fold-button").get_attribute("aria-expanded") == "false" and page.locator("#brands-card .card-fold-button").get_attribute("aria-expanded") == "false")
        tab(page, "dashboard")
        page.evaluate("() => document.getElementById('faction-colours-link').click()")
        page.wait_for_timeout(300)
        check("Faction colours on the Dashboard opens Settings with that card open",
              page.locator("#faction-colours-card .card-fold-button").get_attribute("aria-expanded") == "true" and page.locator("#faction-colour-list").is_visible()
              and page.evaluate("() => { const r = document.getElementById('faction-colours-card').getBoundingClientRect(); return r.top < innerHeight; }"))
        folded = page.evaluate("() => [...document.querySelectorAll('#view-settings .card-fold')].map(c => c.id)")
        check("Faction colours and Paint brands fold, and Backups stays open (v54 later folds Stages, Import and Your data too)", [c for c in folded if c in ("faction-colours-card", "brands-card")] == ["faction-colours-card", "brands-card"] and "backup-card" not in folded, folded)
        check("the Backups buttons are still in view and 44 px (the five big buttons)",
              page.evaluate("() => [...document.querySelectorAll('#backup-card .plain-button')].filter(b => b.getClientRects().length).every(b => b.getBoundingClientRect().height >= 43.5)"))

        # ---------- 10. What the new code is allowed to contain ----------
        print("\n--- 10. The new code ---")
        helpers = app[app.index("const openCards = new Set();"):app.index("// v53: the same for any other native fold")]
        mark = app[app.index("const markedFolds = new WeakSet();"):app.index("function markFold(box)") + 500]
        for name, code in (("the card fold helper", helpers), ("the fold marker", mark)):
            check(f"{name} has no innerHTML, no storage and no network code",
                  not re.search(r"innerHTML|insertAdjacentHTML|localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|WebSocket", code))
        paste_code = app[app.index("// v53: the introduction sits behind More info"):app.index("card.append(box, read);")]
        check("the Paste recipes introduction is built from nodes (no innerHTML)", not re.search(r"\.innerHTML\s*=|insertAdjacentHTML", paste_code) and "textContent" in paste_code)
        check("the helpers sit with the v52 helpers, outside the v36 and v37 scanned code",
              app.index("function foldPageText") < app.index("const openCards") < app.index("function compactRows"))
        check("no em dash in the new Help line or the new hints", "—" not in html[html.index("/* v53"):html.index("/* v53") + 1500])
        check("no new colour is written into any rule: the new CSS uses variables only",
              not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", html[html.index(".card-fold > h2"):html.index(".fold-panel { display: grid")]))

        # ---------- 11. No errors ----------
        print("\n--- 11. No errors ---")
        check("no page error and no unexpected pop-up during all of this", not errors and not dialogs, (errors[:3], dialogs[:3]))
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
