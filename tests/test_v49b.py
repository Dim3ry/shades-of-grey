"""v49 (main) tests for Minifolio (option buttons on one row). Kept as test_v49b because the declutter branch has its own test_v49.

What changed:
 (a) Every group of option buttons (.chips: paint status, To do / Done / Repaint, the eight stages, Paint brands, Appearance,
     the history range, the mood and group buttons, the colour roles, the shop buttons...) is ONE row at every width.
     The buttons share the row (a two-word label may break inside its button); when even that won't fit, each label stays on
     one line and the row scrolls sideways, with a fade on the side that has more and the pressed button brought into view.
 (b) Lists you browse rather than choose from (24 starter schemes, detail recipes, basing tips, your parts and techniques,
     the per-paint "Do you own these?" list) are marked .chips-wrap and still wrap.
 (c) On a wide screen the Units filters put the game and faction menus and To do / Done / Repaint on one line, and the stages
     on the line below.
 (d) The history range buttons are 40 px tall like every other option button (were 36).

Checks:
1. Versions and the v49 Updates line.
2. The CSS: .chips never wraps, browse lists are marked to wrap, scroll rows have room for the focus ring.
3. Every visible option row, on every tab, at 360 and 390 px, in Classic and Paint Bench, dark and light (T3b: the 1280 px run and
   the other four themes were dropped): one line, no button text clipped, buttons at least 40 px (44 where they were 44), nothing
   scrolls the page sideways, two-line buttons get rounded corners instead of a pill.
4. A row that overflows gets the fade class, and its pressed button is scrolled fully into view.
5. The buttons still work: stage and group filters, status, brands, Appearance, history range, the shop buttons.
6. No page errors, no browser pop-ups, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import quiet, tap_tab
from launch_helpers import app_ready
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab_helpers as labh   # X1: the old all-in-one Compendium page (see lab_helpers.py)
import test_v31 as t
from combo_helpers import pick_combo

URL, read, no_sideways = t.URL, t.read, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

THEMES = ["classic", "parchment", "forge", "bench"]   # TH1: Blueprint and Rulebook were removed, so four themes are left
UNITS = [{"id": i + 1, "name": f"Squad {i + 1}", "hobby": "Skirmish", "faction": "Gloom Legion" if i % 2 else "Bright Host",
          "stage": st, "count": 1, "added": "2026-09-01", "log": [["2026-09-01", 0], ["2026-09-1" + str(i), st]], "repaint": i == 3}
         for i, st in enumerate([0, 1, 2, 3, 4, 5, 6, 7])]
PAINTS = [
    {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#0d407f", "status": "wishlist"},
    {"id": 2, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "owned"},
    {"id": 3, "brand": "Vallejo", "name": "Ivory", "colour": "#efe6cf", "status": "empty"},
]
BOOK = {"parts": ["Whole model", "Armour"], "techniques": ["Layer", "Base coat", "Wash"], "paints": PAINTS,
        "recipes": [], "schemes": [], "shorthand": {}, "v15": True}

# Every visible one-row option group: its buttons, whether they share a line, and whether any label is clipped.
ROWS_JS = """() => [...document.querySelectorAll('.chips, .buy-shops')].filter(r => r.offsetParent && r.getClientRects().length).map(r => {
    const kids = [...r.children].filter(c => c.offsetParent && c.tagName === 'BUTTON'), box = r.getBoundingClientRect();
    const tops = new Set(kids.map(c => Math.round(c.getBoundingClientRect().top)));
    const on = kids.filter(c => (c.getAttribute('aria-pressed') === 'true' || c.getAttribute('aria-expanded') === 'true'));
    const inView = (c) => { const b = c.getBoundingClientRect(); return b.left >= box.left - 1 && b.right <= box.right + 1; };
    const cs = getComputedStyle(r);
    return { id: r.id || (r.querySelector(':scope > [data-role]') ? 'colour-roles' : '') || r.parentElement.id || r.parentElement.className, cls: r.className, n: kids.length, lines: tops.size,
             wrapList: r.classList.contains('chips-wrap'), over: r.scrollWidth > r.clientWidth + 1,
             fade: r.classList.contains('chips-more-left') || r.classList.contains('chips-more-right'),
             clipped: kids.filter(c => c.scrollWidth > c.clientWidth + 1 || c.scrollHeight > c.clientHeight + 1).map(c => c.textContent),
             minH: Math.min(...kids.map(c => c.getBoundingClientRect().height)), pressedInView: on.length === 0 || on.some(inView),
             padL: parseFloat(cs.paddingLeft), right: box.right, vw: innerWidth,
             tall: kids.filter(c => c.classList.contains('chip') && c.getBoundingClientRect().height > 50).map(c => getComputedStyle(c).borderTopLeftRadius) }; })"""

TALL44 = ("starter-view", "cmp-starter-view", "buy-shops")

def load(page, settings=None, units=UNITS, book=BOOK):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("""([s, u, b]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [settings, units, book])
    page.goto(URL)
    app_ready(page)
    leave_launch(page)   # U4b: tap through the start page

