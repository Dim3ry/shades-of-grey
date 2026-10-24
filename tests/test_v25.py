"""v25 tests for Minifolio: one gentle "send feedback?" card after about a week of use (roadmap section 4).

Checks:
1. Version numbers (plain numbers, "v25 or later"), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. When the card shows: not on a brand-new start, not for someone who already uses the app (their week starts
   when they update), not at 6 days, yes at 7 and later. It stays up on a reload the same day.
3. What the card is: words, the three controls in order, the same address as Settings -> Updates, only on the Dashboard.
4. Give feedback (real tap): the form opens in a new tab, the card goes and never comes back.
5. Not now (real tap and key press): hides it, asks again only after 30 days.
6. Don't ask again (real tap): hides it for good, says so, Settings -> Updates still has the link.
7. Never twice in a row: a card nobody answered counts as "Not now" the next day.
8. Nothing is sent: no request leaves the app (except the form, when opened), no network code in the new section,
   a backup doesn't carry the dates.
9. Saved data's shape (DATA_VERSION stays 1): settings keep unknown keys, odd saved values never break anything.
10. Dark and light at 390 and 360 px: card on screen, 44 px targets, readable, no sideways scroll.
11. It sits well with the examples card and the Back button.
12. Help and Updates wording (reached via Settings, then the Help / Updates switch).
13. No real browser pop-ups, no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import datetime, json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices

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

V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
UNITS = [{"id": 1, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 10},
         {"id": 2, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10}]
FORM = "https://tally.so/r/Y5Lka6"

def day(n):
    """A date in YOUR time zone, written like the app writes it: today plus n days."""
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()

def clear_photos(page):
    page.evaluate("""async () => { await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""")

def settle(page):
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)

def fresh(page, settings=None):
    """A brand-new start: nothing saved at all (apart from the settings given)."""
    page.goto(URL)
    page.evaluate("(s) => { localStorage.clear(); if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }", settings)
    clear_photos(page)
    page.reload()
    settle(page)

def existing(page, settings=None, units=None):
    """Someone who has used the app before: units saved (and maybe settings)."""
    page.goto(URL)
    page.evaluate("""([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units or UNITS, settings])
    clear_photos(page)
    page.reload()
    settle(page)

def patch_settings(page, **changes):
    """Change what is saved (like a day going by), then open the app again."""
    page.evaluate("""(c) => { const s = JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}');
        for (const [k, v] of Object.entries(c)) { if (v === null) delete s[k]; else s[k] = v; }
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", changes)
    page.reload()
    settle(page)

def main_tab(page, name):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def card_shown(page):
    return page.locator("#feedback-card").is_visible()

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

def main():
    errors, csp, popups, notices, outside = [], [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        # The feedback form is somebody else's website: answer for it here, and note every request that leaves.
        context.route("https://tally.so/**", lambda route: route.fulfill(status=200, content_type="text/html", body="<p>form</p>"))
        context.on("request", lambda r: outside.append(r.url) if not (r.url.startswith(BASE) or r.url.startswith(("data:", "blob:", "about:"))) else None)
        page = context.new_page()
        attach_notices(page, notices.append)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        fresh(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v25 or later", float(version[1:]) >= 25, version)
        check("version is a plain number", re.fullmatch(r"v\d+(\.\d+)?", version) is not None, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="(early|app)\.js\?v=([\d.]+)"', html)
        check("both script tags carry ?v= matching APP_VERSION", sorted(tags) == [("app", version[1:]), ("early", version[1:])], tags)
        check("the comment above the script tag names the same number", f'The "?v={version[1:]}" makes' in html)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v25')")
        if page.evaluate("['v25'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v25 entry with two lines", entry and len(entry["changes"]) >= 2, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v25 entry with two lines')
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder and the paint-list licence kept",
              os.path.isdir(os.path.join(ROOT, "ocr")) and os.path.exists(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        wf = read(".github/workflows/zap-scan.yml")
        check("the ZAP workflow is still the passive baseline scan", "zaproxy/action-baseline" in wf and "full-scan" not in wf)
        csp_meta = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        check("the CSP is exactly v21.4's", csp_meta and " ".join(csp_meta.group(1).split()) == V21_4_CSP,
              csp_meta and csp_meta.group(1))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("storage names unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"',
                                     'RECIPES_KEY = "shades-of-grey-recipes"']))
        check("no code was put inside index.html", len(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html)) == 0)
        check("the feedback address is still the Tally form", page.evaluate("FEEDBACK_URL") == FORM)

        # ---------- 2. When the card shows ----------
        print("\n--- 2. When the card shows ---")
        fresh(page)
        check("a brand-new start: no card", not card_shown(page))
        s = saved_settings(page)
        check("the first day is saved (today), and nothing else about feedback yet",
              s.get("feedbackFirstSeen") == day(0) and not s.get("feedbackShownOn") and not s.get("feedbackHidden")
              and not s.get("feedbackNextAfter"), s)
        existing(page)
        check("someone who already uses the app (no first day saved): no card straight away", not card_shown(page))
        check("their week starts today", saved_settings(page).get("feedbackFirstSeen") == day(0), saved_settings(page))
        existing(page, {"palette": "ice", "tab": "dashboard", "firstRealUse": day(-200), "lastBackup": day(-3)})
        check("even a long-time user with older settings gets no instant card", not card_shown(page))
        check("and their first day is today, not their old first use", saved_settings(page).get("feedbackFirstSeen") == day(0))
        for ago, expect in ((1, False), (3, False), (6, False), (7, True), (8, True), (30, True), (400, True)):
            existing(page, {"feedbackFirstSeen": day(-ago)})
            check(f"first used {ago} days ago: card {'shows' if expect else 'does not show'}", card_shown(page) == expect, card_shown(page))
        existing(page, {"feedbackFirstSeen": day(-10)})
        check("when it shows, the day is saved", saved_settings(page).get("feedbackShownOn") == day(0), saved_settings(page))
        page.reload(); settle(page)
        check("a reload the same day keeps it up", card_shown(page))
        page.reload(); settle(page)
        check("and again", card_shown(page))
        check("opening other tabs and coming back keeps it", (main_tab(page, "units"), main_tab(page, "dashboard"), card_shown(page))[2])

        # ---------- 3. What the card is ----------
        print("\n--- 3. What the card is ---")
        existing(page, {"feedbackFirstSeen": day(-10)})
        text = page.inner_text("#feedback-card")
        check("the card is polite and short (v59: just the question)",
              "Enjoying Minifolio?" in text and "short form" not in text, text)
        controls = page.evaluate("""() => [...document.querySelectorAll('#feedback-card a, #feedback-card button')]
            .map(e => [e.tagName, e.textContent.trim()])""")
        check("three controls in order: Give feedback, Not now, Don't ask again",
              controls == [["A", "Give feedback"], ["BUTTON", "Not now"], ["BUTTON", "Don't ask again"]], controls)
        link = page.evaluate("""() => { const a = document.querySelector('#feedback-card a');
            return { href: a.getAttribute('href'), target: a.target, rel: a.rel }; }""")
        check("Give feedback opens a new tab with noopener noreferrer", link["target"] == "_blank" and "noopener" in link["rel"] and "noreferrer" in link["rel"], link)
        check("it is the form, with the version number", link["href"] == f"{FORM}?version={version}", link)
        main_tab(page, "settings"); sub_tab(page, "updates")
        same = page.evaluate("() => document.getElementById('feedback-link').getAttribute('href')")
        check("the same address as Settings -> Updates", same == link["href"], (same, link["href"]))
        check("the card is not on the Updates page", not card_shown(page))
        main_tab(page, "units")
        check("not on the Units tab", not card_shown(page))
        main_tab(page, "recipes")
        check("not on the Recipes tab", not card_shown(page))
        main_tab(page, "dashboard")
        check("back on the Dashboard it is there", card_shown(page))
        check("it is a note for screen readers", page.get_attribute("#feedback-card", "role") == "note")
        check("the Back button has nothing extra to close for it (not an overlay)", page.evaluate("() => backTarget()") is None)

        # ---------- 4. Give feedback ----------
        print("\n--- 4. Give feedback ---")
        existing(page, {"feedbackFirstSeen": day(-10)})
        del outside[:]
        with context.expect_page() as new_tab:
            page.click("#feedback-card a.feedback-give")
        form = new_tab.value
        form.wait_for_load_state()
        check("the form opened in a new tab (the Tally address, with the version)", form.url == f"{FORM}?version={version}", form.url)
        form.close()
        page.wait_for_timeout(250)
        check("the card is gone", not card_shown(page))
        s = saved_settings(page)
        check("saved: answered for good, nothing waiting", s.get("feedbackHidden") == "done" and not s.get("feedbackShownOn"), s)
        check("the only request that left the app was the form itself",
              [u for u in outside if not u.endswith("favicon.ico")] == [f"{FORM}?version={version}"], outside)
        page.reload(); settle(page)
        check("after a reload it is still gone", not card_shown(page))
        patch_settings(page, feedbackFirstSeen=day(-400), feedbackNextAfter=day(-100))
        check("even long after, it never comes back", not card_shown(page))
        check("Settings -> Updates still has the link", (main_tab(page, "settings"), sub_tab(page, "updates"), page.is_visible("#feedback-link"))[2])

        # ---------- 5. Not now ----------
        print("\n--- 5. Not now ---")
        existing(page, {"feedbackFirstSeen": day(-10)})
        del notices[:]
        page.click("#feedback-card .feedback-later")
        page.wait_for_timeout(250)
        check("the card is gone", not card_shown(page))
        s = saved_settings(page)
        check("saved: ask again in 30 days, nothing else", s.get("feedbackNextAfter") == day(30) and not s.get("feedbackShownOn") and not s.get("feedbackHidden"), s)
        check("no message in the way", notices == [], notices)
        page.reload(); settle(page)
        check("after a reload it is still gone", not card_shown(page))
        patch_settings(page, feedbackNextAfter=day(29))
        check("29 days later: still waiting", not card_shown(page))
        patch_settings(page, feedbackNextAfter=day(1))
        check("tomorrow is the day: still waiting", not card_shown(page))
        patch_settings(page, feedbackNextAfter=day(0))
        check("on the day itself it shows again", card_shown(page))
        patch_settings(page, feedbackShownOn=None, feedbackNextAfter=day(-5))
        check("after the day it shows again", card_shown(page))
        # the keyboard works too: Tab to the button, then Enter
        page.focus("#feedback-card .feedback-later")
        check("Not now can take the focus", page.evaluate("() => document.activeElement.className") == "plain-button feedback-later")
        page.keyboard.press("Enter")
        page.wait_for_timeout(250)
        check("Enter on Not now hides it", not card_shown(page))
        check("and saves the wait", saved_settings(page).get("feedbackNextAfter") == day(30))
        patch_settings(page, feedbackShownOn=None, feedbackNextAfter=day(-1))
        page.focus("#feedback-card .feedback-never")
        page.keyboard.press("Space")
        page.wait_for_timeout(250)
        check("Space on Don't ask again works too", not card_shown(page) and saved_settings(page).get("feedbackHidden") == "never")

        # ---------- 6. Don't ask again ----------
        print("\n--- 6. Don't ask again ---")
        existing(page, {"feedbackFirstSeen": day(-10)})
        del notices[:]
        page.click("#feedback-card .feedback-never")
        page.wait_for_timeout(300)
        check("the card is gone", not card_shown(page))
        s = saved_settings(page)
        check("saved: never again", s.get("feedbackHidden") == "never" and not s.get("feedbackShownOn"), s)
        check("a plain message says so and where the link still is",
              len(notices) == 1 and "won't ask again" in notices[0] and "Settings" in notices[0] and "Updates" in notices[0], notices)
        page.reload(); settle(page)
        check("after a reload it is still gone", not card_shown(page))
        patch_settings(page, feedbackFirstSeen=day(-400), feedbackNextAfter=day(-100), feedbackShownOn=None)
        check("a year later it is still gone", not card_shown(page))
        check("Settings -> Updates still has Give feedback", (main_tab(page, "settings"), sub_tab(page, "updates"), page.is_visible("#feedback-link"))[2])

        # ---------- 7. Never twice in a row ----------
        print("\n--- 7. Never twice in a row ---")
        existing(page, {"feedbackFirstSeen": day(-10)})
        check("day 1: shown", card_shown(page))
        patch_settings(page, feedbackShownOn=day(-1))   # a day goes by, nobody answered
        check("day 2: not shown again", not card_shown(page))
        s = saved_settings(page)
        check("an unanswered card counts as Not now (30 days)", s.get("feedbackNextAfter") == day(30) and not s.get("feedbackShownOn"), s)
        page.reload(); settle(page)
        check("day 2, opened again: still not shown", not card_shown(page))
        check("the wait was not pushed back by the second visit", saved_settings(page).get("feedbackNextAfter") == day(30))
        patch_settings(page, feedbackShownOn=day(-4))   # seen days ago, never answered
        check("seen days ago and not answered: counts as Not now, not shown", not card_shown(page))
        patch_settings(page, feedbackShownOn=None, feedbackNextAfter=day(-1))
        check("30 days on: it can be shown once more", card_shown(page))

        # ---------- 8. Nothing is sent ----------
        print("\n--- 8. Nothing is sent ---")
        del outside[:]
        existing(page, {"feedbackFirstSeen": day(-10)})
        page.click("#feedback-card .feedback-later")
        page.wait_for_timeout(200)
        patch_settings(page, feedbackShownOn=None, feedbackNextAfter=None)
        page.click("#feedback-card .feedback-never")
        page.wait_for_timeout(300)
        main_tab(page, "units"); main_tab(page, "dashboard")
        check("nothing left the app while the card was shown, answered and reloaded", outside == [], outside)
        start = app.index("v25: ONE GENTLE")
        # v27: its section sits just before the Updates list, so stop where v27's begins.
        stop = app.find("v27: COUNTING VISITS", start)
        section = app[start:(stop if stop > 0 else app.index("const CHANGELOG", start))]
        check("the new code has no fetch, XMLHttpRequest, sendBeacon, WebSocket or image pings",
              not re.search(r"fetch\(|XMLHttpRequest|sendBeacon|WebSocket|new Image", section), section[:200])
        check("the card's code uses no inline handlers or eval", not re.search(r"onclick=|eval\(|new Function", section))
        backup = page.evaluate("() => JSON.stringify(backupData())")
        check("a backup does not carry the feedback dates or choice", not re.search(r"feedbackFirstSeen|feedbackHidden|feedbackNextAfter|feedbackShownOn", backup))
        check("the address is only read from the same FEEDBACK_URL as before", "feedbackAddress()" in section and section.count("tally.so") == 0)

        # ---------- 9. Saved data's shape ----------
        print("\n--- 9. Saved data's shape ---")
        existing(page, {"feedbackFirstSeen": day(-10), "someFutureSetting": {"a": 1}})
        s = saved_settings(page)
        check("settings the app doesn't know are kept, as an older version would keep ours",
              s.get("someFutureSetting") == {"a": 1} and s.get("feedbackShownOn") == day(0), s)
        check("DATA_VERSION stays 1 and is what is saved", s.get("dataVersion") == 1, s.get("dataVersion"))
        before = saved_settings(page)
        page.evaluate("() => { settings.paintSort = 'name'; saveSettings(); }")
        after = saved_settings(page)
        check("saving something else keeps the feedback keys", all(after.get(k) == before.get(k) for k in ("feedbackFirstSeen", "feedbackShownOn")), after)
        units_before = page.evaluate("() => localStorage.getItem('mini-tracker-models')")
        page.reload(); settle(page)
        check("saved units are untouched by all this", page.evaluate("() => localStorage.getItem('mini-tracker-models')") == units_before)
        existing(page, {"feedbackFirstSeen": "banana"})
        check("an unreadable first day is replaced with today, no card", saved_settings(page).get("feedbackFirstSeen") == day(0) and not card_shown(page))
        existing(page, {"feedbackFirstSeen": day(-10), "feedbackShownOn": 12345, "feedbackNextAfter": {"x": 1}, "feedbackHidden": "maybe"})
        check("odd saved values are ignored (card shows, nothing breaks)", card_shown(page) and saved_settings(page).get("feedbackShownOn") == day(0), saved_settings(page))
        existing(page, {"feedbackFirstSeen": day(5)})
        check("a first day in the future (clock moved back): no card, no errors", not card_shown(page))
        existing(page, {"feedbackFirstSeen": day(-10), "feedbackShownOn": day(1)})
        check("a 'shown on' day in the future: treated as not answered, no card", not card_shown(page))
        existing(page, {"feedbackFirstSeen": day(-10)})
        page.evaluate("() => localStorage.setItem('shades-of-grey-settings', 'not json')")
        page.reload(); settle(page)
        check("unreadable settings: the app still starts, and no card", not card_shown(page))

        # ---------- 10. Dark and light, 390 and 360 ----------
        print("\n--- 10. Dark and light at 390 and 360 px ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                existing(page, {"appearance": appearance, "feedbackFirstSeen": day(-10)})
                box = page.evaluate("""() => { const r = document.getElementById('feedback-card').getBoundingClientRect();
                    return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: window.innerWidth, h: window.innerHeight }; }""")
                check(f"{tag}: the card is inside the screen, on screen without scrolling",
                      box["l"] >= 0 and box["r"] <= box["w"] + 0.5 and box["b"] <= box["h"], box)
                sizes = page.evaluate("""() => [...document.querySelectorAll('#feedback-card a, #feedback-card button')]
                    .map(b => { const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), b.scrollWidth <= b.clientWidth + 1]; })""")
                check(f"{tag}: all three controls are at least 44 px tall and wide, and their words fit",
                      len(sizes) == 3 and all(w >= 44 and h >= 44 and fits for w, h, fits in sizes), sizes)
                check(f"{tag}: nothing scrolls sideways", no_sideways(page))
                col = page.evaluate("""() => { const card = document.getElementById('feedback-card');
                    const p = card.querySelector('p'), give = card.querySelector('a'), later = card.querySelector('.feedback-later');
                    return { text: getComputedStyle(p).color, card: getComputedStyle(card).backgroundColor,
                             giveFg: getComputedStyle(give).color, giveBg: getComputedStyle(give).backgroundColor,
                             laterFg: getComputedStyle(later).color }; }""")
                check(f"{tag}: the words are readable (contrast at least 4.5)",
                      contrast(rgb(col["text"]), rgb(col["card"])) >= 4.5 and contrast(rgb(col["giveFg"]), rgb(col["giveBg"])) >= 4.5
                      and contrast(rgb(col["laterFg"]), rgb(col["card"])) >= 4.5, col)
                if width == 390:
                    shot(page, f"v25-feedback-card-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 11. With the examples card, and Back ----------
        print("\n--- 11. With the examples card, and Back ---")
        fresh(page, {"feedbackFirstSeen": day(-10)})
        both = page.evaluate("""() => { const a = document.getElementById('examples-card-dash').getBoundingClientRect();
            const b = document.getElementById('feedback-card').getBoundingClientRect();
            return { exShown: !document.getElementById('examples-card-dash').classList.contains('hidden'),
                     fbShown: !document.getElementById('feedback-card').classList.contains('hidden'), exBottom: a.bottom, fbTop: b.top }; }""")
        check("a new start with a week behind it shows both cards", both["exShown"] and both["fbShown"], both)
        check("the feedback card sits below the examples card, not over it", both["fbTop"] >= both["exBottom"] - 0.5, both)
        page.click("#examples-card-dash .clear-examples")
        page.wait_for_timeout(250)
        check("clearing the examples leaves the feedback card alone", card_shown(page))
        check("the headline numbers are still on the Dashboard under the cards", page.is_visible("#done-percent"))
        page.click("#feedback-card .feedback-later")
        page.wait_for_timeout(250)
        check("answering it leaves the Dashboard as it was", not card_shown(page) and page.is_visible("#done-percent"))
        check("no sideways scroll", no_sideways(page))

        # ---------- 12. Help and Updates ----------
        print("\n--- 12. Help and Updates wording ---")
        fresh(page)
        main_tab(page, "settings")
        sub_tab(page, "help")
        help_text = page.evaluate("() => document.getElementById('help-feedback-prompt').textContent")
        check("Help explains the card (a week, the three buttons, 30 days, never two days running, nothing sent)",
              all(w in help_text for w in ["week", "Give feedback", "Not now", "30 days", "Don't ask again", "two days running", "Nothing is sent"]), help_text)
        privacy = page.evaluate("() => document.getElementById('privacy').textContent")
        check("Privacy says what the app saves and that it never leaves the device",
              "feedback card" in privacy and "never sent anywhere" in privacy, privacy[-400:])
        check("Help still says nothing you add is sent anywhere", "nothing you add is sent anywhere" in page.evaluate("() => document.getElementById('view-help').textContent"))
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")
        if page.evaluate("['v25'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates page has the v25 entry in plain words",
                  "v25" in updates and "Enjoying Minifolio?" in updates and "Don't ask again" in updates, updates[:500])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates page has the v25 entry in plain words')
        check("\"Tell us what you think\" is still there", "Tell us what you think" in updates)

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        check("no CSP errors", not csp, csp[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
