"""v47 tests for Minifolio (themes).

What changed:
 (a) Five new themes, each with a dark and a light version: Blueprint, Parchment Codex, Grim Forge, Paint Bench and Rulebook.
     The look before v47 stays as the sixth theme, Classic, and is the default for everyone. Theme (settings.theme) and
     Appearance (dark, light, match my phone) are separate; the look on screen is the theme in the current mode.
 (b) Settings has a Theme card: one row of square buttons, each a tiny page in its own theme with the theme's name in its
     own title font. The row scrolls sideways on narrow phones.
 (c) Fonts are our own files in fonts/ (Latin, woff2). The security policy is unchanged. The service worker keeps each font
     after its first use, in a store that survives updates, and saves none at install.
 (d) early.js puts the theme and mode on the page before it is drawn and sets the phone's top-bar colour from the theme.
 (e) Stage colours are fitted to the active theme's cards and page, so they stay readable in every theme.
 (f) The theme travels in backups; a restore only accepts a known theme name.

Checks:
1. Versions, the v47 Updates entry, the security policy, Help wording.
2. The theme table: every theme and mode defines every token; page and card colours agree between index.html, early.js and app.js.
3. Fonts: every file exists and is used, every family has a fallback stack and a licence, nothing loads from elsewhere.
4. goodTheme and the saved setting: bad values are refused and fall back to Classic; early.js marks the page before app.js runs.
5. The Theme buttons: each one switches the whole page (colours, fonts, top bar), is pressed alone, is saved, and survives a reload;
   each square shows its own theme in the current mode, and follows Match my phone.
6. Contrast, in every theme and mode: text 4.5:1, borders 3:1, button text 4.5:1, status colours 4.5:1, stage colours readable.
7. Classic is unchanged: its colours and sizes are the v46 values.
8. The photo viewer stays on the Classic dark colours.
9. Backups: the theme is saved, restored, and an unknown theme in a backup is ignored.
10. Service worker: fonts are kept after first use and survive an update; nothing is saved at install.
11. Phone widths (390 and 360): nothing scrolls sideways in any theme; the Theme row scrolls on its own.
12. No page errors, no browser pop-ups, no CSP errors.
TH1 (2 Nov 2026): Blueprint and Rulebook were removed and Classic became the sci-fi look (ice cyan accent, Oxanium for titles
and numbers, steel borders at 3:1, 6 px corners). The checks below that named those two themes, or said Classic is the v46 look,
were updated to the four themes and the new Classic; tests/test_v124_th1.py covers the TH1 behaviour itself.
TH6 (3 Nov 2026): every look has its own fonts (Classic: Oxanium, Chakra Petch, Azeret Mono; Grim Forge: Anton, Barlow; Parchment Codex:
Grenze Gotisch, EB Garamond with lining figures; Paint Bench: Atkinson Hyperlegible, DM Mono, Permanent Marker on the tape, Big Shoulders
Stencil for the name), each with a local fallback sized to match, and the Theme squares use four tiny files with only their names' letters.
The font checks below that named the old fonts, counted the old files or said Classic's body text is the system font were updated to
match; the files the looks no longer use stay in fonts/ until they are removed, so they are listed in RETIRED. tests/test_v129_th6.py
covers the TH6 behaviour itself.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from launch_helpers import quiet, open_settings, tap_tab
from launch_helpers import leave_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t     # the shared page helpers

URL, read, shot, no_sideways, ROOT = t.URL, t.read, t.shot, t.no_sideways, t.ROOT
results = []
# TH6: font files no look uses any more. They stay on disk (and in fonts/LICENSES.md) until someone removes them.
RETIRED = ["barlow-semi-condensed-latin-400-normal.woff2", "barlow-semi-condensed-latin-500-normal.woff2", "eb-garamond-latin-400-italic.woff2",
           "eb-garamond-latin-400-normal.woff2", "eb-garamond-latin-500-normal.woff2", "im-fell-english-latin-400-italic.woff2",
           "im-fell-english-latin-400-normal.woff2", "teko-latin-500-normal.woff2", "teko-latin-600-normal.woff2"]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

THEMES = ["classic", "parchment", "forge", "bench"]   # TH1: Blueprint and Rulebook were removed
NAMES = {"classic": "Classic", "parchment": "Parchment Codex", "forge": "Grim Forge", "bench": "Paint Bench"}
NEW = THEMES[1:]
COLOUR_TOKENS = ["--background", "--card", "--track", "--border", "--text", "--muted", "--accent", "--on-accent", "--heading-colour",
                 "--wordmark-colour", "--danger", "--shadow", "--badge-bg", "--accent-wash", "--accent-wash-hover", "--note", "--note-wash",
                 "--good", "--good-wash", "--bad", "--bad-wash", "--warn", "--caution", "--wish", "--grey-status", "--chip-on",
                 "--toast-action", "--series-added", "--series-painted", "--toast-ring", "--basket-deep", "--swatch-edge",
                 "--card-shadow", "--texture", "--frame", "--rule"]
STRUCTURE_TOKENS = ["--font-heading", "--font-body", "--font-num", "--num-style", "--radius-card", "--radius-control", "--radius-box",
                    "--radius-small", "--radius-bar", "--border-width", "--border-style", "--heading-weight", "--heading-transform",
                    "--heading-tracking", "--heading-size", "--wordmark-size", "--body-size", "--card-pad", "--texture-size"]
# TH1: Classic keeps the v46 page, card and text colours; its border and accent are the TH1 ones.
CLASSIC = {"dark": {"--background": "#0b1220", "--card": "#141d2f", "--border": "#4968a0", "--text": "#dbe4f0", "--accent": "#5fe0ea"},
           "light": {"--background": "#e9eff6", "--card": "#f8fafc", "--border": "#6c89ab", "--text": "#0f1b2d", "--accent": "#06707b"}}

def hexrgb(h):
    h = h.strip().lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

def to_rgb(text):
    text = text.strip()
    if text.startswith("#"): return hexrgb(text)
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def contrast(a, b):
    return t.contrast(to_rgb(a), to_rgb(b))

def blocks(css):
    """{selector: {token: value}} for the theme blocks in index.html."""
    out = {}
    for m in re.finditer(r'(\[data-t="(\w+)"\](?:\[data-m="(\w+)"\])?) \{(.*?)\n    \}', css, re.S):
        out.setdefault((m.group(2), m.group(3)), {}).update(dict(re.findall(r"(--[\w-]+): ([^;]+);", m.group(4))))
    return out

def fresh(page, settings=None, units=None):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("""([s, u]) => { localStorage.clear();
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u)); }""", [settings, units])
    page.goto(URL)
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    leave_launch(page)   # U4b: tap through the start page

def tab(page, name):
    tap_tab(page, name)
    quiet(page)

def var(page, name, selector=":root"):
    return page.evaluate("([s, n]) => getComputedStyle(document.querySelector(s)).getPropertyValue(n).trim()", [selector, name])

def main():
    errors, csp, popups = [], [], []
    html, sw, early = read("index.html"), read("sw.js"), read("early.js")
    style = html[html.index("<style>"):html.index("</style>")]
    table = blocks(style)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions, policy, wording ----------
        print("\n--- 1. Versions, the security policy and the wording ---")
        fresh(page)
        m = re.search(r'const VERSION = "v([\d.]+)"', sw)
        check("no inline script added to the page", not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html))
        check("Help names Settings → Theme and every theme", "Settings → Theme" in html and all(f"<strong>{n}</strong>" in html for n in NAMES.values()))
        check("Help says the theme is saved in backups", "Your Appearance, Theme, colour set and Custom colours are saved" in html)
        card = html[html.index('id="theme-card"'):html.index('id="theme-card"') + 2000]
        check("the Theme card has a title and the squares only (no subtitle or helper text)",
              card.count("<h2>Theme</h2>") == 1 and 'class="hint"' not in card.split("</div>\n      </div>")[0])

        # ---------- 2. The theme table ----------
        print("\n--- 2. The theme table ---")
        for th in NEW:
            missing = [k for k in STRUCTURE_TOKENS if k not in table.get((th, None), {})]
            check(f"{NAMES[th]}: every structure token is defined", not missing, missing)
            for mode in ("dark", "light"):
                # TH3: a theme may set a token once for both modes in its shared block (Parchment Codex draws one --texture from per-mode ink colours)
                missing = [k for k in COLOUR_TOKENS if k not in table.get((th, mode), {}) and k not in table.get((th, None), {})]
                check(f"{NAMES[th]} {mode}: every colour token is defined", not missing, missing)
        classic_struct = re.search(r':root, \[data-t="classic"\], \.viewer, #scan-camera \{(.*?)\n    \}', style, re.S)
        missing = [k for k in STRUCTURE_TOKENS if not classic_struct or k + ":" not in classic_struct.group(1)]
        check("Classic defines every structure token (with the v46 values)", not missing, missing)
        pages = json.loads(re.sub(r"(\w+):", r'"\1":', re.search(r"const PAGE_COLOURS = (\{.*?\n  \});", early, re.S).group(1)).replace(",\n  }", "\n  }"))
        surf = page.evaluate("THEME_SURFACES")
        ok = all(pages[th][md] == surf[th][md]["page"] for th in THEMES for md in ("dark", "light"))
        for th in NEW:
            for md in ("dark", "light"):
                ok = ok and table[(th, md)]["--background"] == pages[th][md] and table[(th, md)]["--card"] == surf[th][md]["card"]
        check("page and card colours agree between index.html, early.js and app.js", ok and pages["classic"]["dark"] == "#0b1220", pages)
        check("early.js and app.js know the same four themes", sorted(pages) == sorted(THEMES) == sorted(page.evaluate("Object.keys(THEMES)")))

        # ---------- 3. Fonts ----------
        print("\n--- 3. Fonts ---")
        urls = re.findall(r"url\(fonts/([\w-]+\.woff2)\)", style)
        on_disk = sorted(f for f in os.listdir(os.path.join(ROOT, "fonts")) if f.endswith(".woff2"))
        # TH6: 22 files in use (14 added, 9 retired but kept on disk, see RETIRED); before TH6 it was 17 files, all in use
        check("every font file named in the page exists, and every file in fonts/ is used (apart from the retired ones)",
              sorted(urls) == sorted(set(on_disk) - set(RETIRED)) and len(urls) == 22 and set(RETIRED) <= set(on_disk), (len(urls), len(on_disk)))
        check("every font file is a real woff2 and small (latin subset)",
              all(open(os.path.join(ROOT, "fonts", f), "rb").read(4) == b"wOF2" and os.path.getsize(os.path.join(ROOT, "fonts", f)) < 120_000 for f in on_disk))
        # TH6: the four Theme-square files hold only their names' letters (no range needed), and the eleven fallbacks are the phone's own fonts (local(), no file)
        faces = re.findall(r"@font-face \{[^}]*\}", style)
        files, fallbacks = [f for f in faces if "url(fonts/" in f], [f for f in faces if "url(" not in f]
        check("every @font-face file uses font-display: swap and the latin range (the name-only files apart); the rest are sized local fallbacks",
              len(files) == 22 and all("font-display: swap" in f for f in files) and sum("unicode-range: U+0000-00FF" in f for f in files) == 18
              and len(fallbacks) == 11 and all("local(" in f and "size-adjust" in f for f in fallbacks) and len(faces) == 33, (len(files), len(fallbacks)))
        licences = read("fonts/LICENSES.md")
        families = sorted(set(re.findall(r"font-family: '([^']+)'; font-style", style)))
        check("fonts/LICENSES.md holds a licence for every family", all(f"## {f}" in licences for f in families) and len(families) == 15, families)   # TH6: 9 families before   # TH1: 24 files and 13 families before; Oxanium added, five families removed
        stacks = [v for (th, md), b in table.items() if md is None for k, v in b.items() if k in ("--font-heading", "--font-body", "--font-num")]
        check("every theme font stack ends in a generic fallback", all(re.search(r"(sans-serif|serif|monospace|cursive)\s*$", s) for s in stacks), stacks)
        check("no font, stylesheet or script loads from another website", not re.search(r"(href|src)=\"https?://", html.replace("https://dim3ry.goatcounter.com", "")) and "@import" not in style)

        # ---------- 4. goodTheme and the saved setting ----------
        print("\n--- 4. The setting ---")
        check("goodTheme accepts the four themes", page.evaluate("THEMES_OK = Object.keys(THEMES).every(goodTheme)"))
        bad = page.evaluate("""() => ['', 'Blueprint', 'BLUEPRINT', 'neon', '__proto__', 'constructor', 'toString', 'hasOwnProperty', null, undefined, 5, {}, []]
                               .filter(v => goodTheme(v)).map(String)""")
        check("goodTheme refuses wrong names, lookalikes, built-in names and non-text", bad == [], bad)
        for v in ["neon", "__proto__", 42, None]:
            fresh(page, settings={"theme": v})
            check(f"a saved theme of {v!r} falls back to Classic", page.evaluate("document.documentElement.dataset.t") == "classic"
                  and page.evaluate("settings.theme") == "classic")
        # early.js alone (app.js not loaded): the page is already marked
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        p2 = ctx2.new_page()
        p2.route("**/app.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body="window.__noApp = true;"))
        p2.goto(t.BASE + "manifest.json")
        p2.evaluate("localStorage.setItem('shades-of-grey-settings', JSON.stringify({ theme: 'parchment', appearance: 'light' }))")
        p2.goto(URL)
        marks = p2.evaluate("""() => ({ t: document.documentElement.dataset.t, m: document.documentElement.dataset.m,
            bar: document.querySelector('meta[name=theme-color]').content, bg: getComputedStyle(document.body).backgroundColor })""")
        check("early.js marks the theme and mode before app.js runs (no Classic flash)", marks["t"] == "parchment" and marks["m"] == "light", marks)
        check("…and sets the phone's top bar to the theme's page colour", marks["bar"] == "#d8c59a", marks)
        check("…and the page is already the theme's colour", to_rgb(marks["bg"]) == hexrgb("#d8c59a"), marks)
        ctx2.close()

        # ---------- 5. The Theme buttons ----------
        print("\n--- 5. The Theme buttons ---")
        fresh(page)
        check("Classic is the default", page.evaluate("document.documentElement.dataset.t") == "classic"
              and page.get_attribute('[data-theme-choice="classic"]', "aria-pressed") == "true")
        tab(page, "settings")
        squares = page.evaluate("""() => [...document.querySelectorAll('#theme-card .theme-swatch')].map(b => ({ k: b.dataset.themeChoice, text: b.textContent.trim(),
            type: b.type, w: b.getBoundingClientRect().width, h: b.getBoundingClientRect().height, top: Math.round(b.getBoundingClientRect().top) }))""")
        check("four square buttons in one row, Classic first, each labelled with its theme's name",
              [s["k"] for s in squares] == THEMES and all(s["text"] == NAMES[s["k"]] for s in squares)
              and len({s["top"] for s in squares}) == 1 and all(abs(s["w"] - s["h"]) < 1 and s["w"] >= 44 for s in squares), squares)
        check("the row sits right after the Appearance card", page.evaluate("document.getElementById('appearance-card').nextElementSibling.id") == "theme-card")
        fonts = page.evaluate("""() => [...document.querySelectorAll('#theme-card .ts-name')].map(n => getComputedStyle(n).fontFamily)""")
        want = ["Oxanium Theme Name", "Grenze Gotisch Theme Name", "Anton Theme Name", "Permanent Marker Theme Name"]   # TH6: the title faces, cut down to each name's letters
        check("each name is written in its own theme's title font", all(w in f for w, f in zip(want, fonts)), fonts)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        loaded = page.evaluate("""() => ['700 16px "Oxanium Theme Name"', '16px "Grenze Gotisch Theme Name"', '600 16px "Anton Theme Name"', '16px "Permanent Marker Theme Name"'].map(f => document.fonts.check(f))""")
        check("those title fonts load from our own files", all(loaded), loaded)
        backs = page.evaluate("""() => [...document.querySelectorAll('#theme-card .theme-swatch')].map(b => getComputedStyle(b).backgroundColor)""")
        check("each square is drawn in its own theme (its own page colour, dark mode)",
              [to_rgb(b) for b in backs] == [hexrgb(page.evaluate("THEME_SURFACES")[k]["dark"]["page"]) for k in THEMES], backs)
        for th in THEMES:
            page.click(f'[data-theme-choice="{th}"]')
            state = page.evaluate("""() => ({ t: document.documentElement.dataset.t, pressed: [...document.querySelectorAll('[data-theme-choice]')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.themeChoice),
                saved: JSON.parse(localStorage.getItem('shades-of-grey-settings')).theme, bar: document.querySelector('meta[name=theme-color]').content,
                bg: getComputedStyle(document.body).backgroundColor, h1: getComputedStyle(document.querySelector('h1')).fontFamily,
                appearance: settings.appearance })""")
            surf = page.evaluate("THEME_SURFACES")[th]["dark"]
            check(f"{NAMES[th]}: the page switches, only its square is pressed, it is saved, Appearance is untouched",
                  state["t"] == th and state["pressed"] == [th] and state["saved"] == th and state["appearance"] == "dark", state)
            check(f"{NAMES[th]}: the page colour and the phone's top bar follow the theme", to_rgb(state["bg"]) == hexrgb(surf["page"]) and state["bar"] == surf["page"], state)
            title = ["Oxanium", "Grenze Gotisch", "Anton", "Big Shoulders Stencil"][THEMES.index(th)]   # TH6: new title faces for Parchment Codex and Grim Forge
            check(f"{NAMES[th]}: the title uses the theme's title font", title in state["h1"], state["h1"])
        page.reload(); page.wait_for_function("() => typeof APP_VERSION === 'string'")
        check("the chosen theme survives a reload", page.evaluate("document.documentElement.dataset.t") == "bench")
        # modes: the squares and the page follow Appearance, and Match my phone
        tab(page, "settings")
        page.click('[data-appearance-choice="light"]')
        state = page.evaluate("""() => ({ m: document.documentElement.dataset.m, squares: [...document.querySelectorAll('.theme-swatch')].map(b => b.dataset.m),
            bar: document.querySelector('meta[name=theme-color]').content })""")
        check("Light: the page and every square switch to light, the top bar to Paint Bench light",
              state["m"] == "light" and set(state["squares"]) == {"light"} and state["bar"] == "#e0e4d8", state)   # TH4: Paint Bench light is the lighter, warmer desk (#cfe0d4 before)
        page.click('[data-appearance-choice="auto"]')
        page.emulate_media(color_scheme="dark"); page.wait_for_timeout(150)
        check("Match my phone (phone dark): page and squares are dark", page.evaluate("document.documentElement.dataset.m") == "dark"
              and set(page.evaluate("[...document.querySelectorAll('.theme-swatch')].map(b => b.dataset.m)")) == {"dark"})
        page.emulate_media(color_scheme="light"); page.wait_for_timeout(150)
        check("Match my phone (phone light): page and squares switch to light, theme kept",
              page.evaluate("document.documentElement.dataset.m") == "light" and page.evaluate("document.documentElement.dataset.t") == "bench"
              and set(page.evaluate("[...document.querySelectorAll('.theme-swatch')].map(b => b.dataset.m)")) == {"light"})
        page.emulate_media(color_scheme="dark")
        # keyboard
        page.focus('[data-theme-choice="parchment"]'); page.keyboard.press("Enter")
        check("a square works from the keyboard", page.evaluate("document.documentElement.dataset.t") == "parchment")

        # ---------- 6. Contrast in every theme and mode ----------
        print("\n--- 6. Contrast ---")
        for th in NEW:
            for mode in ("dark", "light"):
                fresh(page, settings={"theme": th, "appearance": mode})
                g = lambda n: var(page, n)
                bg, card = g("--background"), g("--card")
                low = []
                for n in ("--text", "--muted", "--accent", "--heading-colour", "--wordmark-colour", "--good", "--bad", "--warn", "--caution",
                          "--wish", "--grey-status", "--note", "--danger"):
                    for s in (bg, card):
                        if contrast(g(n), s) < 4.5: low.append((n, round(contrast(g(n), s), 2)))
                check(f"{NAMES[th]} {mode}: every text colour reads at 4.5:1 on the page and the cards", not low, low)
                check(f"{NAMES[th]} {mode}: borders reach 3:1 on the page and the cards",
                      min(contrast(g("--border"), bg), contrast(g("--border"), card)) >= 3, (g("--border"), bg, card))
                # TH3: buttons are filled with --accent-fill (the accent itself in every theme but Parchment Codex dark, which uses a deeper red)
                check(f"{NAMES[th]} {mode}: button text reads at 4.5:1 on the accent fill", contrast(g("--on-accent"), g("--accent-fill")) >= 4.5, (g("--on-accent"), g("--accent-fill")))
                check(f"{NAMES[th]} {mode}: the toast's Undo reads at 4.5:1 on the toast", contrast(g("--toast-action"), g("--text")) >= 4.5)
                check(f"{NAMES[th]} {mode}: both graph lines reach 3:1 on the cards and differ",
                      min(contrast(g("--series-added"), card), contrast(g("--series-painted"), card)) >= 3 and g("--series-added") != g("--series-painted"))
                sem = [g(n) for n in ("--good", "--bad", "--warn", "--caution", "--note")]
                check(f"{NAMES[th]} {mode}: good, bad, warn, caution and note are five different colours", len(set(sem)) == 5, sem)
                stages = page.evaluate("Array.from({ length: STAGES.length }, (_, i) => getComputedStyle(document.documentElement).getPropertyValue(`--stage-${i}`).trim())")
                surface = card if mode == "dark" else bg
                faint = [(c, round(contrast(c, surface), 2)) for c in stages if contrast(c, surface) < 4.5]
                check(f"{NAMES[th]} {mode}: every stage colour reads at 4.5:1 on this theme's {'cards' if mode == 'dark' else 'page'}", not faint, faint)

        # ---------- 7. Classic is unchanged ----------
        print("\n--- 7. Classic (TH1: the sci-fi look; page, cards, text and sizes as before) ---")
        for mode in ("dark", "light"):
            fresh(page, settings={"appearance": mode})
            got = {n: var(page, n) for n in CLASSIC[mode]}
            check(f"Classic {mode}: the base colours are the v46 page, card and text with the TH1 border and accent", all(to_rgb(got[n]) == hexrgb(v) for n, v in CLASSIC[mode].items()), got)
            look = page.evaluate("""() => { const h1 = getComputedStyle(document.querySelector('h1')), card = getComputedStyle(document.querySelector('.card')),
                body = getComputedStyle(document.body), btn = getComputedStyle(document.querySelector('.primary-button'));
                return { h1size: h1.fontSize, h1font: h1.fontFamily, h1colour: h1.color, h1weight: h1.fontWeight, radius: card.borderTopLeftRadius,
                         border: card.borderTopWidth + ' ' + card.borderTopStyle, shadow: card.boxShadow, pad: card.paddingTop, body: body.fontFamily,
                         texture: body.backgroundImage, btnColour: btn.color, btnFont: btn.fontFamily, btnWeight: btn.fontWeight }; }""")
            check(f"Classic {mode}: title, cards, body and main button keep the v46 sizes and body font (TH1: Oxanium title at 600, 6 px corners)",
                  look["h1size"] == "24px" and look["h1font"].startswith("Oxanium") and look["h1weight"] == "600"
                  and to_rgb(look["h1colour"]) == hexrgb(CLASSIC[mode]["--accent"]) and look["radius"] == "6px" and look["border"] == "1px solid"
                  and look["shadow"] == "none" and look["pad"] == "16px" and look["body"].startswith('"Chakra Petch"') and look["texture"] == "none"
                  and to_rgb(look["btnColour"]) == hexrgb(CLASSIC[mode]["--background"]) and look["btnWeight"] == "600", look)
            # TH6: Classic's body (Chakra Petch) and numbers (Azeret Mono) have their own fonts too
            # v129: TH6's "<name> Fallback" faces are local() stand-ins with matched metrics (nothing is downloaded), so they are left out of the count
            got = page.evaluate("[...document.fonts].filter(f => f.status === 'loaded' && !/ Fallback$/.test(f.family.replace(/\"/g, ''))).map(f => f.family.replace(/\"/g, ''))")
            check(f"Classic {mode}: only its own fonts (Oxanium, Chakra Petch, Azeret Mono) are downloaded", set(got) <= {"Oxanium", "Chakra Petch", "Azeret Mono"}, got)

        # ---------- 8. The photo viewer stays Classic dark ----------
        print("\n--- 8. Photo viewer ---")
        for th in ("parchment", "classic"):   # TH1: Rulebook was removed; Classic's own colours changed but the viewer keeps the old ones
            for mode in ("dark", "light"):
                fresh(page, settings={"theme": th, "appearance": mode})
                vals = {n: var(page, n, ".viewer") for n in ("--background", "--card", "--text", "--accent")}
                check(f"{NAMES[th]} {mode}: the photo viewer keeps the old Classic dark colours",
                      to_rgb(vals["--background"]) == hexrgb("#0b1220") and to_rgb(vals["--card"]) == hexrgb("#141d2f") and to_rgb(vals["--accent"]) == hexrgb("#7dd3fc"), vals)

        # ---------- 9. Backups ----------
        print("\n--- 9. Backups ---")
        fresh(page, settings={"theme": "forge"})
        check("a backup holds the theme", page.evaluate("backupData().theme") == "forge")
        fresh(page, settings={"theme": "classic"})
        check("backupData always writes a known theme", page.evaluate("goodTheme(backupData().theme)"))
        # restore through the real Restore backup flow (a file chosen in the file box)
        backup = page.evaluate("backupData()")
        for given, expect in (("bench", "bench"), ("Neon", "forge"), ("__proto__", "forge"), (None, "forge")):
            fresh(page, settings={"theme": "forge"})
            data = dict(backup); data["theme"] = given
            if given is None: data.pop("theme")
            page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
            page.wait_for_timeout(500)
            if page.query_selector('.dialog button:has-text("Yes")'): page.click('.dialog button:has-text("Yes")')   # "Replace your current units…?"
            page.wait_for_timeout(500)
            done = page.evaluate("JSON.parse(localStorage.getItem('shades-of-grey-settings')).theme")
            check(f"restoring a backup with theme {given!r}: the theme is {expect!r} (saved and on the page)",
                  done == expect and page.evaluate("document.documentElement.dataset.t") == expect, (done, page.evaluate("document.documentElement.dataset.t")))

        # ---------- 10. Service worker ----------
        print("\n--- 10. Service worker ---")
        check("sw.js keeps fonts in their own store, which updates don't clear",
              'const FONT_CACHE = "shades-of-grey-fonts"' in sw and "name !== FONT_CACHE" in sw)
        check("sw.js does not save any font at install", "woff2" not in sw[sw.index("const APP_FILES"):sw.index("];", sw.index("const APP_FILES"))])
        swctx = browser.new_context(viewport={"width": 390, "height": 844})
        sp = swctx.new_page()
        sp.goto(t.BASE + "manifest.json")
        sp.evaluate("localStorage.setItem('shades-of-grey-settings', JSON.stringify({ theme: 'classic' }))")
        sp.goto(URL)
        sp.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
        leave_launch(sp)   # U4b: tap through the start page
        sp.reload(); sp.wait_for_function("() => typeof APP_VERSION === 'string'")
        sp.evaluate("document.fonts.ready"); sp.wait_for_timeout(300)
        fonts_before = sp.evaluate("caches.open('shades-of-grey-fonts').then(c => c.keys()).then(k => k.map(r => r.url.split('/').pop()))")
        classic_files = {"oxanium-latin-600-normal.woff2", "chakra-petch-latin-400-normal.woff2", "chakra-petch-latin-600-normal.woff2", "azeret-mono-latin-500-normal.woff2"}
        check("only Classic's own fonts are saved while Classic is in use (Settings not opened; TH6: Oxanium, Chakra Petch, Azeret Mono)",
              "oxanium-latin-600-normal.woff2" in fonts_before and set(fonts_before) <= classic_files, fonts_before)
        open_settings(sp); sp.click('[data-theme-choice="bench"]')
        sp.evaluate("document.fonts.ready"); sp.wait_for_timeout(800)
        saved = sp.evaluate("caches.open('shades-of-grey-fonts').then(c => c.keys()).then(k => k.map(r => r.url.split('/').pop()))")
        check("after choosing Paint Bench, its fonts are saved for offline use",
              any("big-shoulders-stencil" in f for f in saved) and any("atkinson-hyperlegible" in f for f in saved), saved)   # TH6: Atkinson Hyperlegible replaced Barlow Semi Condensed
        swctx.set_offline(True)
        sp.reload(); sp.wait_for_function("() => typeof APP_VERSION === 'string'")
        sp.evaluate("document.fonts.ready"); sp.wait_for_timeout(500)
        check("offline, Paint Bench still draws in its own fonts",
              sp.evaluate("document.documentElement.dataset.t") == "bench" and sp.evaluate("document.fonts.check('16px \"Big Shoulders Stencil\"')"))
        swctx.set_offline(False)
        # an update (new VERSION) clears the app store but keeps fonts
        names = sp.evaluate("""async () => { await caches.open('shades-of-grey-v1'); return (await caches.keys()); }""")
        check("the font store sits beside the app store", "shades-of-grey-fonts" in names, names)
        swctx.close()

        # ---------- 11. Phone widths ----------
        print("\n--- 11. Phone widths ---")
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 800})
            for th in NEW:
                for mode in ("dark", "light"):
                    fresh(page, settings={"theme": th, "appearance": mode})
                    wide = []
                    for name in ("dashboard", "units", "recipes", "compendium", "settings"):
                        tab(page, name)
                        if not no_sideways(page): wide.append(name)
                    row = page.evaluate("() => { const r = document.querySelector('.theme-row'); return { scrolls: r.scrollWidth > r.clientWidth, inside: r.getBoundingClientRect().right <= window.innerWidth + 1 }; }")
                    check(f"{NAMES[th]} {mode} {width}px: no tab scrolls sideways; the Theme row scrolls inside its card", not wide and row["inside"], (wide, row))
                    if width == 390 and mode == "dark":
                        page.locator("#theme-card").scroll_into_view_if_needed()
                        shot(page, f"v47-theme-card-{th}-{mode}.png")
        page.set_viewport_size({"width": 1280, "height": 900})
        fresh(page, settings={"theme": "parchment"})
        tab(page, "settings")
        check("on a laptop all four squares fit without scrolling",
              page.evaluate("() => { const r = document.querySelector('.theme-row'); return r.scrollWidth <= r.clientWidth + 1; }"))
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 12. Clean run ----------
        print("\n--- 12. A clean run ---")
        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not popups, popups[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