def tab(page, name):
    t.blur(page)   # the tab bar hides while a text box has the focus (a phone's keyboard is up)
    if name == "compendium": labh.legacy_compendium(page)   # X1: the old all-in-one page
    tap_tab(page, name)
    quiet(page)

def settle(page):
    quiet(page)
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

def open_filters(page):
    # SF3: Filters is a bottom sheet now (the fold-away card and its "Pick by stage" opener are gone): its chips wrap, they do not slide.
    tab(page, "units")
    if not page.evaluate("!!document.getElementById('filters-sheet')"):
        page.click("#toggle-filters")
    settle(page)

def close_filters(page):
    if page.evaluate("!!document.getElementById('filters-sheet')"):
        page.keyboard.press("Escape")
    settle(page)

# SF3: the stage chips used to be the one row that slid sideways at 360 px, and section 4 below used them to check how a sliding row behaves
# (the fade, keeping the pressed button in view, room for the focus ring). The Filters sheet wraps its chips now, so the same row is built here
# by hand: eight stage buttons in a card, redrawn on every tap the way the app redraws its rows.
MAKE_ROW = """(pressed) => { let r = document.getElementById('t-stage-row');
    if (!r) { const card = document.createElement('div'); card.className = 'card'; r = document.createElement('div'); r.id = 't-stage-row'; r.className = 'chips'; card.appendChild(r);
              document.getElementById('view-units').prepend(card); }
    const draw = (p) => r.replaceChildren(...STAGES.map((n, i) => { const b = document.createElement('button'); b.className = 'chip'; b.textContent = n;
        b.setAttribute('aria-pressed', String(i === p)); b.addEventListener('click', () => draw(i)); return b; }));
    draw(pressed); }"""

def seg(page, view):
    tab(page, "recipes")
    page.click(f'#recipe-seg button[data-view="{view}"]')
    settle(page)

def judge(tag, where, rows, seen):
    """Check every row on screen; `seen` collects which rows were met so the sweep can check it reached them all."""
    bad = []
    for r in rows:
        seen.add(r["id"])
        if r["wrapList"]:
            continue
        need = 44 if any(k in (r["id"] + " " + r["cls"]) for k in TALL44) else 40
        if r["lines"] != 1: bad.append(("not one line", r))
        if r["clipped"]: bad.append(("label clipped", r))
        if r["minH"] < need - 0.5: bad.append((f"under {need} px", r))
        if r["right"] > r["vw"] + 1: bad.append(("off the screen", r))
        if r["over"] and not r["fade"]: bad.append(("overflows with no fade", r))
        if r["over"] and not r["pressedInView"]: bad.append(("pressed button hidden", r))
        if r["over"] and r["padL"] < 4: bad.append(("no room for the focus ring", r))
        # AB5 (v134): two-line chips now take the look's control radius (Bench and Classic 6 px, default 8 px, Parchment 2 px, Forge 0), no longer a fixed 14 px; the point here is only that they are not a stretched pill.
        if any(float(rad.replace("px", "")) >= 14 for rad in r["tall"]): bad.append(("two-line button still a stretched pill", r))
    return bad

def sweep(page, tag, results_out, seen):
    """Visit every tab and part of the app that has option rows."""
    def look(where):
        settle(page)
        bad = judge(tag, where, page.evaluate(ROWS_JS), seen)
        if not no_sideways(page): bad.append(("page scrolls sideways", where))
        results_out.extend((where, b) for b in bad)
    tab(page, "dashboard"); look("dashboard")
    open_filters(page); look("units filters")
    page.locator("#fs-chips-stage .chip").last.click(); look("units, last stage pressed")
    page.locator("#fs-chips-stage .chip").last.click()
    close_filters(page)
    seg(page, "recipes"); look("recipes")
    seg(page, "palette"); look("palette")
    page.locator(".paint-head").first.click(); look("palette, a paint open (status)")
    page.fill("#palette-search", "blue"); page.wait_for_timeout(300); look("palette search")
    page.fill("#palette-search", ""); t.blur(page)
    seg(page, "shopping"); look("shopping (shop buttons)")
    tab(page, "compendium")
    for f in page.locator("#view-guides .fold-button").all():
        if f.get_attribute("aria-expanded") == "false": f.click(); page.wait_for_timeout(100)
    pick_combo(page, "#cmp-colour-ideas-base", index=1)
    page.click('#cmp-starter-moods [data-mood="all"]')   # shows the 24 schemes (a browse list, which wraps)
    look("compendium, every fold open")
    page.click("#cmp-starter-view [data-view='combos']"); look("compendium, combinations")
    tab(page, "settings"); page.evaluate("() => { for (const sel of ['#brands-card', '#recipe-prefs-card']) { const b = document.querySelector(sel + ' .card-fold-button'); if (b && b.getAttribute('aria-expanded') !== 'true') b.click(); } }"); settle(page); look("settings")  # v53: Paint brands is a folded card

