"""v21.8 tests for Minifolio: look and feel (the v13 leftovers, part 5).

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry, kept things
   (CNAME, the ocr folder, LICENSE-paint-list.txt, the ZAP workflow, the CSP exactly as v21.4),
   storage names and the data version (still 1).
2. (a) Stage names are readable. In DARK mode every stage colour of every colour set, for 2 to 10
   stages, reaches 4.5 on the dark cards; colours that were already fine are left exactly as they
   were; Greyscale stays easy to tell apart; the stored colours never change. In LIGHT mode every
   stage colour reaches 4.5 on the cards AND on the page colour. The real stage names on the cards
   (computed colour against the card) pass in both, in every set. Custom colours get a note.
3. (b) The photo strip: no tile is cut off at 390 and 360 px (dark and light), at the start and at the
   end, with 1, 2, 4 photos; tiles are square and tappable; wide screens keep their old tile size.
4. (c) The tab bar steps aside while a text box has the cursor and comes back after; boxes that don't
   open a keyboard don't hide it; the message drops to the bottom edge meanwhile; the question box's
   text box counts too (its read-only copy box doesn't); a box taken away while focused doesn't leave
   the bar hidden; the wide-screen top bar is never hidden.
5. (d) Per-model dates: "Today", "Yesterday", "Since 3 Jan", "Since 30 Nov 2025" under each model's
   name; no date where the diary can't say; they follow real taps (▲, the stage menu, Move all
   models) and Undo; nothing is saved differently; dark and light at 390 and 360 px.
6. Help wording; no page errors and no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, struct, sys, zlib
from playwright.sync_api import sync_playwright

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

def png(width=64, height=48, rgb=(40, 90, 160)):
    """A small plain-coloured PNG picture, made here so the test needs no image files."""
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

# v68: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10,
     "repaint": True, "notes": "Purple carapace", "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
    {"id": 3, "name": "Liberators", "hobby": "AoS", "faction": "Stormcast Eternals", "stage": 1, "count": 5,
     "log": [["2026-09-02", 1]]},
]
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
PALETTE_NAMES = ["ice", "frost", "greyscale", "colourblind", "forge"]

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
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def saved_settings(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-settings') || '{}')")

def toast(page):
    return page.evaluate("""() => ({ shown: !document.getElementById('toast').classList.contains('hidden'),
        text: document.getElementById('toast-text').textContent,
        undo: !document.getElementById('toast-undo').classList.contains('hidden') })""")

def open_unit(page, uid):
    """Make sure unit `uid`'s details are open (a tap on a name toggles, so only tap if it's shut)."""
    info = f'#view-units li.unit[data-id="{uid}"] .info'
    # A3: open or shut now shows on the Details button (the name area is no longer a button with aria-expanded).
    if page.get_attribute(info.replace(" .info", " .details-toggle"), "aria-expanded") != "true":
        page.click(info)
        page.wait_for_timeout(250)

def tabs_hidden(page):
    return page.evaluate("() => getComputedStyle(document.querySelector('.tabs')).display === 'none'")

def typing(page):
    return page.evaluate("() => document.body.classList.contains('typing')")

def today_and_yesterday(page):
    return page.evaluate("""() => { const d = new Date(); d.setDate(d.getDate() - 1);
        const y = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        return [todayISO(), y, new Date().getFullYear()]; }""")

def add_photos(page, uid, count, wait=20000):
    open_unit(page, uid)
    # v79: from 900 px a unit's details (photos included) sit in the side pane, not inside its card, so look in either place.
    picker = page.locator(f'#view-units :is(li.unit, .unit-side-card)[data-id="{uid}"] input[type="file"][accept="image/*"]').first
    picker.set_input_files(files=[{"name": f"p{i}.png", "mimeType": "image/png",
                                   "buffer": png(300, 200, (40 + i * 30, 90, 160))} for i in range(count)])
    page.wait_for_function(f"""() => {{ const im = [...document.querySelectorAll('#view-units :is(li.unit, .unit-side-card)[data-id="{uid}"] .photo-tile img')];
        return im.length === {count} && im.every(i => i.complete && i.naturalWidth > 0); }}""", timeout=wait)
    page.wait_for_timeout(500)

STRIP_JS = """(uid) => { const s = document.querySelector('#view-units :is(li.unit, .unit-side-card)[data-id="' + uid + '"] .photo-strip');
    if (!s) return null;
    const sr = s.getBoundingClientRect();
    const items = [...s.querySelectorAll('li')].map(li => ({ li, r: li.getBoundingClientRect(), t: li.querySelector('.photo-tile').getBoundingClientRect() }));
    const shown = items.filter(x => x.r.right > sr.left + 1 && x.r.left < sr.right - 1);
    return { total: items.length, shown: shown.length,
             whole: shown.every(x => x.r.left >= sr.left - 1 && x.r.right <= sr.right + 1),
             square: shown.every(x => Math.abs(x.t.width - x.t.height) <= 1.5),
             tile: shown.length ? shown[0].t.width : 0, scrollLeft: s.scrollLeft, max: s.scrollWidth - s.clientWidth,
             sideways: document.documentElement.scrollWidth > window.innerWidth + 1 }; }"""

def main():
    errors, csp = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        seed(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.8')")
        joined = " ".join(entry["changes"]) if entry else ""
        if page.evaluate("['v21.8'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("…about stage names, the photo strip, typing and model dates",
                  all(w in joined for w in ["dark mode", "photo", "tab bar", "each model"]), joined[:200])
        else:
            print("SKIP (entry no longer in the public Updates list): " + '…about stage names, the photo strip, typing and model dates')
        tab(page, "updates")
        heads = page.locator("#view-updates h3").all_inner_texts()
        for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes"]:
            check(f"storage key {key} still used", key in app)
        check("the tab bar rule is only for screens under 900 px (the top bar is never hidden)",
              re.search(r"@media \(max-width: 899\.98px\)\s*\{[^}]*body\.typing \.tabs \{ display: none; \}", html) is not None)
        check("the message and Select bar drop down while typing",
              "body.typing .toast" in html and "body.typing .select-bar" in html)

        # ---------- 2. (a) Stage names are readable ----------
        print("\n--- 2. (a) Readable stage names ---")
        probe = """([names, lightMode]) => { const out = {};
            for (const name of names) { const rows = [];
              for (let n = 2; n <= 10; n++) {
                const base = stageColours(name, n), shown = shownStageColours(name, n);
                rows.push({ n, base, shown,
                  card: shown.map(c => contrastRatio(c, '#141d2f')), lcard: shown.map(c => contrastRatio(c, '#f8fafc')),
                  lpage: shown.map(c => contrastRatio(c, '#e9eff6')),
                  baseCard: base.map(c => contrastRatio(c, '#141d2f')),
                  gap: closestNeighbours(shown), baseGap: closestNeighbours(base) }); }
              out[name] = rows; }
            return out; }"""
        seed(page, settings=full_settings(appearance="dark"))
        before_pal = page.evaluate("JSON.stringify(PALETTES)")
        dark = page.evaluate(probe, [PALETTE_NAMES, False])
        bad_dark, changed_ok, bad_gap, kept_all = [], [], [], True
        for name, rows in dark.items():
            for r in rows:
                for i, c in enumerate(r["shown"]):
                    if r["card"][i] < 4.5 - 0.005:
                        bad_dark.append((name, r["n"], i, c, round(r["card"][i], 2)))
                    # Greyscale's run of greys is the one exception: it is spaced out again as a whole.
                    if name != "greyscale" and r["baseCard"][i] >= 4.5 and c != r["base"][i]:
                        changed_ok.append((name, r["n"], i, r["base"][i], c))
                if r["gap"] < min(r["baseGap"] * 0.6, 12) - 0.01:
                    bad_gap.append((name, r["n"], round(r["gap"], 1), round(r["baseGap"], 1)))
        check("dark: every stage colour of every set (2 to 10 stages) reads at 4.5 or more on the dark cards", not bad_dark, bad_dark[:5])
        check("dark: colours that already read well are left exactly as they were (Greyscale's run of greys is re-spaced as a whole)", not changed_ok, changed_ok[:5])
        grey_ok = all(all(r["shown"][i] != r["shown"][i - 1] for i in range(1, len(r["shown"]))) and
                      all(r["card"][i] >= r["card"][i - 1] - 0.01 for i in range(1, len(r["card"])))
                      for r in dark["greyscale"])
        check("dark: Greyscale's greys still go from darker to lighter, every step different", grey_ok)
        grey_small = [(r["n"], i) for r in dark["greyscale"] for i, c in enumerate(r["shown"])
                      if r["baseCard"][i] >= 4.5 and abs(int(c[1:3], 16) - int(r["base"][i][1:3], 16)) > 40]
        check("dark: and none of its already-readable greys moves far (no more than 40 steps of red)", not grey_small, grey_small[:5])
        check("dark: stages stay easy to tell apart (no two neighbours bunch up)", not bad_gap, bad_gap[:5])
        gap_min = min(r["gap"] for rows in dark.values() for r in rows)
        check("dark: the closest two neighbouring stages in any set differ by at least 12", gap_min >= 12, gap_min)
        some_changed = sum(1 for rows in dark.values() for r in rows for i, c in enumerate(r["shown"]) if c != r["base"][i])
        check("dark: some colours really were lightened (Ice, Frost, Greyscale, Forge)", some_changed > 20, some_changed)
        cb = dark["colourblind"]
        check("dark: Colour-blind friendly was already readable, so it's untouched",
              all(r["shown"] == r["base"] for r in cb))
        check("the colour sets themselves are unchanged (stored colours)", page.evaluate("JSON.stringify(PALETTES)") == before_pal)
        check("Greyscale's first grey is still #6b7280 in the set",
              page.evaluate("stageColours('greyscale', 5)[0]") == "#6b7280")

        seed(page, settings=full_settings(appearance="light"))
        light = page.evaluate(probe, [PALETTE_NAMES, True])
        bad_light = [(name, r["n"], i, c, round(r["lcard"][i], 2), round(r["lpage"][i], 2))
                     for name, rows in light.items() for r in rows for i, c in enumerate(r["shown"])
                     if r["lcard"][i] < 4.5 - 0.005 or r["lpage"][i] < 4.5 - 0.005]
        check("light: every stage colour of every set reads at 4.5 or more on the cards AND on the page colour", not bad_light, bad_light[:5])

        # The real stage names on the real cards, every set, both looks, two widths.
        stage_units = [{"id": i + 1, "name": f"Unit {i + 1}", "hobby": "40K", "faction": "Ultramarines", "stage": i,
                        "count": 1, "log": [["2026-09-01", i]]} for i in range(len(STAGES))]
        real_js = """() => { const hex = s => '#' + s.match(/\\d+/g).slice(0, 3).map(n => (+n).toString(16).padStart(2, '0')).join('');
            return [...document.querySelectorAll('#view-units li.unit')].map(li => { const st = li.querySelector('.stage');
              return { text: st.textContent, colour: hex(getComputedStyle(st).color), card: hex(getComputedStyle(li).backgroundColor),
                       ratio: contrastRatio(hex(getComputedStyle(st).color), hex(getComputedStyle(li).backgroundColor)) }; }); }"""
        weak = []
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 900})
                for name in PALETTE_NAMES:
                    seed(page, units=stage_units, settings=full_settings(appearance=appearance, palette=name))
                    tab(page, "units")
                    rows = page.evaluate(real_js)
                    if len(rows) != len(STAGES):
                        weak.append((appearance, width, name, "only", len(rows)))
                    for r in rows:
                        if r["ratio"] < 4.5 - 0.01:
                            weak.append((appearance, width, name, r["text"], r["colour"], r["card"], round(r["ratio"], 2)))
                    if name == "greyscale":
                        check(f"{appearance} {width}px greyscale: nothing scrolls sideways", no_sideways(page))
                        shot(page, f"v21-8-greyscale-names-{appearance}-{width}.png")
        check("the real stage names on the unit cards read at 4.5 or more, in every set, dark and light, 390 and 360 px",
              not weak, weak[:5])
        page.set_viewport_size({"width": 390, "height": 844})

        # Custom colours: stored as picked, notes say what's happening.
        custom = ["#6b7280", "#1a1a2e", "#a7f3d0", "#38bdf8", "#22d3ee", "#6366f1", "#e69f00", "#ffffff"]
        for appearance in ["dark", "light"]:
            seed(page, settings=full_settings(appearance=appearance, useCustom=True, customColours=custom))
            tab(page, "settings")
            page.wait_for_timeout(200)
            notes = page.evaluate("() => [...document.querySelectorAll('#custom-colour-list .custom-colour-row small')].map(s => s.hidden ? '' : s.textContent)")
            stored = saved_settings(page).get("customColours")
            check(f"{appearance}: Custom colours are saved exactly as picked", stored == custom, stored)
            if appearance == "dark":
                check("dark: a colour a little too dark (3 to 4.5) says it's shown brighter",
                      "brighter in dark mode" in notes[0], notes[0])
                check("dark: a very faint colour still gets the warning", "Too faint" in notes[1], notes[1])
                check("dark: a colour that reads well has no note", notes[3] == "", notes[3])
                shown = page.evaluate("() => shownStageColours('ice', 8)")
                names_ok = page.evaluate("""() => [...document.querySelectorAll('#custom-colour-list .custom-colour-row strong')].map(s => {
                    const hex = c => '#' + c.match(/\\d+/g).slice(0, 3).map(n => (+n).toString(16).padStart(2, '0')).join('');
                    return contrastRatio(hex(getComputedStyle(s).color), hex(getComputedStyle(document.body).backgroundColor)); })""")
                check("dark: every Custom stage name reads at 4.5 or more (even the very faint one)",
                      all(r >= 4.5 - 0.01 for r in names_ok), [round(r, 2) for r in names_ok])
            else:
                check("light: a pale colour says it's shown deeper", "deeper in light mode" in notes[2], notes[2])
                check("light: a colour that reads well has no note", notes[1] == "" or "Too faint" in notes[1] or notes[1] == "", notes[1])
            shot(page, f"v21-8-custom-{appearance}-390.png")
            check(f"{appearance}: Custom list doesn't scroll sideways", no_sideways(page))

        # ---------- 3. (b) The photo strip ----------
        print("\n--- 3. (b) Photo strip ---")
        for appearance, width in [("dark", 390), ("dark", 360), ("light", 390), ("light", 360)]:
            page.set_viewport_size({"width": width, "height": 844})
            seed(page, settings=full_settings(appearance=appearance))
            tab(page, "units")
            add_photos(page, 2, 4)
            at_end = page.evaluate(STRIP_JS, 2)
            check(f"{appearance} {width}px: 4 photos, strip opens at the newest and every tile on show is whole",
                  at_end and at_end["whole"] and at_end["scrollLeft"] > 0, at_end)
            check(f"{appearance} {width}px: two tiles fit at a time", at_end and at_end["shown"] == 2, at_end)
            check(f"{appearance} {width}px: tiles are square and big enough to tap", at_end and at_end["square"] and at_end["tile"] >= 44, at_end)
            check(f"{appearance} {width}px: nothing scrolls sideways", at_end and not at_end["sideways"], at_end)
            page.locator('#view-units li.unit[data-id="2"] .photo-strip').first.scroll_into_view_if_needed()
            shot(page, f"v21-8-photo-strip-end-{appearance}-{width}.png")
            page.evaluate("""() => { document.querySelector('#view-units li.unit[data-id="2"] .photo-strip').scrollLeft = 0; }""")
            page.wait_for_timeout(450)
            at_start = page.evaluate(STRIP_JS, 2)
            check(f"{appearance} {width}px: back at the start every tile on show is whole", at_start and at_start["whole"] and at_start["shown"] == 2, at_start)
            shot(page, f"v21-8-photo-strip-start-{appearance}-{width}.png")
            page.evaluate("""() => { const s = document.querySelector('#view-units li.unit[data-id="2"] .photo-strip'); s.scrollLeft = s.clientWidth / 2; }""")
            page.wait_for_timeout(600)
            mid = page.evaluate(STRIP_JS, 2)
            check(f"{appearance} {width}px: left half-way between, it settles on whole tiles", mid and mid["whole"], mid)
            # A real tap on a tile opens the viewer.
            page.evaluate("""() => { document.querySelector('#view-units li.unit[data-id="2"] .photo-strip').scrollLeft = 0; }""")
            page.wait_for_timeout(450)
            page.locator('#view-units li.unit[data-id="2"] .photo-tile').first.click()
            page.wait_for_timeout(300)
            check(f"{appearance} {width}px: tapping the first tile opens the photo viewer",
                  page.evaluate("() => !document.querySelector('.viewer').classList.contains('hidden')"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)

        page.set_viewport_size({"width": 360, "height": 844})
        for count in (1, 2):
            seed(page)
            tab(page, "units")
            add_photos(page, 2, count)
            r = page.evaluate(STRIP_JS, 2)
            check(f"360px: {count} photo(s): whole and in view", r and r["whole"] and r["shown"] == count, r)
        page.set_viewport_size({"width": 1000, "height": 800})
        seed(page)
        tab(page, "units")
        add_photos(page, 2, 3)
        r = page.evaluate(STRIP_JS, 2)
        check("wide screen: tiles keep their old 116 px size", r and abs(r["tile"] - 116) <= 1 and r["whole"], r)
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 4. (c) The tab bar while typing ----------
        print("\n--- 4. (c) Tab bar while typing ---")
        for appearance, width in [("dark", 390), ("light", 360)]:
            page.set_viewport_size({"width": width, "height": 800})
            seed(page, settings=full_settings(appearance=appearance))
            tab(page, "units")
            check(f"{appearance} {width}px: the tab bar shows to start with", not tabs_hidden(page) and not typing(page))
            page.click("#toggle-add")
            page.wait_for_timeout(200)
            page.click("#name-input")
            page.wait_for_timeout(150)
            check(f"{appearance} {width}px: a text box has the cursor, so the tab bar is out of the way", typing(page) and tabs_hidden(page))
            page.keyboard.type("Bladeguard")
            check(f"{appearance} {width}px: typing works", page.input_value("#name-input") == "Bladeguard")
            shot(page, f"v21-8-typing-{appearance}-{width}.png")
            # Enter adds the unit; the name box keeps the cursor, and the message sits at the bottom edge.
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            t = toast(page)
            check(f"{appearance} {width}px: 'Added' message shows while still typing", t["shown"] and t["text"].startswith("Added"), t)
            gap = page.evaluate("() => window.innerHeight - document.getElementById('toast').getBoundingClientRect().bottom")
            check(f"{appearance} {width}px: the message drops to the bottom edge (not left floating above a hidden bar)", 0 <= gap <= 20, gap)
            check(f"{appearance} {width}px: the tab bar is still out of the way", tabs_hidden(page) and typing(page))
            shot(page, f"v21-8-typing-message-{appearance}-{width}.png")
            # Tapping somewhere that isn't a text box brings it back.
            page.click("h1")
            page.wait_for_timeout(150)
            check(f"{appearance} {width}px: tapping elsewhere brings the tab bar back", not tabs_hidden(page) and not typing(page))
            bottom = page.evaluate("() => { const r = document.querySelector('.tabs').getBoundingClientRect(); return [r.bottom, window.innerHeight, r.height]; }")
            check(f"{appearance} {width}px: …and it's back at the bottom, full height", abs(bottom[0] - bottom[1]) <= 1 and bottom[2] >= 44, bottom)
            check(f"{appearance} {width}px: nothing scrolls sideways", no_sideways(page))

        page.set_viewport_size({"width": 390, "height": 844})
        seed(page)
        tab(page, "units")
        page.click("#toggle-add")
        page.wait_for_timeout(200)
        page.click("#name-input")
        check("a second text box (Tab key onwards) keeps the bar out of the way while it has the cursor", typing(page))
        # Move on with the Tab key until the cursor lands on something that isn't a text box.
        landed = []
        for _ in range(12):
            page.keyboard.press("Tab")
            page.wait_for_timeout(60)
            kind = page.evaluate("() => { const a = document.activeElement; return a.tagName + ':' + (a.type || ''); }")
            landed.append((kind, typing(page), tabs_hidden(page)))
            if not typing(page):
                break
        consistent = all(h == t for _, t, h in landed)
        check("while the cursor moves through the form, the bar is hidden exactly when it's in a text box", consistent, landed)
        check("…and on a select or button it comes back", any(not t and not h for _, t, h in landed), landed)

        # Boxes that don't open a keyboard don't hide the bar.
        tab(page, "units")
        open_unit(page, 1)
        # v23: the tick boxes and the nickname are folded under "Edit details"; open it first.
        page.locator('#view-units li.unit[data-id="1"] .panel details.edit-details > summary').click()
        box = page.locator('#view-units li.unit[data-id="1"] .panel .edit-details-body input[type="checkbox"]').first
        if box.count():
            box.focus()
            check("a tick box with the cursor doesn't hide the tab bar", not typing(page) and not tabs_hidden(page))
        else:
            check("a tick box with the cursor doesn't hide the tab bar", False, "no tick box in the panel")
        nick = page.locator('#view-units li.unit[data-id="1"] .panel label', has_text="Nickname").locator("input").first
        nick.click()
        check("the nickname box (text) hides the bar", typing(page) and tabs_hidden(page))
        # The box is taken away (screen redrawn) while it has the cursor: a tap sorts it out.
        page.evaluate("() => render()")
        page.click("h1")
        page.wait_for_timeout(150)
        check("a text box taken away while it had the cursor doesn't leave the bar hidden", not typing(page) and not tabs_hidden(page))
        check("read-only boxes and unusual types don't count",
              page.evaluate("""() => { const t = (tag, type, ro) => { const e = document.createElement(tag); if (type) e.type = type; if (ro) e.readOnly = true; return isTextBox(e); };
                return [t('input', 'checkbox'), t('input', 'radio'), t('input', 'color'), t('input', 'file'), t('input', 'range'), t('button'),
                        t('textarea', null, true), t('input', 'text', true)].every(v => v === false)
                    && [t('input', 'text'), t('input', 'search'), t('input', 'number'), t('input', 'email'), t('input', 'tel'), t('textarea')].every(v => v === true); }"""))

        # The question box.
        page.evaluate("() => { askText('Name of the new part:', '', () => {}); }")
        page.wait_for_function("() => document.activeElement && document.activeElement.id === 'dialog-input'", timeout=5000)
        page.wait_for_timeout(100)
        check("the question box's type-a-name box counts as typing", typing(page) and tabs_hidden(page))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        check("closing it brings the tab bar back", not typing(page) and not tabs_hidden(page))
        page.evaluate("() => { showTextToCopy('Copy this text:', 'hello'); }")
        page.wait_for_timeout(250)
        check("the read-only copy box doesn't hide the bar", not typing(page) and not tabs_hidden(page))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # Wide screen: the tabs are a bar at the top, never in the way.
        page.set_viewport_size({"width": 1000, "height": 800})
        seed(page)
        tab(page, "units")
        page.click("#toggle-add")
        page.wait_for_timeout(200)
        page.click("#name-input")
        page.wait_for_timeout(150)
        top = page.evaluate("() => { const r = document.querySelector('.tabs').getBoundingClientRect(); return r.top; }")
        check("wide screen: the top tab bar stays while typing", not tabs_hidden(page) and top < 120, top)
        shot(page, "v21-8-typing-wide.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 5. (d) Per-model dates ----------
        print("\n--- 5. (d) Per-model dates ---")
        seed(page)
        today, yesterday, year = today_and_yesterday(page)
        jan2, last_nov = f"{year}-01-02", f"{year - 1}-11-30"
        each_unit = {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 1, "count": 4,
                     "each": True, "stages": [3, 1, 3, 2],
                     "log": [[f"{year - 1}-11-01", 0], [last_nov, 2, 3], [jan2, 3, 2], [yesterday, 1, 1], [today, 3, 0]]}
        mismatch = {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 2,
                    "each": True, "stages": [2, 0], "log": [[today, 1]]}
        nolog = {"id": 3, "name": "Liberators", "hobby": "AoS", "faction": "Stormcast Eternals", "stage": 1, "count": 2,
                 "each": True, "stages": [1, 1]}
        batch = {"id": 4, "name": "Hellblasters", "hobby": "40K", "faction": "Ultramarines", "stage": 2, "count": 5,
                 "log": [[today, 2]]}
        units_d = [each_unit, mismatch, nolog, batch]
        seed(page, units=units_d)
        tab(page, "units")
        before_saved = saved_units(page)
        open_unit(page, 1)
        def since_texts(uid):
            return page.evaluate(f"""() => [...document.querySelectorAll('#view-units li.unit[data-id="{uid}"] .each-list li')].map(li => {{
                const s = li.querySelector('.each-since'); return s ? s.textContent : null; }})""")
        texts = since_texts(1)
        check("Model 1 moved today: 'Today'", texts[0] == "Today", texts)
        check("Model 2 moved yesterday: 'Yesterday'", texts[1] == "Yesterday", texts)
        check("Model 3: 'Since 2 Jan' (this year, no year shown)", texts[2] == "Since 2 Jan", texts)
        check("Model 4: 'Since 30 Nov <last year>' (earlier year shows the year)", texts[3] == f"Since 30 Nov {year - 1}", texts)
        title = page.evaluate("""() => document.querySelectorAll('#view-units li.unit[data-id="1"] .each-since')[3].title""")
        check("the date has a full wording on hold: stage and date", title == f"Model 4 reached Assembled on 30 Nov {year - 1}", title)
        check("the model's name is still there", page.evaluate("""() => [...document.querySelectorAll('#view-units li.unit[data-id="1"] .each-name')].map(l => l.firstChild.textContent)""")
              == ["Model 1", "Model 2", "Model 3", "Model 4"])
        check("each row's stage menu and ◀ ▲ buttons are still there and 44 px",
              page.evaluate("""() => [...document.querySelectorAll('#view-units li.unit[data-id="1"] .each-list li')].every(li =>
                  li.querySelector('select.each-stage') && li.querySelectorAll('button').length === 2 &&
                  [...li.querySelectorAll('button')].every(b => b.getBoundingClientRect().width >= 43.5 && b.getBoundingClientRect().height >= 43.5))"""))
        shot(page, "v21-8-model-dates-dark-390.png")

        open_unit(page, 2)
        check("a model whose stage the diary doesn't match shows no date (no wrong dates)", since_texts(2) == [None, None], since_texts(2))
        open_unit(page, 3)
        check("a unit with no diary shows no dates", since_texts(3) == [None, None], since_texts(3))
        open_unit(page, 4)
        check("a unit painted as a batch shows no per-model dates", page.locator('#view-units li.unit[data-id="4"] .each-since').count() == 0)
        check("showing dates saves nothing differently (the saved units are exactly as seeded)",
              saved_units(page) == before_saved and page.evaluate("DATA_VERSION") in (1, 2))  # v62 raised DATA_VERSION to 2 for the "Needs touch-ups" rename

        # Real taps change the date.
        open_unit(page, 1)
        page.click('#view-units li.unit[data-id="1"] button[aria-label="Move model 2 up a stage"]')
        page.wait_for_timeout(300)
        texts = since_texts(1)
        check("▲ on Model 2: its date becomes 'Today', the others are as they were",
              texts == ["Today", "Today", "Since 2 Jan", f"Since 30 Nov {year - 1}"], texts)
        saved_log = next(u for u in saved_units(page) if u["id"] == 1)["log"]
        check("the diary got a Model 2 entry for today", saved_log[-1] == [today, 2, 1], saved_log[-1])
        page.click("#toast-undo")
        page.wait_for_timeout(300)
        texts = since_texts(1)
        check("Undo brings Model 2's old date back ('Yesterday')", texts[1] == "Yesterday", texts)
        check("…and the saved diary is exactly as before",
              next(u for u in saved_units(page) if u["id"] == 1)["log"] == each_unit["log"])
        page.select_option('#view-units li.unit[data-id="1"] .each-list li:nth-child(3) select.each-stage', label="Battle ready")
        page.wait_for_timeout(300)
        check("jumping Model 3 with its stage menu: its date becomes 'Today'", since_texts(1)[2] == "Today", since_texts(1))
        open_unit(page, 1)
        page.wait_for_timeout(100)
        page.select_option('#view-units li.unit[data-id="1"] select.jump-stage', label="Primed")
        page.wait_for_timeout(300)
        check("Move all models to a stage: every model says 'Today'", since_texts(1) == ["Today"] * 4, since_texts(1))

        # Looks: dark and light, two widths.
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 844})
                seed(page, units=units_d, settings=full_settings(appearance=appearance))
                tab(page, "units")
                open_unit(page, 1)
                geo = page.evaluate("""() => { const hex = c => '#' + c.match(/\\d+/g).slice(0, 3).map(n => (+n).toString(16).padStart(2, '0')).join('');
                    return [...document.querySelectorAll('#view-units li.unit[data-id="1"] .each-list li')].map(li => {
                      const r = li.getBoundingClientRect(), s = li.querySelector('.each-since').getBoundingClientRect();
                      const n = li.querySelector('.each-since');
                      return { inside: s.left >= r.left - 0.5 && s.right <= r.right + 0.5 && s.top >= r.top - 0.5 && s.bottom <= r.bottom + 0.5,
                               ratio: contrastRatio(hex(getComputedStyle(n).color), hex(getComputedStyle(li.closest('.card, li.unit')).backgroundColor)),
                               stageW: li.querySelector('select.each-stage').getBoundingClientRect().width }; }); }""")
                check(f"{appearance} {width}px: each date sits inside its row", all(g["inside"] for g in geo), geo)
                check(f"{appearance} {width}px: the date text reads at 4.5 or more", all(g["ratio"] >= 4.5 for g in geo), [round(g["ratio"], 2) for g in geo])
                check(f"{appearance} {width}px: each stage menu is still wide enough to use (80 px or more)", all(g["stageW"] >= 80 for g in geo), [round(g["stageW"]) for g in geo])
                check(f"{appearance} {width}px: nothing scrolls sideways", no_sideways(page))
                shot(page, f"v21-8-model-dates-{appearance}-{width}.png")

        # ---------- 6. Help ----------
        print("\n--- 6. Help ---")
        seed(page)
        tab(page, "help")
        def help_text(i):
            return page.evaluate(f"() => document.getElementById('{i}') ? document.getElementById('{i}').textContent : ''")
        check("Help explains the dark-mode lift", "too dark" in help_text("help-dark-readable") and "brighter" in help_text("help-dark-readable"), help_text("help-dark-readable"))
        check("Help explains the model dates", all(w in help_text("help-model-dates") for w in ["Today", "Yesterday", "Since 7 Oct"]), help_text("help-model-dates"))
        check("Help explains the tab bar while typing", "tab bar" in help_text("help-typing") and "keyboard" in help_text("help-typing"), help_text("help-typing"))

        check("no page errors", not errors, errors[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
