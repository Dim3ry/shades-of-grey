"""v37 tests for Minifolio (Compendium 2b, part 1): folding sections, the Themes | Combinations switch, and short lists by default.

What changed in the Compendium tab (Pro preview):
 - The colour wheel stays open at the top. Colour ideas, Your schemes, Starter schemes, Detail recipes and Basing tips are each a heading you
   tap to open and close. They all start closed, and which are open is kept while the app is open.
 - Starter schemes has a Themes | Combinations switch. Themes shows the cold, warm, dark and bright groups. Combinations groups the same schemes
   by their main (armour) colour, worked out from the colour, never from the name. Every scheme is reachable in both.
 - Nothing is listed until a group (or All) is chosen in Starter schemes, Detail recipes and Basing tips, so the page stays short.
   Tapping the group that is on puts it away again. The recipe editor's card is exactly as before.
 - Reuse: the same shared builders and the "door" idea (door.fold, door.short, door.switcher); no new files, no libraries, offline.

Checks:
1. Versions, the v37 Updates entry, wiring (six script files, the same twelve offline files, data files and colour.js unchanged), Help,
   and the new code has no network code, no storage, no innerHTML, no links.
2. Folding sections: five headings in order, all closed at the start, accessible (heading, aria-expanded, aria-controls), open and close by
   tap, Enter and Space, the wheel stays open, state kept while the app is open and not after a reload, a closed page is short.
3. Short lists: no list until a group is chosen, the right counts for every group, All, tap again to put away (schemes, detail recipes, tips).
4. The switch: Themes and Combinations, the groups, every one of the 24 schemes reachable in both, placement from colour not name, a picked
   scheme stays in sight, rows, tags and Copy as text the same in both views, the recipe card has no switch and is unchanged.
5. Hostile text (text-injection test) and a text scan for Games Workshop and brand words over everything new.
6. Offline.
7. Phone widths 360, 375, 390 and 400.
8. Dark and light at 390 and 360 px: contrast.
9. Nothing else changed.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheel_helpers as wh   # v43
from notice_watch import attach_notices
import test_v31 as t   # the helpers (loading the app, the palette, the colours) and the Games Workshop word lists
from combo_helpers import pick_combo   # v37 part 2: "Start from" is a search box now

SHOTS, ROOT = t.SHOTS, t.ROOT
read, load, blur, edit_recipe, open_panel = t.read, t.load, t.blur, t.edit_recipe, t.open_panel
shot, no_sideways, rgb, contrast = t.shot, t.no_sideways, t.rgb, t.contrast
rec, unit, HOSTILE, HOSTILE_BRAND, PAINTS = t.rec, t.unit, t.HOSTILE, t.HOSTILE_BRAND, t.PAINTS
GW_WORDS, GW_MORE = t.GW_WORDS, t.GW_MORE
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BRAND_WORDS = re.compile(r"\b(citadel|vallejo|army painter|scale ?75|tamiya|games workshop|warhammer|amazon|ebay|etsy|shop|buy|store)\b", re.I)

KEYS = ["ideas", "history", "starter", "detail", "basing"]
LABELS = ["Colour ideas", "Your schemes", "Starter schemes", "Detail recipes", "Basing tips"]
THEMES = ["All", "Cold", "Warm", "Dark", "Bright"]
COMBOS = ["All", "Reds", "Oranges and browns", "Yellows and sand", "Greens", "Blues", "Purples", "Greys, blacks and whites"]
COMBO_KEYS = ["red", "orange", "yellow", "green", "blue", "purple", "neutral"]
NONE_LINE = "Pick a group above to see its {}, or tap All."

UNITS = [unit(1, "Troop A", "Gloom Legion", [101]), unit(2, "Other", "Other Host", [102])]
RECIPES = [rec(101, "Armour blue", "Whole model", [1, 22]), rec(102, "Orange trim", "Armour", [2, 22]), rec(201, "Blue only", "Armour", [1])]

ROWS_JS = """(sel) => [...document.querySelectorAll(sel)].map(b => ({
    name: b.querySelector('.idea-name').childNodes[0].textContent, brand: (b.querySelector('.idea-name small') || {}).textContent || '',
    tag: b.querySelector('.idea-tag').textContent, why: b.querySelector('.idea-why').textContent,
    note: (b.querySelector('.idea-note') || {}).textContent || '' }))"""
# everything WE wrote on the Compendium (paint names, brands and the pickers are the user's or built-in names, so they are left out)
SHOWN_JS = """() => { const c = document.getElementById('compendium-body').cloneNode(true);
    c.querySelectorAll('.idea-name, select, #cmp-faction-history-for').forEach(e => e.remove());
    return c.innerText + ' ' + [...c.querySelectorAll('[aria-label], title')].map(e => e.getAttribute('aria-label') || e.textContent).join(' '); }"""

def rows(page, sel):
    return page.evaluate(ROWS_JS, sel)

def open_tab(page):
    blur(page)
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_timeout(200)

def is_open(page, key):
    return page.get_attribute(f"#cmp-fold-{key}-button", "aria-expanded") == "true"

def fold(page, key, want=True):
    if is_open(page, key) != want:
        page.click(f"#cmp-fold-{key}-button")
        page.wait_for_timeout(100)

def open_all(page):
    for key in KEYS:
        fold(page, key, True)

def tab_away_and_back(page):
    blur(page)
    page.click('nav button[data-tab="units"]')
    page.wait_for_timeout(120)
    open_tab(page)

def copy_spy(page):
    page.evaluate("""() => { window.__copied = null;
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (x) => { window.__copied = x; return Promise.resolve(); } } }); }""")

def copied(page):
    page.wait_for_timeout(200)
    return page.evaluate("() => window.__copied")

def chips(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s)].map(c => [c.textContent, c.getAttribute('aria-pressed')])", sel)

def scheme_chip_keys(page):
    return page.evaluate("() => [...document.querySelectorAll('#cmp-starter-chips .chip')].map(c => c.dataset.scheme)")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs, requests = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)
        page.on("request", lambda r: requests.append(r.url))

        # ---------- 1. Versions and wiring ----------
        print("\n--- 1. Versions and wiring ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        html, sw, app = read("index.html"), read("sw.js"), read("app.js")
        check("APP_VERSION is v37 or later", float(page.evaluate("APP_VERSION")[1:]) >= 37, page.evaluate("APP_VERSION"))
        check("sw.js VERSION is v37 or later", float(re.search(r'const VERSION = "v([\d.]+)"', sw).group(1)) >= 37)
        tags = re.findall(r'<script src="([^"]+)\?v=(\d+)"', html)
        check("every script tag carries the same ?v= number (37 or later), and there are exactly six script files",
              len(tags) == 6 and len({v for _, v in tags}) == 1 and float(tags[0][1]) >= 37, tags)
        check("APP_VERSION, sw.js and the six script tags all carry the same number",
              {page.evaluate("APP_VERSION")[1:]} == {re.search(r'const VERSION = "v([\d.]+)"', sw).group(1)} == {v for _, v in tags})
        check("the two comments that name the number carry it too (the one in index.html and the one in app.js)",
              f'The "?v={tags[0][1]}" makes' in html and f'e.g. "app.js?v={tags[0][1]}"' in app, tags[0])
        check("the script files are the same six as before, in the same order",
              [n for n, _ in tags] == ["early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "app.js"], tags)
        files = re.search(r"const APP_FILES = \[(.*?)\];", sw, re.S).group(1)
        check("sw.js saves exactly the same twelve app files for offline use (nothing new was added to the app, so nothing new to cache)",
              re.findall(r'"\./([^"?]*)', files) == ["", "index.html", "app.js", "early.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js", "manifest.json", "icon-192.png", "icon-512.png", "ocr/ocr-worker.js"],
              re.findall(r'"\./([^"?]*)', files))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v37')")
        check("Updates has a v37 entry, and the newest entry is v37 or later", entry and float(page.evaluate("CHANGELOG[0].version")[1:]) >= 37, entry)
        joined = " ".join(entry["changes"]) if entry else ""
        check("the Updates entry says Compendium, Pro preview, heading, Themes, Combinations, all 24 schemes, group and short",
              all(w in joined for w in ["Compendium", "Pro preview", "heading", "Themes", "Combinations", "scheme", "group", "short"]), joined[:300])
        check("the v36, v35 and v34 Updates entries are still there", page.evaluate("['v36', 'v35', 'v34'].every(v => !!CHANGELOG.find(r => r.version === v))"))
        check("DATA_VERSION is still 1 and the three storage names are unchanged", page.evaluate("DATA_VERSION") == 1
              and all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']))
        policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        policy = policy.group(1) if policy else ""
        hosts = set(re.findall(r"https?://[^\s;'\"]+", policy))
        check("the security policy is untouched: the only outside address is still the one GoatCounter picture address",
              len(hosts) == 1 and "goatcounter" in list(hosts)[0], (hosts, policy[:200]))
        changed = []
        for base in ("HEAD", "origin/main"):
            out = subprocess.run(["git", "diff", "--name-only", base, "--", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js"],
                                 cwd=ROOT, capture_output=True, text=True)
            if out.returncode == 0: changed += out.stdout.split()
        check("the content data files and colour.js are unchanged (schemes.js, detail-recipes.js, basing-tips.js, colour.js)", changed == [], changed)
        new_code = app[app.index("v37: the group buttons"):app.index("v35: door = where this is shown")] + app[app.index("v37: one folding part"):app.index("function renderCompendium(")]
        check("the new code has no network code, no storage, no innerHTML, no links and no shop wording",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|\beval\s*\(|new Function|insertAdjacentHTML|outerHTML|innerHTML|createElement\('a'\)|createElement\(\"a\"\)|href|affiliate|\bshop\b", new_code),
              [mm.group(0) for mm in re.finditer(r"(fetch|innerHTML|href|affiliate)[^\n]*", new_code)][:3])
        check("the building blocks are shared, not copied: each builder is still defined once, and the card and the Compendium both use libraryParts",
              all(app.count(f"function {n}(") == 1 for n in ["buildStarterSchemes", "buildDetailRecipes", "buildBasingTips", "buildFactionHistory", "libraryParts", "appendLibraryParts", "foldSection", "groupValue", "groupAllows"])
              and app.count("libraryParts(") >= 3)
        help_text = page.evaluate("() => document.getElementById('help-tabs').textContent")
        check("Help still names five tabs and now says the parts open and close under headings and that Starter schemes has a Themes | Combinations switch",
              all(w in help_text for w in ["five tabs", "Compendium", "colour wheel", "heading", "Themes", "Combinations", "without needing a recipe"]), help_text)
        check("the Pro preview label is still on the Compendium", page.locator("#view-compendium .pro-pill").inner_text() == "Pro preview")

        # ---------- 2. Folding sections ----------
        print("\n--- 2. Folding sections ---")
        open_tab(page)
        heads = page.evaluate("""() => [...document.querySelectorAll('#compendium-body > section.fold')].map(s => { const h = s.querySelector(':scope > h3.fold-head'), b = h && h.querySelector('button.fold-button'),
            p = s.querySelector(':scope > .fold-panel'); return { label: b && b.firstElementChild.textContent, name: b && b.textContent, exp: b && b.getAttribute('aria-expanded'),
            controls: b && b.getAttribute('aria-controls'), panelId: p && p.id, hidden: p && p.hidden, empty: p && p.childElementCount === 0, type: b && b.type }; })""")
        check("there are five headings in order: Colour ideas, Your schemes, Starter schemes, Detail recipes, Basing tips", [h["label"] for h in heads] == LABELS, heads)
        check("each heading is a real heading (h3) holding one button that says what the part is", all(h["name"] == h["label"] and h["type"] == "button" for h in heads), heads)
        check("they all start closed (aria-expanded false), and each button points at its own panel (aria-controls)",
              all(h["exp"] == "false" and h["controls"] == h["panelId"] for h in heads), heads)
        check("a closed panel is hidden and empty (nothing is built until it is opened)", all(h["hidden"] and h["empty"] for h in heads), heads)
        check("the wheel is not inside a heading: it stays open at the top, before the five parts",
              page.evaluate("""() => { const b = document.getElementById('compendium-body'), w = document.getElementById('cmp-wheel-block'), f = document.getElementById('cmp-fold-ideas');
                return w.parentElement === b && b.contains(f) && !!(w.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_FOLLOWING) && w.getBoundingClientRect().height > 250; }"""))
        check("none of the five parts' content is on the page while they are closed",
              all(page.locator(f"#{i}").count() == 0 for i in ["cmp-colour-ideas-base", "cmp-faction-history", "cmp-starter-schemes", "cmp-detail-recipes", "cmp-basing-tips"]))
        closed_height = page.evaluate("() => document.getElementById('compendium-body').offsetHeight")
        wh.tap(page, "blue")   # v43: drills into blue and opens a group
        check("the wheel works while the parts are closed (tap a colour: its detail opens below) and no part opens by itself",
              page.locator("#cmp-wheel-detail").count() == 1 and all(not is_open(page, k) for k in KEYS))
        wh.tap(page, "blue")   # v43: back up to the whole wheel
        page.click("#cmp-fold-starter-button")
        page.wait_for_timeout(120)
        check("tapping Starter schemes opens it: the button says expanded, the panel shows, and the part is inside",
              is_open(page, "starter") and page.is_visible("#cmp-fold-starter-panel") and page.locator("#cmp-fold-starter-panel #cmp-starter-schemes").count() == 1)
        check("opening one part leaves the others closed", [is_open(page, k) for k in KEYS] == [False, False, True, False, False])
        check("under a heading the part does not repeat its own title (the heading says it)", page.locator("#cmp-starter-schemes > .scheme-title").count() == 0)
        page.click("#cmp-fold-starter-button")
        page.wait_for_timeout(100)
        check("tapping it again closes it: hidden and empty again", not is_open(page, "starter") and not page.is_visible("#cmp-fold-starter-panel")
              and page.evaluate("() => document.getElementById('cmp-fold-starter-panel').childElementCount") == 0)
        check("the button keeps the focus after a tap (a screen reader stays where you are)", page.evaluate("() => document.activeElement.id") == "cmp-fold-starter-button")
        page.focus("#cmp-fold-detail-button")
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        on_enter = is_open(page, "detail")
        page.keyboard.press(" ")
        page.wait_for_timeout(100)
        check("with the keyboard: Enter opens a part and Space closes it again", on_enter and not is_open(page, "detail"), (on_enter, is_open(page, "detail")))
        page.focus("#cmp-fold-basing-button")
        page.keyboard.press(" ")
        page.wait_for_timeout(100)
        check("Space opens a part too", is_open(page, "basing"))
        fold(page, "basing", False)
        check("the heading buttons can all be reached with the Tab key (none is skipped)",
              page.evaluate("() => [...document.querySelectorAll('.fold-button')].every(b => b.tabIndex === 0 && !b.disabled)"))
        # state is kept
        fold(page, "ideas", True)
        fold(page, "detail", True)
        pick_combo(page, "#cmp-colour-ideas-base", index=1)
        check("choosing a colour inside Colour ideas redraws the page and the open parts stay open", [is_open(page, k) for k in KEYS] == [True, False, False, True, False])
        tab_away_and_back(page)
        check("which parts are open is kept while the app is open (leave the tab and come back)", [is_open(page, k) for k in KEYS] == [True, False, False, True, False],
              [is_open(page, k) for k in KEYS])
        check("the kept state is the door's own (compendiumState.open)", page.evaluate("() => JSON.stringify(Object.keys(compendiumState.open).filter(k => compendiumState.open[k]).sort())") == '["detail","ideas"]')
        page.reload()
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(300)
        check("after the app is closed and opened again (a reload) everything starts closed again", page.is_visible("#view-compendium") and all(not is_open(page, k) for k in KEYS))
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        closed_height = page.evaluate("() => document.getElementById('compendium-body').offsetHeight")
        open_all(page)
        for sel in ['#cmp-starter-moods [data-mood="all"]', '#cmp-detail-groups [data-detail-group="all"]', '#cmp-basing-groups [data-basing-group="all"]']:
            page.click(sel)
        full_height = page.evaluate("() => document.getElementById('compendium-body').offsetHeight")
        check(f"the page is short by default: everything closed is {closed_height} px tall, everything open with every list showing is {full_height} px", full_height > 2.5 * closed_height and closed_height < 1000, (closed_height, full_height))
        shot(page, "v37-all-open-390.png")

        # ---------- 3. Short lists ----------
        print("\n--- 3. Short lists until a group is chosen ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        info = page.evaluate("""() => ({ s: STARTER_SCHEMES.length, d: DETAIL_RECIPES.length, b: BASING_TIPS.length,
            moods: Object.fromEntries(STARTER_MOODS.map(m => [m.key, STARTER_SCHEMES.filter(s => s.mood === m.key).length])),
            dgroups: Object.fromEntries(DETAIL_GROUPS.map(g => [g.key, DETAIL_RECIPES.filter(s => s.group === g.key).length])),
            bgroups: Object.fromEntries(BASING_GROUPS.map(g => [g.key, BASING_TIPS.filter(s => s.group === g.key).length])) })""")
        check("the data is what the tests expect: 24 schemes, 18 detail recipes, 12 basing tips", (info["s"], info["d"], info["b"]) == (24, 18, 12), info)
        for part, chipsId, noneId, what, attr, total in [("starter", "starter-chips", "starter-none", "schemes", "mood", 24), ("detail", "detail-chips", "detail-none-group", "recipes", "detail-group", 18),
                                                          ("basing", "basing-chips", "basing-none-group", "tips", "basing-group", 12)]:
            check(f"{part}: at the start no list is shown, and a plain line says to pick a group or tap All",
                  page.locator(f"#cmp-{chipsId}").count() == 0 and page.inner_text(f"#cmp-{noneId}") == NONE_LINE.format(what), page.inner_text(f"#cmp-{noneId}") if page.locator(f"#cmp-{noneId}").count() else "missing")
            groups_id = {"starter": "starter-moods", "detail": "detail-groups", "basing": "basing-groups"}[part]
            row = chips(page, f"#cmp-{groups_id} .chip")
            check(f"{part}: the group buttons are there, All first, and none is on", row[0][0] == "All" and all(r[1] == "false" for r in row), row)
            page.click(f'#cmp-{groups_id} [data-{attr}="all"]')
            page.wait_for_timeout(100)
            check(f"{part}: All shows all {total}", page.locator(f"#cmp-{chipsId} .chip").count() == total and page.get_attribute(f'#cmp-{groups_id} [data-{attr}="all"]', "aria-pressed") == "true")
            page.click(f'#cmp-{groups_id} [data-{attr}="all"]')
            page.wait_for_timeout(100)
            check(f"{part}: tapping All again puts the list away", page.locator(f"#cmp-{chipsId}").count() == 0 and page.locator(f"#cmp-{noneId}").count() == 1)
        counts = {}
        for key, n in info["moods"].items():
            page.click(f'#cmp-starter-moods [data-mood="{key}"]')
            page.wait_for_timeout(80)
            counts[key] = page.locator("#cmp-starter-chips .chip").count()
        check("every theme group shows exactly its own schemes (Cold, Warm, Dark, Bright)", counts == info["moods"], counts)
        page.click('#cmp-starter-moods [data-mood="bright"]')
        page.wait_for_timeout(80)
        check("tapping the group that is on puts it away", page.locator("#cmp-starter-chips").count() == 0 and page.locator("#cmp-starter-none").count() == 1)
        dcounts, bcounts = {}, {}
        for key in info["dgroups"]:
            page.click(f'#cmp-detail-groups [data-detail-group="{key}"]')
            page.wait_for_timeout(80)
            dcounts[key] = page.locator("#cmp-detail-chips .chip").count()
        for key in info["bgroups"]:
            page.click(f'#cmp-basing-groups [data-basing-group="{key}"]')
            page.wait_for_timeout(80)
            bcounts[key] = page.locator("#cmp-basing-chips .chip").count()
        check("every detail recipe group and every basing group shows exactly its own items", dcounts == info["dgroups"] and bcounts == info["bgroups"], (dcounts, bcounts))
        first_d = list(info["dgroups"])[0]
        page.click(f'#cmp-detail-groups [data-detail-group="{first_d}"]')   # put the group away
        page.wait_for_timeout(80)
        page.click('#cmp-detail-groups [data-detail-group="all"]')
        page.click("#cmp-detail-chips .chip")
        page.wait_for_timeout(100)
        check("picking a detail recipe still shows its steps with paints, and the choice is kept", page.locator("#cmp-detail-list .idea-static").count() >= 2)
        check("the tapped group button keeps the focus after a redraw", (lambda: (page.click('#cmp-basing-groups [data-basing-group="all"]'), page.wait_for_timeout(100), page.evaluate("() => document.activeElement.dataset.basingGroup"))[-1])() == "all")
        page.click('#cmp-basing-groups [data-basing-group="all"]')
        page.wait_for_timeout(100)
        check("and when a group is toggled off the focus stays on that same button", page.evaluate("() => document.activeElement.dataset.basingGroup") == "all")

        # ---------- 4. The Themes | Combinations switch ----------
        print("\n--- 4. Themes | Combinations ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        fold(page, "starter", True)
        sw_ = page.evaluate("""() => { const g = document.getElementById('cmp-starter-view'); return { role: g.getAttribute('role'), label: g.getAttribute('aria-label'),
            buttons: [...g.querySelectorAll('button')].map(b => [b.textContent, b.getAttribute('aria-pressed'), b.dataset.view]) }; }""")
        check("the switch has two buttons, Themes then Combinations, as a labelled group, and Themes is on to start with",
              sw_["role"] == "group" and sw_["label"] == "Browse starter schemes by" and sw_["buttons"] == [["Themes", "true", "themes"], ["Combinations", "false", "combos"]], sw_)
        check("it sits at the top of Starter schemes, above the group buttons",
              page.evaluate("() => { const a = document.getElementById('cmp-starter-view').getBoundingClientRect(), b = document.getElementById('cmp-starter-moods').getBoundingClientRect(); return a.bottom <= b.top + 0.5; }"))
        check("Themes shows the groups All, Cold, Warm, Dark, Bright", [r[0] for r in chips(page, "#cmp-starter-moods .chip")] == THEMES)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.wait_for_timeout(100)
        check("tapping Combinations turns it on and Themes off, and shows the pairing groups", [r[1] for r in chips(page, "#cmp-starter-view .chip")] == ["false", "true"]
              and [r[0] for r in chips(page, "#cmp-starter-combos .chip")] == COMBOS and page.locator("#cmp-starter-moods").count() == 0, chips(page, "#cmp-starter-combos .chip"))
        check("the switch keeps the focus on the button just tapped", page.evaluate("() => document.activeElement.dataset.view") == "combos")
        check("no list until a pairing group is chosen, and the plain line says so", page.locator("#cmp-starter-chips").count() == 0 and page.inner_text("#cmp-starter-none") == NONE_LINE.format("schemes"))
        all_keys = page.evaluate("STARTER_SCHEMES.map(s => s.key)")
        seen, per = [], {}
        for ck in COMBO_KEYS:
            page.click(f'#cmp-starter-combos [data-combo="{ck}"]')
            page.wait_for_timeout(80)
            per[ck] = scheme_chip_keys(page)
            seen += per[ck]
        check("in Combinations every one of the 24 schemes is in exactly one group", sorted(seen) == sorted(all_keys), {k: len(v) for k, v in per.items()})
        check("every pairing group has at least one scheme and none is longer than 8 (a short list)", all(1 <= len(v) <= 8 for v in per.values()), {k: len(v) for k, v in per.items()})
        page.click('#cmp-starter-combos [data-combo="all"]')
        page.wait_for_timeout(80)
        check("in Combinations, All shows all 24", page.locator("#cmp-starter-chips .chip").count() == 24)
        names = page.evaluate("() => Object.fromEntries(STARTER_SCHEMES.map(s => [s.key, s.name]))")
        shown_names = page.evaluate("() => [...document.querySelectorAll('#cmp-starter-chips .chip')].map(c => c.textContent)")
        check("the scheme buttons are named as before (the scheme's own name), in both views", sorted(shown_names) == sorted(names.values()))
        page.click('#cmp-starter-view [data-view="themes"]')
        page.wait_for_timeout(80)
        theme_seen = []
        for mk in ["cold", "warm", "dark", "bright"]:
            page.click(f'#cmp-starter-moods [data-mood="{mk}"]')
            page.wait_for_timeout(80)
            theme_seen += scheme_chip_keys(page)
        check("in Themes every one of the 24 schemes is in exactly one group too (every current scheme is still reachable)", sorted(theme_seen) == sorted(all_keys))
        # placement works from the colour
        by_colour = page.evaluate("""() => { const out = {};
            for (const s of STARTER_SCHEMES) { const at = wheelPlace({ name: '', colour: s.colours[0].hex }); out[s.key] = at ? (['white', 'grey', 'black', 'metallic'].includes(at.seg) ? 'neutral' : at.seg) : 'neutral'; }
            return out; }""")
        check("each scheme sits in the group of its armour colour on the wheel", all(any(k == s for s in per[by_colour[k]]) for k in all_keys), [k for k in all_keys if k not in per[by_colour[k]]])
        fake = page.evaluate("""() => [
            starterComboKey({ name: 'Bright red and white', colours: [{ hex: '#1f4287' }] }),
            starterComboKey({ name: 'Cold blue and gold', colours: [{ hex: '#c1272d' }] }),
            starterComboKey({ name: 'Green things', colours: [{ hex: '#111111' }] }) ]""")
        check("the group comes from the colour, never from the words in the name (a blue armour called 'red' is blue, a red one called 'blue' is red, a black one called 'green' is neutral)",
              fake == ["blue", "red", "neutral"], fake)
        check("the combination code does not look at the scheme's name", "starterComboKey(scheme) {\n      const at = wheelPlace({ name: \"\", colour: scheme.colours[0].hex })" in app.replace("\r", ""))

        # a picked scheme stays in sight, and rows, tags and Copy as text are the same in both views
        copy_spy(page)
        page.evaluate("() => { compendiumState.combo = ''; }")   # no pairing group chosen yet, so the switch has to choose one
        page.click('#cmp-starter-moods [data-mood="cold"]')
        page.click('#cmp-starter-chips [data-scheme="blue-gold"]')
        page.wait_for_timeout(100)
        t_rows = rows(page, "#cmp-starter-list .idea-static")
        page.click("#cmp-starter-schemes .share-row button:has-text('Copy as text')")
        t_copy = copied(page)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.wait_for_timeout(100)
        check("switching to Combinations keeps the picked scheme in sight: its group is chosen, it is still on, and its paints are still shown",
              page.get_attribute('#cmp-starter-combos [data-combo="blue"]', "aria-pressed") == "true" and page.get_attribute('#cmp-starter-chips [data-scheme="blue-gold"]', "aria-pressed") == "true"
              and page.locator("#cmp-starter-list .idea-static").count() == 4)
        c_rows = rows(page, "#cmp-starter-list .idea-static")
        page.click("#cmp-starter-schemes .share-row button:has-text('Copy as text')")
        c_copy = copied(page)
        check("the same scheme gives the same four rows, tags and notes in both views", t_rows == c_rows and len(t_rows) == 4, (t_rows[:1], c_rows[:1]))
        check("and the same Copy as text", t_copy and t_copy == c_copy and t_copy.startswith("Starter scheme: Cold blue and gold"), (t_copy or "")[:80])
        check("Copy as text is plain text: the name, the summary, the reason, one line for each paint and the screen-colours footnote",
              all(r["name"] in t_copy for r in t_rows) and "Cold blue armour, gold trim, red eyes" in t_copy and "classic pair" in t_copy
              and t_copy.rstrip().endswith("Colours on a screen are only a guide, so check them on your model.") and "<" not in t_copy, t_copy[-120:])
        check("Save into a new recipe… is still next to Copy as text", page.locator("#cmp-starter-schemes .share-row button").count() == 2
              and page.locator("#cmp-starter-schemes .share-row button:has-text('Save into a new recipe')").count() == 1)
        page.click('#cmp-starter-view [data-view="themes"]')
        page.wait_for_timeout(100)
        check("switching back to Themes shows the group of the picked scheme (Cold) and the scheme is still picked",
              page.get_attribute('#cmp-starter-moods [data-mood="cold"]', "aria-pressed") == "true" and page.locator("#cmp-starter-list .idea-static").count() == 4)
        # every scheme: same rows in both views
        diffs = []
        for key in all_keys:
            page.click('#cmp-starter-view [data-view="themes"]')
            page.click('#cmp-starter-moods [data-mood="all"]') if page.get_attribute('#cmp-starter-moods [data-mood="all"]', "aria-pressed") != "true" else None
            page.wait_for_timeout(40)
            if page.get_attribute(f'#cmp-starter-chips [data-scheme="{key}"]', "aria-pressed") != "true":
                page.click(f'#cmp-starter-chips [data-scheme="{key}"]')
            page.wait_for_timeout(40)
            a = rows(page, "#cmp-starter-list .idea-static")
            page.click('#cmp-starter-view [data-view="combos"]')
            page.wait_for_timeout(40)
            if page.get_attribute('#cmp-starter-combos [data-combo="all"]', "aria-pressed") != "true" and page.get_attribute(f'#cmp-starter-chips [data-scheme="{key}"]', "aria-pressed") != "true":
                page.click('#cmp-starter-combos [data-combo="all"]')
            page.wait_for_timeout(40)
            if page.get_attribute(f'#cmp-starter-chips [data-scheme="{key}"]', "aria-pressed") != "true":
                page.click(f'#cmp-starter-chips [data-scheme="{key}"]')
            page.wait_for_timeout(40)
            b = rows(page, "#cmp-starter-list .idea-static")
            if not (a == b and len(a) == 4):
                diffs.append((key, a[:1], b[:1]))
        check("all 24 schemes give the same four rows (name, tag, reason, note) in Themes and in Combinations", not diffs, diffs[:1])
        page.click('#cmp-starter-view [data-view="combos"]')
        page.click('#cmp-starter-combos [data-combo="red"]')
        page.wait_for_timeout(80)
        page.click(f'#cmp-starter-chips [data-scheme="{per["red"][0]}"]') if page.get_attribute(f'#cmp-starter-chips [data-scheme="{per["red"][0]}"]', "aria-pressed") != "true" else None
        page.wait_for_timeout(80)
        tab_away_and_back(page)
        check("the view, the group and the picked scheme are kept while the app is open",
              page.evaluate("() => [compendiumState.view, compendiumState.combo, compendiumState.scheme]") == ["combos", "red", per["red"][0]]
              and page.get_attribute('#cmp-starter-view [data-view="combos"]', "aria-pressed") == "true" and page.locator("#cmp-starter-list .idea-static").count() == 4)
        page.click('#cmp-starter-combos [data-combo="blue"]')
        page.wait_for_timeout(80)
        check("choosing another pairing group puts away a scheme that is not in it", page.locator("#cmp-starter-list").count() == 0 and page.evaluate("() => compendiumState.scheme") == "")
        # the recipe card is as before
        edit_recipe(page, 201)
        open_panel(page)
        card = page.evaluate("""() => ({ view: document.querySelectorAll('#colour-ideas #starter-view, #colour-ideas .view-switch').length, folds: document.querySelectorAll('#colour-ideas .fold, #colour-ideas .fold-button').length,
            moods: [...document.querySelectorAll('#starter-moods .chip')].map(c => [c.textContent, c.getAttribute('aria-pressed')]), schemes: document.querySelectorAll('#starter-chips .chip').length,
            title: !!document.querySelector('#starter-schemes > .scheme-title') })""")
        check("the card in a recipe is unchanged: no switch, no folding headings, the title is still there, and All is on with all 24 schemes listed from the start",
              card["view"] == 0 and card["folds"] == 0 and card["title"] and card["schemes"] == 24 and card["moods"][0] == ["All", "true"] and [m[0] for m in card["moods"]] == THEMES, card)
        check("the card's detail recipes and basing tips also still list everything from the start",
              page.locator("#detail-chips .chip").count() == 18 and page.locator("#basing-chips .chip").count() == 12)
        page.click('#starter-moods [data-mood="cold"]')
        page.wait_for_timeout(100)
        check("in the card the mood buttons still work the old way (Cold shows six; All brings back 24)", page.locator("#starter-chips .chip").count() == 6)
        page.click('#starter-moods [data-mood="all"]')
        page.wait_for_timeout(100)
        check("and All in the card is on and shows 24 again", page.locator("#starter-chips .chip").count() == 24 and page.get_attribute('#starter-moods [data-mood="all"]', "aria-pressed") == "true")

        # ---------- 5. Hostile text and the text scan ----------
        print("\n--- 5. Hostile text and the text scan ---")
        evil_paints = PAINTS + [{"id": 90, "brand": HOSTILE_BRAND, "name": HOSTILE, "colour": "#1f4287", "status": "owned"}]
        evil_recipes = [rec(301, HOSTILE, "Armour", [90])]
        evil_units = [unit(1, HOSTILE, HOSTILE + " Host", [301])]
        load(page, paints=evil_paints, recipes=evil_recipes, units=evil_units)
        open_tab(page)
        open_all(page)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.click('#cmp-starter-combos [data-combo="blue"]')
        page.click('#cmp-starter-chips [data-scheme="blue-gold"]')
        page.wait_for_timeout(150)
        names_row = [r["name"] for r in rows(page, "#cmp-starter-list .idea-static")]
        check("hostile paint and brand names show as plain text in the Combinations rows (nothing is built from them)",
              HOSTILE in names_row and page.evaluate("() => window.__pwned") is None and page.locator("#compendium-body img[src='x']").count() == 0
              and page.locator("#compendium-body script").count() == 0, names_row)
        copy_spy(page)
        page.click("#cmp-starter-schemes .share-row button:has-text('Copy as text')")
        text = copied(page)
        check("and in Copy as text, as plain words", text and HOSTILE in text and page.evaluate("() => window.__pwned") is None)
        check("the new buttons are built from fixed text only (no HTML in the headings, the switch or the group buttons)",
              page.evaluate("() => [...document.querySelectorAll('.fold-button, #cmp-starter-view .chip, #cmp-starter-combos .chip')].every(c => [...c.children].every(k => k.tagName === 'SPAN'))"))
        state_ok = page.evaluate("""() => { compendiumState.view = '<img src=x onerror="window.__pwned=7">'; compendiumState.combo = '<b>x</b>'; compendiumState.mood = '<b>y</b>'; compendiumState.open = { starter: true, '<i>': true };
            renderCompendium(); return window.__pwned === undefined && document.querySelectorAll('#compendium-body img[src=x]').length === 0 && document.querySelectorAll('#cmp-starter-chips .chip').length === 0; }""")
        check("odd saved choices (HTML in the view, group or open state) change nothing and break nothing", state_ok)
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        open_tab(page)
        open_all(page)
        page.click('#cmp-starter-combos [data-combo="all"]') if page.locator("#cmp-starter-combos").count() else None
        for sel in ['#cmp-starter-moods [data-mood="all"]', '#cmp-detail-groups [data-detail-group="all"]', '#cmp-basing-groups [data-basing-group="all"]']:
            page.click(sel)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.click('#cmp-starter-combos [data-combo="blue"]')
        page.click('#cmp-starter-chips [data-scheme="blue-gold"]')
        page.wait_for_timeout(100)
        shown = page.evaluate(SHOWN_JS)
        check("text scan: nothing new names a Games Workshop game, faction, scheme, paint or product, or a brand or shop (GW word lists)", not GW_WORDS.search(shown) and not GW_MORE.search(shown),
              (GW_WORDS.search(shown) or GW_MORE.search(shown)).group(0) if (GW_WORDS.search(shown) or GW_MORE.search(shown)) else "")
        check("text scan: no brand, shop or buying words", not BRAND_WORDS.search(shown), BRAND_WORDS.search(shown).group(0) if BRAND_WORDS.search(shown) else "")
        new_text = " ".join(COMBOS + LABELS + ["Themes", "Combinations"])
        check("text scan of the new group and heading names", not GW_WORDS.search(new_text) and not GW_MORE.search(new_text) and not BRAND_WORDS.search(new_text))

        # ---------- 6. Offline ----------
        print("\n--- 6. Offline ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        mark = len(requests)
        open_tab(page)
        open_all(page)
        page.click('#cmp-starter-view [data-view="combos"]')
        page.click('#cmp-starter-combos [data-combo="all"]')
        page.click('#cmp-starter-chips [data-scheme="blue-gold"]')
        outside = [u for u in requests[mark:] if not u.startswith(t.BASE) and not u.startswith("data:") and not u.startswith("blob:")]
        check("using the headings, the switch and the groups makes no request to any other address", not outside, outside[:5])
        ctx.set_offline(True)
        fold(page, "detail", False)
        fold(page, "detail", True)
        page.click('#cmp-starter-view [data-view="themes"]')
        if page.get_attribute('#cmp-starter-moods [data-mood="cold"]', "aria-pressed") != "true":
            page.click('#cmp-starter-moods [data-mood="cold"]')
        check("it all works with the network off", page.locator("#cmp-starter-chips .chip").count() == 6 and is_open(page, "detail"))
        ctx.set_offline(False)

        # ---------- 7. Phone widths ----------
        print("\n--- 7. Phone widths 360, 375, 390 and 400 ---")
        for width in (360, 375, 390, 400):
            page.set_viewport_size({"width": width, "height": 800})
            load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
            open_tab(page)
            geo = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('.fold-button')].map(b => { const r = b.getBoundingClientRect(); return { h: r.height, w: r.width, l: r.left - c.left, rr: c.right - r.right }; }); }""")
            check(f"at {width} px the five headings are 44 px tall or more, full width inside the card, and nothing scrolls sideways",
                  len(geo) == 5 and all(g["h"] >= 44 and g["l"] >= -0.5 and g["rr"] >= -0.5 and g["w"] > 250 for g in geo) and no_sideways(page), geo)
            open_all(page)
            page.click('#cmp-starter-moods [data-mood="all"]')
            page.click('#cmp-detail-groups [data-detail-group="all"]')
            page.click('#cmp-basing-groups [data-basing-group="all"]')
            page.wait_for_timeout(100)
            check(f"at {width} px nothing scrolls sideways with all five parts open and every list showing", no_sideways(page))
            sw_geo = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('#cmp-starter-view .chip')].map(b => { const r = b.getBoundingClientRect(); return { h: r.height, w: r.width, in: r.left >= c.left - 0.5 && r.right <= c.right + 0.5, text: b.scrollWidth <= b.clientWidth + 1 }; }); }""")
            check(f"at {width} px the Themes and Combinations buttons are 44 px tall, the same width, inside the card, with the words fully inside",
                  len(sw_geo) == 2 and all(g["h"] >= 44 and g["in"] and g["text"] for g in sw_geo) and abs(sw_geo[0]["w"] - sw_geo[1]["w"]) < 1, sw_geo)
            page.click('#cmp-starter-view [data-view="combos"]')
            page.wait_for_timeout(100)
            combo_geo = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('#cmp-starter-combos .chip')].map(b => { const r = b.getBoundingClientRect(); return { h: r.height, in: r.left >= c.left - 0.5 && r.right <= c.right + 0.5, text: b.scrollWidth <= b.clientWidth + 1 }; }); }""")
            check(f"at {width} px the eight pairing group buttons are all inside the card, at least 36 px tall, with their words fully inside, and nothing scrolls sideways",
                  len(combo_geo) == 8 and all(g["h"] >= 36 and g["in"] and g["text"] for g in combo_geo) and no_sideways(page), combo_geo)
            page.click('#cmp-starter-combos [data-combo="all"]')
            page.click('#cmp-starter-chips [data-scheme="red-grey"]')
            page.wait_for_timeout(120)
            outside = page.evaluate("""() => { const c = document.querySelector('#view-compendium .card').getBoundingClientRect();
                return [...document.querySelectorAll('#compendium-body *')].filter(e => { const r = e.getBoundingClientRect();
                    return r.width > 0 && (r.right > c.right + 0.5 || r.left < c.left - 0.5); }).map(e => e.id || e.className.baseVal || e.className || e.tagName); }""")
            check(f"at {width} px everything in the Compendium is inside the card with Combinations, All and a scheme open", not outside and no_sideways(page), outside[:5])
            if width in (360, 400):
                page.evaluate("() => window.scrollTo(0, 0)")
                shot(page, f"v37-combinations-{width}.png")
                fold(page, "ideas", False); fold(page, "history", False); fold(page, "detail", False); fold(page, "basing", False); fold(page, "starter", False)
                page.evaluate("() => window.scrollTo(0, 0)")
                shot(page, f"v37-closed-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 8. Dark and light ----------
        print("\n--- 8. Dark and light, 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, paints=PAINTS, recipes=RECIPES, units=UNITS, settings={"appearance": appearance})
                open_tab(page)
                fold(page, "starter", True)
                page.click('#cmp-starter-view [data-view="combos"]')
                page.click('#cmp-starter-combos [data-combo="blue"]')
                page.click('#cmp-starter-chips [data-scheme="blue-gold"]')
                page.wait_for_timeout(100)
                fold(page, "detail", True)
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        const m = v.match(/rgba\\(.*,\\s*([\\d.]+)\\)/);
                        if (v && v !== 'transparent' && !(m && parseFloat(m[1]) < 0.9)) return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const out = {};
                    const pairs = [['heading open', '#cmp-fold-starter-button'], ['heading shut', '#cmp-fold-history-button'], ['switch on', '#cmp-starter-view .chip[aria-pressed="true"]'],
                                   ['switch off', '#cmp-starter-view .chip[aria-pressed="false"]'], ['group on', '#cmp-starter-combos .chip[aria-pressed="true"]'],
                                   ['group off', '#cmp-starter-combos .chip[aria-pressed="false"]'], ['scheme off', '#cmp-starter-chips .chip[aria-pressed="false"]'],
                                   ['none line', '#cmp-detail-none-group'], ['summary', '#cmp-starter-summary'], ['why', '#cmp-starter-list .idea-why'],
                                   ['tag', '#cmp-starter-list .idea-tag'], ['hint', '#cmp-starter-schemes > .hint']];
                    for (const [k, s] of pairs) { const el = document.querySelector(s); if (el) out[k] = [getComputedStyle(el).color, bg(el)]; }
                    return out; }""")
                bad = {k: round(contrast(rgb(v[0]), rgb(v[1])), 2) for k, v in col.items() if contrast(rgb(v[0]), rgb(v[1])) < 4.5}
                tag = f"{appearance} {width}px"
                check(f"{tag}: the headings, the switch, the group and scheme buttons, the plain line and the text all have contrast of at least 4.5", not bad and len(col) >= 11, (bad, len(col)))
                edge = page.evaluate("""() => { const open = getComputedStyle(document.getElementById('cmp-fold-starter-button')), card = getComputedStyle(document.querySelector('#view-compendium .card')).backgroundColor;
                    return { border: open.borderTopColor, card }; }""")
                check(f"{tag}: an open heading has an outline you can see (contrast 3 or more against the card)", contrast(rgb(edge["border"]), rgb(edge["card"])) >= 3, edge)
                mark = page.evaluate("() => { const b = document.getElementById('cmp-fold-starter-button'), m = b.querySelector('.fold-mark'); return [getComputedStyle(m).borderRightColor, getComputedStyle(b).color, getComputedStyle(b).backgroundColor]; }")
                check(f"{tag}: the little arrow on a heading is the same colour as its words, so it can be seen as well as they can", contrast(rgb(mark[0]), rgb(mark[2])) >= 4.5, mark)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v37-compendium-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 9. Nothing else changed ----------
        print("\n--- 9. Nothing else changed ---")
        load(page, paints=PAINTS, recipes=RECIPES, units=UNITS)
        for tab, view in [("dashboard", "view-dashboard"), ("units", "view-units"), ("recipes", "view-recipes"), ("settings", "view-settings"), ("compendium", "view-compendium")]:
            blur(page)
            page.click(f'nav button[data-tab="{tab}"]')
            page.wait_for_timeout(120)
            check(f"the {tab} tab opens its own page and hides the others", page.is_visible(f"#{view}") and sum(page.is_visible(f"#{v}") for v in ["view-dashboard", "view-units", "view-recipes", "view-settings", "view-compendium"]) == 1)
        order = page.evaluate("() => [...document.querySelectorAll('#compendium-body > *')].map(e => e.id).filter(Boolean)")
        check("the Compendium is: the intro, the wheel, the five folding parts, then the footnote",
              order == ["cmp-intro", "cmp-wheel-block", "cmp-fold-ideas", "cmp-fold-history", "cmp-fold-starter", "cmp-fold-detail", "cmp-fold-basing", "cmp-foot"], order)
        check("the intro line says to tap a heading", "Tap a heading to open it" in page.inner_text("#cmp-intro"), page.inner_text("#cmp-intro"))
        check("no real browser pop-ups appeared", not [d for d in dialogs if "Do you own" in d], dialogs[:3])
        check("no page errors", not errors, errors[:3])
        browser.close()

if __name__ == "__main__":
    main()
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