def main():
    errors, csp, popups = [], [], []
    app, html, sw = read("app.js"), read("index.html"), read("sw.js")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")  # T7: this file checks layout, not motion
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        load(page)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and wording ---")
        m = re.search(r'const VERSION = "v([\d.]+)"', sw)

        # ---------- 2. The CSS ----------
        print("\n--- 2. The CSS ---")
        check(".chips and .buy-shops never wrap", re.search(r"\.chips, \.buy-shops \{[^}]*flex-wrap: nowrap", html) is not None)
        check("only the marked browse lists wrap", re.search(r"\.chips\.chips-wrap \{[^}]*flex-wrap: wrap", html) is not None
              and not re.search(r"\.chips \{[^}]*flex-wrap: wrap", html))
        wraps = set(re.findall(r'door\.id\("([\w-]+)"\)', "\n".join(l for l in app.splitlines() if "chips chips-wrap" in l or "chips.id = door.id" in l)))
        check("the starter schemes, detail recipes and basing tips lists are browse lists",
              app.count('chips.className = "chips chips-wrap";') == 3 and 'list.className = "chips chips-wrap";' in app
              and 'class="chips chips-wrap" id="part-chips"' in html and 'class="chips chips-wrap" id="technique-chips"' in html, wraps)
        check("the history range buttons are 40 px tall (were 36), or 44 px from v53", ".range-chips .chip { padding: 8px 12px; min-height: 40px; }" in html or ".range-chips .chip { padding: 8px 12px; min-height: 44px; }" in html)

        # ---------- 3. Every row, every tab ----------
        print("\n--- 3. Every option row is one line ---")
        seen = set()
        # T3b: 390 and 360 px, dark and light, and the two most different themes (was 12 runs, 16 with the other four themes at 360 px dark)
        runs = [(w, th, mode) for w in (360, 390) for th in ("classic", "bench") for mode in ("dark", "light")]
        for w, th, mode in runs:
            tag = f"{th} {mode} {w}px"
            page.set_viewport_size({"width": w, "height": 900})
            load(page, {"theme": th, "appearance": mode})
            bad = []
            sweep(page, tag, bad, seen)
            check(f"{tag}: every option row is one line, nothing clipped, buttons tall enough, no sideways page", not bad, bad[:3])
            if w == 390 and th == "bench" and mode == "dark":
                open_filters(page); page.locator("#filters-sheet .fs-sheet").screenshot(path=os.path.join(t.SHOTS, "v49-filters-bench-dark-390.png")); close_filters(page)
        want = {"history-range", "fs-chips-progress", "fs-chips-stage", "can-paint-box", "brand-chips", "palette-search-result", "brand-toggles",
                "cmp-starter-view", "cmp-starter-moods", "cmp-starter-combos", "cmp-detail-groups", "cmp-basing-groups", "buy-bar",
                "cmp-starter-chips", "part-chips"}
        check("the sweep met every kind of option row (and the browse lists)", want <= seen, sorted(want - seen))
        check("…including the paint status row and the Appearance row",
              any("status-row" in s for s in seen) and any("appearance" in s for s in seen), sorted(seen))
        check("…and the colour role row (What are you painting?)", "colour-roles" in seen, sorted(seen))

        # Browse lists still wrap.
        page.set_viewport_size({"width": 390, "height": 900})
        load(page)
        tab(page, "compendium")
        for f in page.locator("#view-guides .fold-button").all():
            if f.get_attribute("aria-expanded") == "false": f.click(); page.wait_for_timeout(100)
        page.click('#cmp-starter-moods [data-mood="all"]')
        settle(page)
        lines = page.evaluate("() => new Set([...document.querySelectorAll('#cmp-starter-chips .chip')].map(c => Math.round(c.getBoundingClientRect().top))).size")
        check("the 24 starter schemes still wrap onto several lines (a list to browse)", lines >= 3, lines)
        row = page.evaluate("() => { const r = document.getElementById('cmp-starter-moods'); return [r.className, new Set([...r.children].map(c => Math.round(c.getBoundingClientRect().top))).size]; }")
        check("…while the mood buttons above it are one row", row[1] == 1 and "chips-wrap" not in row[0], row)

        # Two-line buttons: the status row at 390 in Paint Bench shares the row with "Running / low" on two lines.
        load(page, {"theme": "bench", "appearance": "dark"})
        seg(page, "palette"); page.locator(".paint-head").first.click(); settle(page)
        st = page.evaluate("""() => { const r = document.querySelector('.status-row .chips'); return { cls: r.className, over: r.scrollWidth > r.clientWidth + 1,
            radius: [...r.children].map(c => getComputedStyle(c).borderTopLeftRadius), h: [...r.children].map(c => Math.round(c.getBoundingClientRect().height)) }; }""")
        check("Paint Bench 390: the five status buttons share one row with no sideways scroll", "chips-fit" in st["cls"] and not st["over"], st)
        check("…and when a label takes two lines the buttons get rounded corners, all the same height", "chips-tall" not in st["cls"]
              or (len(set(st["radius"])) == 1 and float(st["radius"][0].replace("px", "")) < 14 and len(set(st["h"])) == 1), st)  # AB5: the look's control radius, not a fixed 14 px
        page.locator(".paint-item").first.screenshot(path=os.path.join(t.SHOTS, "v49-status-bench-dark-390.png"))

        # ---------- 4. Overflowing rows ----------
        print("\n--- 4. A row too long for the screen ---")
        page.set_viewport_size({"width": 360, "height": 900})
        load(page, {"theme": "classic", "appearance": "dark"})
        tab(page, "units"); page.evaluate(MAKE_ROW, 0); settle(page)
        r = page.evaluate("() => { const r = document.getElementById('t-stage-row'); return [r.className, r.scrollLeft, r.scrollWidth > r.clientWidth + 1]; }")
        check("360 px: the eight stages scroll sideways with a fade on the right only", r[2] and "chips-scroll" in r[0] and "chips-more-right" in r[0] and "chips-more-left" not in r[0], r)
        page.locator("#t-stage-row .chip").last.scroll_into_view_if_needed()
        page.locator("#t-stage-row .chip").last.click(); settle(page); settle(page)
        r = page.evaluate("""() => { const r = document.getElementById('t-stage-row'), b = r.getBoundingClientRect(), c = r.querySelector('[aria-pressed="true"]').getBoundingClientRect();
            return { cls: r.className, inView: c.left >= b.left - 1 && c.right <= b.right + 1, text: r.querySelector('[aria-pressed="true"]').textContent }; }""")
        check("after the row is redrawn, the pressed stage (the last one) is fully in view and the fade moves to the left",
              r["inView"] and r["text"] == page.evaluate("STAGES[STAGES.length - 1]") and "chips-more-left" in r["cls"] and "chips-more-right" not in r["cls"], r)
        load(page, {"theme": "classic", "appearance": "dark"})   # a fresh page with the last stage pressed from the start
        tab(page, "units"); page.evaluate(MAKE_ROW, 7); settle(page)
        r = page.evaluate("""() => { const r = document.getElementById('t-stage-row'), b = r.getBoundingClientRect(), c = r.querySelector('[aria-pressed="true"]').getBoundingClientRect();
            return c.left >= b.left - 1 && c.right <= b.right + 1; }""")
        check("a row that opens with its pressed button off to the side scrolls to show it", r)
        page.evaluate("document.getElementById('t-stage-row').scrollLeft = 0"); settle(page)
        r = page.evaluate("document.getElementById('t-stage-row').className")
        check("scrolling back to the start by hand moves the fade back to the right", "chips-more-right" in r and "chips-more-left" not in r, r)
        page.evaluate("document.querySelector('#t-stage-row .chip').focus()")
        pad = page.evaluate("() => { const r = document.getElementById('t-stage-row'), c = r.firstElementChild.getBoundingClientRect(), b = r.getBoundingClientRect(); return [c.left - b.left, c.top - b.top, b.bottom - c.bottom]; }")
        check("a focused button has at least 4 px of the row round it, so its focus ring (2 px + 2 px gap) isn't cut off", min(pad) >= 3.5, pad)

        # ---------- 5. The buttons still work ----------
        print("\n--- 5. The buttons still work ---")
        page.set_viewport_size({"width": 390, "height": 900})
        load(page)
        open_filters(page)
        shown = lambda: page.locator("#unit-list li.unit").count()
        before = shown()
        page.locator("#fs-chips-stage .chip").nth(2).click(); settle(page)
        check("a stage button turns on (aria-pressed) and filters the units", page.locator("#fs-chips-stage .chip").nth(2).get_attribute("aria-pressed") == "true"
              and shown() == 1 and before == 8, (before, shown()))
        page.locator("#fs-chips-stage .chip").nth(2).click(); settle(page)
        check("…and tapping it again turns it off", page.locator("#fs-chips-stage .chip").nth(2).get_attribute("aria-pressed") == "false" and shown() == 8)
        page.locator("#fs-chips-progress .chip", has_text="Done").click(); settle(page)
        done = page.evaluate("doneStages().length")
        check("Done turns on and shows the done units", page.locator("#fs-chips-progress .chip", has_text="Done").get_attribute("aria-pressed") == "true" and shown() == done, (shown(), done))
        page.locator("#fs-chips-progress .chip", has_text="Repaint").click(); settle(page)
        check("↻ Repaint narrows it further", page.locator("#fs-chips-progress .chip", has_text="Repaint").get_attribute("aria-pressed") == "true" and shown() <= 1)
        page.click("#fs-clear"); settle(page)   # SF3: Clear all in the sheet (the Clear link under the sheet is behind it)
        check("Clear all still turns every button off", page.locator("#filters-sheet [aria-pressed='true']:not([data-fk='game:']):not([data-fk='faction:'])").count() == 0 and shown() == 8)   # only "All games" and "All factions" stay on
        close_filters(page)

        seg(page, "palette")
        page.locator(".paint-head").first.click(); settle(page)
        page.locator(".status-row .status-chip[data-status='low']").click(); settle(page)
        first = page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-recipes')).paints")
        check("a status button sets the paint's status", any(p.get("status") == "low" for p in first), [p.get("status") for p in first])
        check("…and shows as pressed", page.locator(".status-row .status-chip[data-status='low']").get_attribute("aria-pressed") == "true")

        tab(page, "settings"); page.evaluate("() => { const b = document.querySelector('#brands-card .card-fold-button'); if (b && b.getAttribute('aria-expanded') !== 'true') b.click(); }"); settle(page)
        page.click("#brand-toggles [data-brand-choice='Vallejo']"); settle(page)
        check("a Paint brands button switches the brand off", page.get_attribute("#brand-toggles [data-brand-choice='Vallejo']", "aria-pressed") == "false"
              and page.evaluate("settings.brandsOff") == ["Vallejo"])
        page.click("#brand-toggles [data-brand-choice='Vallejo']"); settle(page)
        page.click("[data-appearance-choice='light']"); settle(page)
        check("Appearance still switches to light", page.evaluate("document.documentElement.dataset.m") == "light"
              and page.get_attribute("[data-appearance-choice='light']", "aria-pressed") == "true")

        tab(page, "dashboard")
        page.locator("#history-range .chip", has_text="1 month").click(); settle(page)
        check("a history range button is chosen and saved", page.evaluate("settings.historyRange") == "30"
              and page.locator("#history-range .chip", has_text="1 month").get_attribute("aria-pressed") == "true")

        seg(page, "shopping")
        if page.locator("#buy-bar .buy-shops button").count():
            page.locator("#buy-bar .buy-shops button").first.click(); settle(page)
            check("a shop button opens its links", page.locator("#buy-bar .buy-shops button").first.get_attribute("aria-expanded") == "true")
        else:
            check("the shopping list has the Buy these shop buttons", False, "no shop buttons")

        # SF3: on a wide screen the Filters sheet is still a bottom sheet no wider than 560 px, with its chips wrapping inside it.
        page.set_viewport_size({"width": 1280, "height": 900})
        load(page)
        open_filters(page)
        geo = page.evaluate("""() => { const b = document.querySelector('#filters-sheet .fs-sheet').getBoundingClientRect(), r = document.getElementById('fs-chips-stage');
            return { w: b.width, bottom: b.bottom, vh: innerHeight, wraps: r.classList.contains('chips-wrap'), over: r.scrollWidth > r.clientWidth + 1 }; }""")
        check("1280 px: the Filters sheet is a bottom sheet at most 560 px wide and the stages wrap inside it",
              geo["w"] <= 561 and abs(geo["bottom"] - geo["vh"]) < 2 and geo["wraps"] and not geo["over"], geo)
        close_filters(page)

        # ---------- 6. Clean run ----------
        print("\n--- 6. A clean run ---")
        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not popups, popups[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
