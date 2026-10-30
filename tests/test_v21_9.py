"""v21.9 tests for Minifolio: fewer tabs + "Tell us" wording (roadmap section 4).

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. The bottom bar has 4 tabs (Dashboard, Units, Recipes, Settings), no Help or Updates button, every
   button at least 44 px tall, at 390 and 360 px, dark and light, nothing scrolls sideways.
3. The Settings / Help / Updates switch: shows only on those three pages, works with real taps, the
   right page shows and the others hide, Settings stays lit in the bottom bar, buttons 44 px or more,
   selected state follows; dark and light at 390 and 360 px, no sideways scroll on any of the pages.
4. The last page used is remembered: saved "help" and "updates" (old values) open the right page with the
   switch showing it; "settings" too; an unknown value opens the Dashboard; nothing about how it is
   saved has changed (still the same plain names); other settings are left alone.
5. The phone's Back button still goes to the Dashboard from Settings, Help and Updates; with nothing
   open on the Dashboard it has nothing to close.
6. Help still works: topics open and shut, the new tabs topic is there, the feedback lines point at
   Settings → Updates; the tab bar still hides while typing, also on the Settings page, and the switch
   can still be tapped meanwhile.
7. The wording: "Tell us what you think" on the Updates page (and the old words are gone); the feedback
   link still works as before.
8. A wide screen (laptop): the bar along the top has 4 tabs and the switch shows, no sideways scroll.
9. No page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import app_ready, quiet, open_settings, tap_tab
import fold_opener   # v54: Stages, Import and Your data fold shut; this older test works inside them
from launch_helpers import leave_launch

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10,
     "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
]
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
PAGES = ["settings", "help", "updates"]
LABELS = {"settings": "Settings", "help": "Help", "updates": "Updates"}

def full_settings(**extra):
    s = {"palette": "ice", "tab": "units", "stages": STAGES, "doneFrom": 5, "examplesChecked": True}
    s.update(extra)
    return s

def seed(page, units=UNITS, settings=None):
    page.goto(URL)
    page.evaluate("""async ([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s || {}));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""",
                  [units, settings or full_settings()])
    page.reload()
    app_ready(page)
    leave_launch(page)   # U4b (v89): a fresh load shows the start page; tap through to the saved section, as before

def main_tab(page, name):
    tap_tab(page, name)
    quiet(page)

def sub_tab(page, name):
    """A real tap on the Settings / Help / Updates switch (the page must already be one of the three)."""
    page.click(f'#more-seg button[data-page="{name}"]')
    quiet(page)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def shown_views(page):
    """Which of the six pages are showing (should be exactly one)."""
    return page.evaluate("""() => [...document.querySelectorAll('main > section')]
        .filter(s => !s.classList.contains('hidden')).map(s => s.id.replace('view-', ''))""")

def lit_tabs(page):
    return page.evaluate("""() => [...document.querySelectorAll('nav button[data-tab]')]   /* U4a: the four segments plus the Settings cog in the header */
        .filter(b => b.getAttribute('aria-current') === 'page').map(b => b.dataset.tab)""")

def seg_state(page):
    return page.evaluate("""() => { const s = document.getElementById('more-seg');
        const r = s.getBoundingClientRect();
        return { shown: !s.classList.contains('hidden') && r.height > 0,
                 labels: [...s.querySelectorAll('button')].map(b => b.textContent.trim()),
                 selected: [...s.querySelectorAll('button')].filter(b => b.getAttribute('aria-selected') === 'true').map(b => b.dataset.page),
                 minHeight: Math.min(...[...s.querySelectorAll('button')].map(b => b.getBoundingClientRect().height)),
                 inside: r.left >= -0.5 && r.right <= window.innerWidth + 0.5 }; }""")

def tabs_hidden(page):
    return page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display === 'none'")

def typing(page):
    return page.evaluate("() => document.body.classList.contains('typing')")

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(120)

def back(page):
    page.evaluate("history.back()")
    page.wait_for_timeout(250)

def main():
    errors, csp = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        fold_opener.open_cards_on_load(page)   # v54: open the folded Settings cards whenever the app loads
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        seed(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.9')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v21.9'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("…about fewer tabs, the switch, remembering the page, Back and the new wording",
                  all(w in joined for w in ["four tabs", "Settings / Help / Updates", "remembers", "Back", "Tell us what you think"]), joined[:300])
        else:
            print("SKIP (entry no longer in the public Updates list): " + '…about fewer tabs, the switch, remembering the page, Back and the new wording')
        check("no code in index.html (no inline scripts or on…= handlers)",
              len(re.findall(r"<script(?![^>]*\bsrc=)", html)) == 0 and re.search(r"\son(click|change|load|input)=", html) is None)
        keys = page.evaluate("() => Object.keys(localStorage).sort()")
        check("storage keys are the same ones as before", "mini-tracker-models" in keys and "shades-of-grey-settings" in keys, keys)

        # ---------- 2. The bottom bar has 4 tabs ----------
        print("\n--- 2. Four tabs along the bottom ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                seed(page, settings=full_settings(appearance=appearance))
                # U4a: the bar has four segments; Settings is the cog in the header (the tab names inside are unchanged)
                names = page.evaluate("() => [...document.querySelectorAll('nav button[data-tab]')].map(b => b.dataset.tab)")
                check(f"{appearance} {width}px: the bar has Dashboard, Units, Recipes and Help and Tools (X2: the cog is gone)",
                      names == ["dashboard", "units", "recipes", "guides"], names)
                check(f"{appearance} {width}px: no Help or Updates button in the bar",
                      page.locator('nav.tabs button[data-tab="help"], nav.tabs button[data-tab="updates"]').count() == 0)
                heights = page.evaluate("() => [...document.querySelectorAll('nav button[data-tab]')].map(b => b.getBoundingClientRect().height)")
                widths = page.evaluate("() => [...document.querySelectorAll('nav button[data-tab]')].map(b => b.getBoundingClientRect().width)")
                check(f"{appearance} {width}px: every tab button is at least 44 px tall and wide", min(heights) >= 44 and min(widths) >= 44, [heights, widths])
                labels = page.evaluate("""() => [...document.querySelectorAll('nav.tabs button[data-tab]')].map(b =>
                    [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim())""")
                check(f"{appearance} {width}px: the labels read Dashboard, Models, Painting, Compendium", labels == ["Dashboard", "Models", "Painting", "Help"], labels)   # X2: the fourth says Help # U3: Painting. U4a: Units is now Models and Settings is the cog
                fits = page.evaluate("""() => [...document.querySelectorAll('nav.tabs button[data-tab]')].every(b => b.scrollWidth <= b.clientWidth + 1)""")
                check(f"{appearance} {width}px: no label is cut off", fits)
                check(f"{appearance} {width}px: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v21-9-bar-{appearance}-{width}.png")
        for name in ["dashboard", "units", "recipes"]:
            main_tab(page, name)
            check(f"the switch is hidden on the {name} tab", not seg_state(page)["shown"])
            check(f"only the {name} page shows", shown_views(page) == [name], shown_views(page))
            check(f"the {name} button is lit", lit_tabs(page) == [name], lit_tabs(page))

        # ---------- 3. The Settings / Help / Updates switch ----------
        print("\n--- 3. The Settings / Help / Updates switch ---")
        page.set_viewport_size({"width": 390, "height": 844})
        seed(page)
        main_tab(page, "settings")
        st = seg_state(page)
        check("tapping Settings in the bar opens the Settings page", shown_views(page) == ["settings"], shown_views(page))
        check("the switch shows, with Settings, Help and Updates in that order", st["shown"] and st["labels"] == ["Guides", "Settings", "Help", "Updates"], st)   # X2: Guides is first
        check("Settings is the selected one", st["selected"] == ["settings"], st)
        check("Settings stays lit in the bar", lit_tabs(page) == ["guides"], lit_tabs(page))   # X2: Settings lives under the Help segment
        check("the switch buttons are at least 44 px tall", st["minHeight"] >= 44, st["minHeight"])
        check("the switch sits inside the screen", st["inside"], st)
        roles = page.evaluate("""() => { const s = document.getElementById('more-seg');
            return [s.getAttribute('role'), [...s.querySelectorAll('button')].map(b => b.getAttribute('role'))]; }""")
        check("the switch is marked up like the Recipes one (a tab list of tabs)", roles == ["tablist", ["tab", "tab", "tab", "tab"]], roles)   # X2: four pages
        check("the Settings page shows the Stages card", page.is_visible("#stage-list"))
        for name in ["help", "updates", "settings", "updates", "help"]:
            sub_tab(page, name)
            st = seg_state(page)
            check(f"tap {LABELS[name]}: only the {name} page shows", shown_views(page) == [name], shown_views(page))
            check(f"tap {LABELS[name]}: it is the selected one", st["selected"] == [name], st)
            check(f"tap {LABELS[name]}: Settings stays lit in the bar", lit_tabs(page) == ["guides"], lit_tabs(page))   # X2: Settings lives under the Help segment
            check(f"tap {LABELS[name]}: the switch stays on screen", st["shown"])
            check(f"tap {LABELS[name]}: the page starts at the top", page.evaluate("() => window.scrollY") == 0)
        sub_tab(page, "help")
        check("the Help page content is there (How to use Minifolio)", "How to use Minifolio" in page.inner_text("#view-help"))
        sub_tab(page, "updates")
        if page.evaluate("['v21.9'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates page content is there (What's new + a v21.9 heading)",
                  "What's new" in page.inner_text("#view-updates") and any(h.startswith("v21.9") for h in page.eval_on_selector_all("#changelog h3", "els => els.map(e => e.textContent)")))
        else:
            print("SKIP (entry no longer in the public Updates list): " + "the Updates page content is there (What's new + a v21.9 heading)")
        main_tab(page, "units")
        check("leaving for Units hides the switch and shows the Units page", not seg_state(page)["shown"] and shown_views(page) == ["units"])
        main_tab(page, "settings")
        check("tapping Settings in the bar from another tab opens the Settings page", shown_views(page) == ["settings"] and seg_state(page)["selected"] == ["settings"])
        sub_tab(page, "help")
        main_tab(page, "settings")
        check("tapping Settings in the bar while on Help goes to the Settings page", shown_views(page) == ["settings"], shown_views(page))
        # keyboard: the switch is made of real buttons, so Tab and Enter work
        page.focus('#more-seg button[data-page="help"]')
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("Enter on a focused switch button opens that page", shown_views(page) == ["help"], shown_views(page))
        page.focus('#more-seg button[data-page="updates"]')
        page.keyboard.press("Space")
        page.wait_for_timeout(150)
        check("Space on a focused switch button opens that page", shown_views(page) == ["updates"], shown_views(page))

        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                seed(page, settings=full_settings(appearance=appearance))
                main_tab(page, "settings")
                for name in PAGES:
                    sub_tab(page, name)
                    st = seg_state(page)
                    check(f"{appearance} {width}px {name}: switch shows, 44 px or more, inside the screen",
                          st["shown"] and st["minHeight"] >= 44 and st["inside"], st)
                    check(f"{appearance} {width}px {name}: nothing scrolls sideways", no_sideways(page))
                    sel = page.evaluate("""() => { const b = document.querySelector('#more-seg button[aria-selected="true"]');
                        const o = document.querySelector('#more-seg button[aria-selected="false"]');
                        const rgb = c => c.match(/[\\d.]+/g).slice(0, 3).map(Number);
                        const lum = c => { const [r, g, bl] = rgb(c).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * bl; };
                        const ratio = (a, c) => { const x = lum(a), y = lum(c); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
                        const s = getComputedStyle(b), t = getComputedStyle(o), card = getComputedStyle(document.getElementById('more-seg')).backgroundColor;
                        return { selected: ratio(s.color, s.backgroundColor), other: ratio(t.color, card) }; }""")
                    check(f"{appearance} {width}px {name}: switch text reads at 4.5 or more (selected and not)", sel["selected"] >= 4.5 and sel["other"] >= 4.5, sel)
                    shot(page, f"v21-9-{name}-{appearance}-{width}.png")

        # ---------- 4. The last page used is remembered ----------
        print("\n--- 4. The last page used is remembered ---")
        page.set_viewport_size({"width": 390, "height": 844})
        seed(page)
        for name in PAGES:
            main_tab(page, "settings")
            sub_tab(page, name)
            check(f"opening {LABELS[name]} saves settings.tab as \"{name}\" (same plain names as before)", saved_settings(page).get("tab") == name, saved_settings(page).get("tab"))
            page.reload()
            app_ready(page)
            check(f"after a reload the {name} page is open", shown_views(page) == [name], shown_views(page))
            # U4b (v89): a reload now shows the start page, so the page is kept underneath and nothing is lit or shown until a section is tapped.
            check(f"after a reload the start page shows, with nothing lit ({name})", page.evaluate("() => document.body.classList.contains('launching')") and lit_tabs(page) == [], lit_tabs(page))
            open_settings(page)
            page.wait_for_timeout(150)
            st = seg_state(page)
            check(f"after opening Settings the switch is shown and Settings is lit ({name})", st["shown"] and lit_tabs(page) == ["guides"], (st, lit_tabs(page)))   # X2: the Help segment is lit
        for old in ["help", "updates", "settings"]:
            seed(page, settings=full_settings(tab=old, appearance="dark", customColours=["#112233"], palette="forge"))
            check(f"an old saved tab of \"{old}\" opens that page", shown_views(page) == [old], shown_views(page))
            check(f"…with the switch showing it", seg_state(page)["selected"] == [old], seg_state(page))
            kept = saved_settings(page)
            check(f"…and the other saved settings are untouched", kept.get("palette") == "forge" and kept.get("appearance") == "dark" and kept.get("customColours") == ["#112233"], kept)
        for plain in ["dashboard", "units", "recipes"]:
            seed(page, settings=full_settings(tab=plain))
            check(f"a saved tab of \"{plain}\" still opens {plain}", shown_views(page) == [plain] and not seg_state(page)["shown"], shown_views(page))
        seed(page, settings=full_settings(tab="bogus"))
        check("an unknown saved tab opens the Dashboard", shown_views(page) == ["dashboard"], shown_views(page))
        seed(page, settings=full_settings(tab="more"))
        check("a made-up \"more\" tab opens the Dashboard too", shown_views(page) == ["dashboard"], shown_views(page))
        seed(page)
        before = page.evaluate("() => localStorage.getItem('mini-tracker-models')")
        for name in ["settings", "help", "updates", "settings"]:
            main_tab(page, "settings")
            sub_tab(page, name)
        after = page.evaluate("() => localStorage.getItem('mini-tracker-models')")
        check("moving around the three pages doesn't change the saved units", before == after)

        # ---------- 5. The phone's Back button ----------
        print("\n--- 5. The phone's Back button ---")
        for name in PAGES:
            seed(page)
            main_tab(page, "settings")
            sub_tab(page, name)
            has_step = page.evaluate("!!(history.state && history.state.minifolio === 'back')")
            check(f"on {LABELS[name]} there is a Back step to use", has_step)
            back(page)
            check(f"Back from {LABELS[name]} goes to the Dashboard", shown_views(page) == ["dashboard"] and page.evaluate("settings.tab") == "dashboard", [shown_views(page), page.evaluate("settings.tab")])
            check(f"…and the switch hides", not seg_state(page)["shown"])
            check(f"…and with nothing left open there is no Back step", not page.evaluate("!!(history.state && history.state.minifolio === 'back')"))
        seed(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        sub_tab(page, "updates")
        sub_tab(page, "settings")
        back(page)
        check("after hopping between the three pages, one Back still goes to the Dashboard", shown_views(page) == ["dashboard"], shown_views(page))
        t = page.evaluate("backTarget()")
        check("on the Dashboard with nothing open Back has nothing to close", t is None, t)
        main_tab(page, "units")
        back(page)
        check("Back from Units still goes to the Dashboard", shown_views(page) == ["dashboard"], shown_views(page))
        # a question box over the Settings page is closed by Back first
        main_tab(page, "settings")
        sub_tab(page, "help")
        page.evaluate("() => askYesNo('Test question?', () => {})")
        page.wait_for_timeout(200)
        back(page)
        check("a question box over Help is closed first by Back (the page stays on Help)",
              shown_views(page) == ["help"] and not page.evaluate("!!dialogState"), [shown_views(page), page.evaluate("!!dialogState")])
        back(page)
        check("a second Back then goes to the Dashboard", shown_views(page) == ["dashboard"], shown_views(page))

        # ---------- 6. Help still works; the tab bar while typing ----------
        print("\n--- 6. Help topics, links and typing ---")
        seed(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        topics = page.evaluate("() => document.querySelectorAll('#view-help details').length")
        check("Help still has its topics", topics >= 10, topics)
        first = page.locator("#view-help details > summary").nth(1)
        was = page.evaluate("() => document.querySelectorAll('#view-help details')[1].open")
        first.click()
        page.wait_for_timeout(120)
        now = page.evaluate("() => document.querySelectorAll('#view-help details')[1].open")
        check("tapping a Help topic's title opens it (and again shuts it)", was != now)
        first.click()
        page.wait_for_timeout(120)
        check("…tapping again shuts it", page.evaluate("() => document.querySelectorAll('#view-help details')[1].open") == was)
        heights = page.evaluate("() => [...document.querySelectorAll('#view-help summary')].map(s => s.getBoundingClientRect().height)")
        check("Help topic titles are still 44 px or more", min(heights) >= 44, min(heights))
        # a jump to a Help topic by its link: set the address's #topic and open it, like a link would
        ok = page.evaluate("""() => { const d = document.getElementById('about'); d.open = true; d.scrollIntoView(); return d.open; }""")
        check("a Help topic can be opened and scrolled to (About)", ok)
        def help_text(i):
            return page.evaluate(f"() => document.getElementById('{i}') ? document.getElementById('{i}').textContent : ''")
        tabs_text = help_text("help-tabs")
        # v75: HELP-3 made this one short sentence
        check("Help explains the four sections and the Help and Tools pages", all(w in tabs_text for w in ["four sections", "Dashboard", "Models", "Painting", "Help and Tools", "Guides", "Settings", "Updates"]), tabs_text)   # X2: no cog   # U4a: four sections around Ask Mentor, Units is Models, Settings is the cog
        feedback_lines = [t for t in page.eval_on_selector_all("#view-help li", "els => els.map(e => e.textContent)") if "Give feedback" in t]
        check("the Help lines that tell you where to find Give feedback say Settings → Updates",
              sum("Settings → Updates" in t for t in feedback_lines) >= 2 and not any("Updates tab" in t for t in feedback_lines), feedback_lines)
        check("no Help line still says the Updates tab", "on the Updates tab" not in html and "the Help tab" not in html.replace("<!--", ""), "")
        check("Help's Back-button line still says it goes to the Dashboard", "Dashboard" in help_text("help-back"))
        # the typing rule, on the Settings page
        sub_tab(page, "settings")
        check("the tab bar shows to start with", not tabs_hidden(page) and not typing(page))
        page.click("#stage-list input")
        page.wait_for_timeout(150)
        check("a text box on Settings has the cursor: the bar steps aside", typing(page) and tabs_hidden(page))
        check("…and the Settings / Help / Updates switch is still on the page", seg_state(page)["shown"])
        sub_tab(page, "help")
        check("tapping Help in the switch while typing works", shown_views(page) == ["help"], shown_views(page))
        check("…and the bar comes back (the cursor left the box)", not tabs_hidden(page) and not typing(page))
        sub_tab(page, "settings")
        page.click("#stage-list input")
        page.wait_for_timeout(150)
        blur(page)
        check("after the cursor leaves the box, the bar is back", not tabs_hidden(page))
        main_tab(page, "dashboard")
        check("after blurring, a bottom-bar tab can be tapped", shown_views(page) == ["dashboard"])

        # ---------- 7. The wording ----------
        print("\n--- 7. The wording ---")
        seed(page)
        main_tab(page, "settings")
        sub_tab(page, "updates")
        heads = page.eval_on_selector_all("#view-updates h2", "els => els.map(e => e.textContent.trim())")
        check("the Updates page says \"Tell us what you think\"", "Tell us what you think" in heads, heads)
        link = page.evaluate("""() => { const a = document.getElementById('feedback-link');
            return { hidden: a.classList.contains('hidden'), href: a.getAttribute('href') || '', rel: a.rel, target: a.target }; }""")
        check("the Give feedback link is unchanged (new tab, noopener noreferrer, version added)",
              (link["hidden"] or (link["target"] == "_blank" and "noopener" in link["rel"] and "noreferrer" in link["rel"] and ("version=" + version) in link["href"])), link)
        check("the unofficial note and the version note are still on the Updates page",
              "Unofficial fan-made app" in page.inner_text("#view-updates") and f"You're on version {version}" in page.inner_text("#view-updates"))

        # ---------- 8. A wide screen ----------
        print("\n--- 8. A wide screen ---")
        page.set_viewport_size({"width": 1100, "height": 800})
        seed(page, settings=full_settings(tab="settings"))
        names = page.evaluate("() => [...document.querySelectorAll('nav button[data-tab]')].map(b => b.dataset.tab)")
        check("the same four sections are there (X2: no cog)", names == ["dashboard", "units", "recipes", "guides"], names)
        top_pos = page.evaluate("() => { const r = document.querySelector('nav.tabs').getBoundingClientRect(); return r.top; }")
        check("the bar is along the bottom (U4a: it no longer moves to the top on a wide screen)", top_pos > 400, top_pos)
        for name in PAGES:
            sub_tab(page, name)
            st = seg_state(page)
            check(f"wide: {name}: the switch shows and the right page is open", st["shown"] and st["selected"] == [name] and shown_views(page) == [name], [st, shown_views(page)])
            check(f"wide: {name}: nothing scrolls sideways", no_sideways(page))
            shot(page, f"v21-9-wide-{name}.png")
        main_tab(page, "units")
        main_tab(page, "settings")
        check("wide: the tab bar is never hidden", not tabs_hidden(page))

        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
