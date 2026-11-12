"""TH1 tests for Minifolio (four themes, and Classic as the sci-fi look). New behaviour only:
1. The theme list is exactly four (Classic, Parchment Codex, Grim Forge, Paint Bench) in the app, early.js and the Theme card.
2. A saved Blueprint or Rulebook theme loads as Classic (with and without app.js), with no error.
3. Restoring a backup that names Blueprint or Rulebook works and ends on Classic.
4. Classic's accent (ice cyan) and its borders pass contrast in light and dark: text 4.5 to 1, borders and controls 3 to 1;
   good, bad and warning stay green, red and amber, clearly apart from each other and from the cyan; the note colour is a cold violet-blue, clearly apart from muted grey.
5. Classic's title and number font (Oxanium) loads from the app's own site; body text keeps the system font; the removed fonts are gone.
6. Cards get thin lines and small corner marks drawn in CSS, with tighter corners and no resting transform.
7. The photo viewer and the camera keep their old colours in Classic, light and dark.
8. Classic at 320 px: nothing scrolls sideways.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import colorsys, json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch, tap_tab, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

FOUR = ["classic", "parchment", "forge", "bench"]
OLD_VIEWER = {"--background": "#0b1220", "--card": "#141d2f", "--accent": "#7dd3fc", "--note": "#c4b5fd", "--good": "#5eead4", "--border": "#22304a"}
GONE_FONTS = ["Barlow Condensed", "IBM Plex Sans Condensed", "Share Tech Mono", "Special Elite", "Courier Prime"]

def rgb(text):
    text = text.strip()
    if text.startswith("#"):
        return [int(text[i:i + 2], 16) for i in (1, 3, 5)]
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def ratio(a, b):
    return t.contrast(rgb(a), rgb(b))

def hue(c):
    r, g, b = [x / 255 for x in rgb(c)]
    return colorsys.rgb_to_hls(r, g, b)[0] * 360

def hue_gap(a, b):
    d = abs(hue(a) - hue(b)) % 360
    return min(d, 360 - d)

def fresh(page, settings, launch=False):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("(s) => { localStorage.clear(); localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }", settings)
    page.goto(t.URL)
    page.wait_for_function("() => typeof settings === 'object'")
    if not launch:
        leave_launch(page)

def tokens(page, names, selector=":root"):
    return page.evaluate("([s, n]) => { const c = getComputedStyle(document.querySelector(s)); return Object.fromEntries(n.map(k => [k, c.getPropertyValue(k).trim()])); }",
                         [selector, names])

def main():
    errors, dialogs, requests = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url))

        print("\n--- 1. Four themes ---")
        fresh(page, {"theme": "forge"})
        check("the app knows exactly four themes, Classic first", page.evaluate("Object.keys(THEMES)") == FOUR, page.evaluate("Object.keys(THEMES)"))
        check("the page and card colours are kept for the same four", sorted(page.evaluate("Object.keys(THEME_SURFACES)")) == sorted(FOUR))
        early = t.read("early.js")
        keys = re.findall(r"^\s{4}(\w+): \{ dark:", early[early.index("PAGE_COLOURS"):early.index("};")], re.M)
        check("early.js knows the same four", keys == FOUR, keys)
        squares = page.evaluate("() => [...document.querySelectorAll('#theme-card [data-theme-choice]')].map(b => b.dataset.themeChoice)")
        check("Settings shows four theme squares", squares == FOUR, squares)
        html = t.read("index.html")
        check("no Blueprint or Rulebook styles or buttons are left in the page", not re.search(r'data-t(?:heme-choice)?="(blueprint|rulebook)"', html))

        print("\n--- 2. A saved Blueprint or Rulebook theme loads as Classic ---")
        for old, mode in (("blueprint", "dark"), ("rulebook", "light")):
            fresh(page, {"theme": old, "appearance": mode})
            state = page.evaluate("""() => ({ t: document.documentElement.dataset.t, m: document.documentElement.dataset.m, theme: currentTheme(), setting: settings.theme,
                pressed: [...document.querySelectorAll('[data-theme-choice][aria-pressed="true"]')].map(b => b.dataset.themeChoice),
                bar: document.querySelector('meta[name=theme-color]').content, bg: getComputedStyle(document.body).backgroundColor })""")
            surf = page.evaluate("THEME_SURFACES.classic")[mode]["page"]
            check(f"a saved {old} ({mode}) opens as Classic {mode}, with the Classic square pressed",
                  state["t"] == "classic" and state["m"] == mode and state["theme"] == "classic" and state["setting"] == "classic" and state["pressed"] == ["classic"], state)
            check(f"…its page and top bar are Classic's {mode} page colour", rgb(state["bg"]) == rgb(surf) and state["bar"] == surf, state)
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        p2 = ctx2.new_page()
        p2.route("**/app.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body="window.__noApp = true;"))
        p2.goto(t.BASE + "manifest.json")
        p2.evaluate("localStorage.setItem('shades-of-grey-settings', JSON.stringify({ theme: 'rulebook' }))")
        p2.goto(t.URL)
        check("before app.js runs, early.js already marks a saved Rulebook as Classic", p2.evaluate("document.documentElement.dataset.t") == "classic")
        ctx2.close()

        print("\n--- 3. Backups that name a removed theme ---")
        fresh(page, {"theme": "forge"})
        backup = page.evaluate("backupData()")
        for old in ("blueprint", "rulebook"):
            fresh(page, {"theme": "forge"})
            data = dict(backup, theme=old)
            page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
            page.wait_for_timeout(400)
            if page.query_selector('.dialog button:has-text("Yes")'):
                page.click('.dialog button:has-text("Yes")')
            page.wait_for_function("() => JSON.parse(localStorage.getItem('shades-of-grey-settings')).theme !== 'forge'", timeout=5000)
            saved = page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-settings')).theme")
            check(f"restoring a backup with theme {old!r} works and ends on Classic (saved and on the page)",
                  saved == "classic" and page.evaluate("document.documentElement.dataset.t") == "classic", (saved, page.evaluate("document.documentElement.dataset.t")))
        check("no error during the loads and restores", not errors, errors[:2])

        print("\n--- 4. Contrast and status colours in Classic ---")
        names = ["--background", "--card", "--border", "--text", "--muted", "--accent", "--on-accent", "--good", "--bad", "--warn", "--caution", "--note", "--danger", "--toast-action"]
        for mode in ("dark", "light"):
            fresh(page, {"theme": "classic", "appearance": mode})
            g = tokens(page, names)
            bg, card = g["--background"], g["--card"]
            check(f"{mode}: the accent is an ice cyan (blue-green, hue 175 to 195)", 175 <= hue(g["--accent"]) <= 195, (g["--accent"], round(hue(g["--accent"]))))
            low = [(n, s, round(ratio(g[n], s), 2)) for n in ("--accent", "--text", "--muted", "--good", "--bad", "--warn", "--caution", "--note", "--danger") for s in (bg, card) if ratio(g[n], s) < 4.5]
            check(f"{mode}: accent and status text read at 4.5 to 1 on the page and the cards", not low, low)
            check(f"{mode}: button text on the accent reads at 4.5 to 1", ratio(g["--on-accent"], g["--accent"]) >= 4.5, (g["--on-accent"], g["--accent"]))
            check(f"{mode}: borders reach 3 to 1 on the page and the cards", min(ratio(g["--border"], bg), ratio(g["--border"], card)) >= 3, g["--border"])
            check(f"{mode}: the toast's Undo reads at 4.5 to 1 on the toast", ratio(g["--toast-action"], g["--text"]) >= 4.5)
            ctrl = page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.primary-button')), c = getComputedStyle(document.querySelector('.plain-button'));
                return { fill: s.backgroundColor, edge: c.borderTopColor }; }""")
            check(f"{mode}: the main button's fill and a plain button's edge reach 3 to 1 on the cards",
                  ratio(ctrl["fill"], card) >= 3 and ratio(ctrl["edge"], card) >= 3, ctrl)
            gaps = {"good-accent": hue_gap(g["--good"], g["--accent"]), "good-bad": hue_gap(g["--good"], g["--bad"]),
                    "caution-bad": hue_gap(g["--caution"], g["--bad"]), "caution-good": hue_gap(g["--caution"], g["--good"]), "bad-accent": hue_gap(g["--bad"], g["--accent"])}
            check(f"{mode}: good is green (hue 100 to 150), bad red, warning amber", 100 <= hue(g["--good"]) <= 150 and (hue(g["--bad"]) <= 15 or hue(g["--bad"]) >= 345)
                  and 25 <= hue(g["--caution"]) <= 50, [round(hue(g[n])) for n in ("--good", "--bad", "--caution")])
            check(f"{mode}: good, bad, warning and the cyan are at least 25 degrees of hue apart", min(gaps.values()) >= 25, gaps)
            sat = lambda c: colorsys.rgb_to_hls(*[x / 255 for x in rgb(c)])[2]
            note_gaps = [round(hue_gap(g["--note"], g[n])) for n in ("--accent", "--good", "--bad", "--caution")]
            check(f"{mode}: the note colour is a cold violet-blue (hue 225 to 245), clearly coloured next to muted grey, and apart from cyan, good, bad and warning",
                  225 <= hue(g["--note"]) <= 245 and sat(g["--note"]) >= 0.5 > sat(g["--muted"]) and min(note_gaps) >= 25
                  and g["--note"].lower() not in ("#c4b5fd", "#6d28d9"), (g["--note"], round(hue(g["--note"])), note_gaps))

            print(f"\n--- 5 to 7. Fonts, panels and the photo viewer ({mode}) ---")
            page.evaluate("document.fonts.ready")
            look = page.evaluate("""() => { const h1 = getComputedStyle(document.querySelector('h1')), h2 = getComputedStyle(document.querySelector('.card h2')),
                big = document.querySelector('.group-button strong'), body = getComputedStyle(document.body);
                return { h1: h1.fontFamily, h2: h2.fontFamily, big: big ? getComputedStyle(big).fontFamily : 'none', body: body.fontFamily,
                         oxanium: document.fonts.check('600 16px Oxanium') }; }""")
            # TH6 (v129): Classic's body text is now Chakra Petch and its numbers Azeret Mono (each look has its own fonts); the titles stay Oxanium.
            check(f"{mode}: titles use Oxanium with a real fallback; body text and numbers use Classic's own TH6 fonts",
                  look["h1"].startswith("Oxanium") and look["h2"].startswith("Oxanium") and look["big"].startswith('"Azeret Mono"')
                  and look["h1"].rstrip().endswith("sans-serif") and look["body"].startswith('"Chakra Petch"') and look["body"].rstrip().endswith("sans-serif"), look)
            check(f"{mode}: Oxanium has loaded", look["oxanium"])
            card = page.evaluate("""() => { const c = getComputedStyle(document.querySelector('#headline-card'));   /* AB5 (v134): the corner marks are on the headline card and the Mentor window only, so this reads the headline card */
                return { img: c.backgroundImage, radius: c.borderTopLeftRadius, width: c.borderTopWidth, transform: c.transform, scale: c.scale }; }""")
            check(f"{mode}: cards have a 1 px line, 6 px corners and eight corner-mark strokes drawn in the accent",
                  card["width"] == "1px" and card["radius"] == "6px" and card["img"].count("linear-gradient") == 8
                  and rgb(re.search(r"rgb\([^)]*\)", card["img"]).group(0)) == rgb(g["--accent"]), card)
            # AB5 (v134): every other Classic card is a plain 1 px line; the marks are new behaviour tested in test_v134_ab5.
            check(f"{mode}: other cards are a plain 1 px line with no corner marks",
                  page.evaluate("""() => { const c = [...document.querySelectorAll('#view-dashboard .card')].find(e => e.id !== 'headline-card'); return !c || getComputedStyle(c).backgroundImage === 'none'; }"""))
            check(f"{mode}: no resting transform or scale on cards or buttons", page.evaluate("""() => [...document.querySelectorAll('.card, .primary-button, .plain-button, .chip')]
                .every(e => { const s = getComputedStyle(e); return s.transform === 'none' && (s.scale === 'none' || s.scale === '1'); })"""))
            edge = page.evaluate("""() => { const c = [...document.querySelectorAll('#history-card .chip')].find(e => e.getAttribute('aria-pressed') !== 'true' && !e.style.getPropertyValue('--chip-colour'));
                return c ? getComputedStyle(c).borderLeftColor : null; }""")
            check(f"{mode}: a plain pill has no coloured left stripe (v136, AT-53: its left edge is the same line as the other three)", edge and edge == page.evaluate("""() => getComputedStyle([...document.querySelectorAll('#history-card .chip')].find(e => e.getAttribute('aria-pressed') !== 'true' && !e.style.getPropertyValue('--chip-colour'))).borderTopColor"""), edge)
            for sel in (".viewer", "#scan-camera"):
                # the camera box is only built when the camera opens, so a bare one stands in for it here (only its colours are read)
                page.evaluate("(s) => { if (!document.querySelector(s)) { const d = document.createElement('div'); if (s[0] === '#') d.id = s.slice(1); else d.className = s.slice(1); d.hidden = true; document.body.appendChild(d); } }", sel)
                got = tokens(page, list(OLD_VIEWER), sel)
                check(f"{mode}: {sel} keeps its old colours", all(rgb(got[k]) == rgb(v) for k, v in OLD_VIEWER.items()), got)

        print("\n--- 5. Fonts come from the app's own site ---")
        fonts = [u for u in requests if ".woff2" in u]
        check("every font request goes to the app's own site, and Oxanium was one of them",
              fonts and all(u.startswith(t.BASE) for u in fonts) and any("oxanium-latin-600-normal.woff2" in u for u in fonts), fonts)
        style = html[html.index("<style>"):html.index("</style>")]
        face = re.search(r"@font-face \{ font-family: 'Oxanium';[^}]*\}", style)
        check("Oxanium is one Latin woff2 file with font-display swap", face and "font-display: swap" in face.group(0) and "url(fonts/oxanium-latin-600-normal.woff2)" in face.group(0)
              and "U+0000-00FF" in face.group(0))
        path = os.path.join(t.ROOT, "fonts", "oxanium-latin-600-normal.woff2")
        check("the Oxanium file is a real woff2 under 20 KB, and its licence (SIL OFL) is listed",
              open(path, "rb").read(4) == b"wOF2" and os.path.getsize(path) < 20_000 and re.search(r"## Oxanium\n\n```\n.*SIL Open Font License", t.read("fonts/LICENSES.md"), re.S))
        files = " ".join(os.listdir(os.path.join(t.ROOT, "fonts")))
        check("the five fonts only Blueprint and Rulebook used are gone (files, styles and licences)",
              not any(f"'{n}'" in style or f"## {n}\n" in t.read("fonts/LICENSES.md") for n in GONE_FONTS)
              and not re.search(r"barlow-condensed|ibm-plex|share-tech|special-elite|courier-prime", files))

        print("\n--- 8. Classic at 320 px ---")
        page.set_viewport_size({"width": 320, "height": 640})
        for mode in ("dark", "light"):
            fresh(page, {"theme": "classic", "appearance": mode})
            wide = []
            for name in ("units", "settings"):   # the two busiest sections; the others were checked by eye at 320, 360 and 390 px
                tap_tab(page, name); quiet(page)
                if not t.no_sideways(page): wide.append(name)
            check(f"Classic {mode} at 320 px: no section scrolls sideways", not wide, wide)

        check("no page errors and no browser pop-ups", not errors and not dialogs, (errors[:2], dialogs[:2]))
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
