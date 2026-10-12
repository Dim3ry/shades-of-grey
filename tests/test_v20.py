"""v20 tests for Minifolio: Appearance (Dark / Light / Match my phone).

Checks:
1. Version numbers, the Updates entry, CNAME and the ocr folder kept, storage names and the data
   version unchanged.
2. Dark stays the default and looks exactly as before (same base colours, no light mark).
3. Settings → Appearance: three buttons, one pressed at a time; Light swaps the whole colour set;
   each choice survives a reload (and the page is light BEFORE the app starts, so no dark flash).
4. Match my phone follows the phone's own setting, and switches live when the phone does.
5. Readability in light mode: base text colours, status colours and every stage colour of every
   colour set reach the 4.5 contrast target on the cards; dark mode keeps the set's own colours.
   The photo viewer and camera stay dark. Nothing scrolls sideways.
6. Backups: carry Appearance and the colour set; restoring brings each choice back; older backups
   and nonsense values leave yours alone. Unknown settings are kept when saving (which is why older
   versions of the app keep the new setting, and the data version didn't need raising).
7. Help and screenshots of the main screens in light mode.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
from dialog_watch import DialogAnswers

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
    # v21.4: the app's code moved out of index.html into early.js and app.js, so "index.html"
    # here means the page plus those two files (the source checks look across all three).
    if name == "index.html":
        return "\n".join(open(os.path.join(ROOT, n), encoding="utf-8").read() for n in ("index.html", "early.js", "app.js"))
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
UNITS = [{"id": i + 1, "name": n, "hobby": "40K", "faction": f, "stage": st, "count": c, "notes": "",
          "log": [["2026-09-01", 0], ["2026-10-0" + str(i + 1), st]]}
         for i, (n, f, st, c) in enumerate([("Intercessors", "Ultramarines", 7, 10), ("Hive Tyrant", "Tyranids", 5, 1),
                                            ("Termagants", "Tyranids", 3, 20), ("Bikers", "White Scars", 6, 3),
                                            ("Boyz", "Orks", 0, 10)])]
BOOK = {"paints": [
    {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a", "status": "wishlist"},
    {"id": 2, "brand": "The Army Painter", "name": "Matt White", "colour": "#f5f5f5", "status": "empty"},
    {"id": 3, "brand": "Vallejo", "name": "Ivory", "colour": "#efe6cf", "status": "low"},
    {"id": 4, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "owned"}],
    "recipes": [{"id": 1, "name": "Blue armour", "part": "Armour", "notes": "",
                 "steps": [{"technique": "Base coat", "coats": 2, "paints": [{"paint": 1, "mix": None}]},
                           {"technique": "Wash", "coats": 1, "paints": [{"paint": 4, "mix": None}]}]}],
    "schemes": []}
FACTIONS = {"Ultramarines": "#1f4fa3", "White Scars": "#e8e6dc", "Tyranids": "#6d28d9"}

def seed(page, settings=None, units=UNITS, book=BOOK):
    page.goto(URL)
    page.evaluate("""([u, b, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, book, settings])
    page.reload()
    page.wait_for_timeout(300)

def full_settings(**extra):
    s = {"palette": "ice", "tab": "dashboard", "stages": STAGES, "doneFrom": 5, "factionColours": FACTIONS}
    s.update(extra)
    return s

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(80)

def mark(page):
    return page.evaluate("document.documentElement.dataset.appearance || ''")

def background(page):
    return page.evaluate("getComputedStyle(document.body).backgroundColor")

def saved(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings') || '{}'"))

def pressed(page):
    return page.eval_on_selector_all("[data-appearance-choice][aria-pressed='true']", "els => els.map(e => e.dataset.appearanceChoice)")

def choose(page, choice):
    tab(page, "settings")
    page.click(f"[data-appearance-choice='{choice}']")
    page.wait_for_timeout(100)

def restore(page, backup):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json",
                                                  "buffer": json.dumps(backup).encode()}])
    page.wait_for_timeout(700)

DARK_BG, LIGHT_BG = "rgb(11, 18, 32)", "rgb(233, 239, 246)"

def main():
    sw = read("sw.js")
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        DialogAnswers(page)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v20 or later", float(version[1:]) >= 20, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        v20 = [i for i, h in enumerate(heads) if re.match(r"v20(?!\.)", h)]
        check("the Updates tab has a v20 entry", bool(v20), heads[:3])
        if v20:
            text = page.locator("#changelog .release").nth(v20[0]).inner_text()
            check("the v20 entry mentions Appearance, Match my phone and backups",
                  "Appearance" in text and "Match my phone" in text and "Backups" in text, text)
        check("CNAME file kept", os.path.exists(os.path.join(ROOT, "CNAME")) and "minifolio.app" in read("CNAME"))
        check("ocr folder kept", os.path.exists(os.path.join(ROOT, "ocr", "ocr-worker.js")))
        for key in ['"mini-tracker-models"', '"shades-of-grey-settings"', '"shades-of-grey-recipes"', '"shades-of-grey-photos"']:
            check(f"storage name {key} unchanged", key in html)
        check("DATA_VERSION still 1 (saved data's shape is unchanged)", page.evaluate("DATA_VERSION") == 1)

        # ---------- 2. Dark is the default ----------
        print("--- 2. Dark is the default ---")
        seed(page)
        check("a new user gets dark (no light mark)", mark(page) == "", mark(page))
        check("dark page colour is the same deep navy as before", background(page) == DARK_BG, background(page))
        check("dark base colours unchanged", page.evaluate("""() => { const s = getComputedStyle(document.documentElement);
            return ['--background','--card','--border','--text','--muted','--accent','--danger'].map(k => s.getPropertyValue(k).trim()); }""")
              == ["#0b1220", "#141d2f", "#22304a", "#dbe4f0", "#8193ad", "#7dd3fc", "#f87171"])
        tab(page, "settings")
        check("Settings has the three Appearance choices",
              page.locator("#appearance-card [data-appearance-choice]").all_inner_texts() == ["Dark", "Light", "Match my phone"])
        check("Dark is pressed to start with", pressed(page) == ["dark"], pressed(page))
        # v27: the Counting visits card now sits between them, so the check is "before Colours, with only that card between".
        check("the Appearance card sits just above Colours (v27: with the Counting visits card between)", page.evaluate("""() => {
            const a = document.getElementById('appearance-card'); let next = a.nextElementSibling;
            if (next && next.id === 'counting-card') next = next.nextElementSibling;
            return !!next && next.contains(document.getElementById('palette-select')); }"""))
        seed(page, full_settings(palette="ice"))
        check("dark mode shows the colour set's own stage colours (v21.8: lifted only where too dark to read)", page.evaluate("""() => {
            const s = getComputedStyle(document.documentElement);
            return forShow(stageColours('ice', STAGES.length)).every((c, i) => s.getPropertyValue('--stage-' + i).trim() === c); }"""))

        # ---------- 3. Choosing Light, and each choice surviving a reload ----------
        print("--- 3. Light, and reloads ---")
        seed(page, full_settings())
        choose(page, "light")
        check("Light puts the light mark on the page", mark(page) == "light", mark(page))
        check("Light swaps the page colour to the pale cool blue-grey", background(page) == LIGHT_BG, background(page))
        check("Light is pressed, and only Light", pressed(page) == ["light"], pressed(page))
        check("Light is saved with the other settings", saved(page).get("appearance") == "light" and saved(page).get("stages") == STAGES)
        check("the phone's top-bar colour follows (light)",
              page.get_attribute('meta[name="theme-color"]', "content") == "#e9eff6")
        check("Colours card explains the deeper stage colours in light mode", page.is_visible("#palette-light-note"))
        for choice, want in [("light", "light"), ("dark", ""), ("auto", "")]:
            seed(page, full_settings())
            page.emulate_media(color_scheme="dark")
            choose(page, choice)
            page.reload(); page.wait_for_timeout(300)
            tab(page, "settings")
            check(f"'{choice}' survives a reload", saved(page).get("appearance") == choice and pressed(page) == [choice]
                  and mark(page) == want, (saved(page).get("appearance"), pressed(page), mark(page)))
        # The little script in <head> marks the page light before the app's own code runs.
        seed(page, full_settings(appearance="light"))
        page.add_init_script("""document.addEventListener('readystatechange', () => {
            if (document.readyState === 'interactive' && window.__early === undefined)
              window.__early = document.documentElement.dataset.appearance || ''; });""")
        page.reload(); page.wait_for_timeout(300)
        check("light is set before the page is first drawn (no dark flash)",
              page.evaluate("window.__early") == "light" or "document.documentElement.dataset.appearance = \"light\"" in html.split("<style>")[0],
              page.evaluate("window.__early"))
        check("dark choice restores the dark colours", (choose(page, "dark") or True) and background(page) == DARK_BG and mark(page) == "")

        # ---------- 4. Match my phone ----------
        print("--- 4. Match my phone ---")
        seed(page, full_settings())
        page.emulate_media(color_scheme="light")
        choose(page, "auto")
        check("Match my phone + phone in light mode = light", mark(page) == "light")
        check("Match my phone explains what it's doing right now",
              "light" in page.inner_text("#appearance-note"), page.inner_text("#appearance-note"))
        page.emulate_media(color_scheme="dark"); page.wait_for_timeout(200)
        check("phone switches to dark: the app follows straight away", mark(page) == "" and background(page) == DARK_BG)
        check("the note updates too", "dark" in page.inner_text("#appearance-note"), page.inner_text("#appearance-note"))
        page.emulate_media(color_scheme="light"); page.wait_for_timeout(200)
        check("phone switches back to light: the app follows", mark(page) == "light")
        choose(page, "dark")
        check("Dark ignores the phone being light", mark(page) == "")
        choose(page, "light"); page.emulate_media(color_scheme="dark"); page.wait_for_timeout(200)
        check("Light ignores the phone being dark", mark(page) == "light")
        page.emulate_media(color_scheme="no-preference")

        # ---------- 5. Readability in light mode ----------
        print("--- 5. Readability in light mode ---")
        seed(page, full_settings(appearance="light"))
        ratios = page.evaluate("""() => { const s = getComputedStyle(document.documentElement);
            const v = k => s.getPropertyValue(k).trim(); const card = v('--card'), bg = v('--background');
            const out = {};
            for (const k of ['--text','--muted','--accent','--danger','--note','--good','--bad','--warn','--caution','--wish','--grey-status'])
              out[k] = Math.min(contrastRatio(v(k), card), contrastRatio(v(k), bg));
            return out; }""")
        low = {k: round(r, 2) for k, r in ratios.items() if r < 4.5}
        check("text, muted, accent, danger and status colours all reach 4.5 on cards and page", not low, low)
        check("light colours are cool (blue more than red) for page, cards and accent", page.evaluate("""() => {
            const s = getComputedStyle(document.documentElement);
            return ['--background','--card','--accent','--text'].every(k => { const h = s.getPropertyValue(k).trim();
              return parseInt(h.slice(5, 7), 16) >= parseInt(h.slice(1, 3), 16); }); }"""))
        bad = page.evaluate("""() => { const out = [];
            for (const name of Object.keys(PALETTES)) for (const n of [2, 5, 8, 10])
              shownStageColours(name, n).forEach((c, i) => { const r = contrastRatio(c, '#f8fafc');
                if (r < 4.5) out.push(name + ' ' + n + '/' + i + ' ' + c + ' ' + r.toFixed(2)); });
            return out; }""")
        check("every stage colour of every colour set reads at 4.5+ in light mode", not bad, bad[:5])
        check("stage colours on the page are the deepened ones", page.evaluate("""() => {
            const s = getComputedStyle(document.documentElement);
            return shownStageColours(settings.palette, STAGES.length).every((c, i) => s.getPropertyValue('--stage-' + i).trim() === c)
              && s.getPropertyValue('--stage-' + (STAGES.length - 1)).trim() !== stageColours(settings.palette, STAGES.length).pop(); }"""))
        check("each colour set keeps different colours for different stages in light mode", page.evaluate("""() =>
            Object.keys(PALETTES).every(name => new Set(shownStageColours(name, 8)).size === 8)"""))
        check("colours that already read well aren't changed", page.evaluate("deepenForLight('#1f3a8a') === '#1f3a8a'"))
        check("a pale faction colour gets a deeper bar in light mode, a dark one doesn't", page.evaluate("""() => {
            const a = document.createElement('div'), b = document.createElement('div');
            setFactionStyle(a, '#e8e6dc'); setFactionStyle(b, '#1f4fa3');
            return a.style.getPropertyValue('--faction-colour') !== '#e8e6dc' && b.style.getPropertyValue('--faction-colour') === '#1f4fa3'; }"""))
        check("pressed paint-status chips use white text in light mode", page.evaluate("""() =>
            getComputedStyle(document.documentElement).getPropertyValue('--chip-on').trim() === '#ffffff'"""))
        # Photo viewer and camera stay dark.
        check("the photo viewer keeps the dark colours", page.evaluate("""() => {
            const v = getComputedStyle(document.getElementById('viewer'));
            return v.getPropertyValue('--text').trim() === '#dbe4f0' && v.getPropertyValue('--card').trim() === '#141d2f'; }"""))
        page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
        page.click("#scan-button")
        page.locator("#scan-panel button", has_text="Scan a label").click()
        page.wait_for_selector("#scan-camera video", timeout=5000)
        check("the camera view stays dark in light mode", page.evaluate("""() => {
            const c = document.getElementById('scan-camera'); const s = getComputedStyle(c);
            return s.backgroundColor === 'rgb(0, 0, 0)' && s.getPropertyValue('--text').trim() === '#dbe4f0'; }"""))
        page.screenshot(path=os.path.join(SHOTS, "v20-light-camera.png"))
        page.locator("#scan-camera button", has_text="Cancel").click()
        page.wait_for_timeout(100)
        for name in ["dashboard", "units", "recipes", "help", "updates", "settings"]:
            tab(page, name)
            check(f"light mode: nothing scrolls sideways on {name}",
                  page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

        # ---------- 6. Backups ----------
        print("--- 6. Backups ---")
        seed(page, full_settings(appearance="light", palette="greyscale"))
        b = page.evaluate("backupData()")
        check("a backup carries Appearance and the colour set", b.get("appearance") == "light" and b.get("palette") == "greyscale", b)
        check("a backup's data version is still 1", b.get("dataVersion") == 1)
        for choice, palette in [("dark", "frost"), ("light", "colourblind"), ("auto", "greyscale")]:
            seed(page, full_settings(appearance=choice, palette=palette))
            backup = page.evaluate("backupData()")
            other = "light" if choice != "light" else "dark"
            seed(page, full_settings(appearance=other, palette="ice"))
            restore(page, backup)
            s = saved(page)
            tab(page, "settings")
            check(f"restoring brings back '{choice}' and {palette}",
                  s.get("appearance") == choice and s.get("palette") == palette and pressed(page) == [choice]
                  and page.input_value("#palette-select") == palette, (s.get("appearance"), s.get("palette"), pressed(page)))
        seed(page, full_settings(appearance="light", palette="frost"))
        old = {"app": "Minifolio", "version": 6, "dataVersion": 1, "stages": STAGES, "doneFrom": 5, "models": UNITS,
               "recipes": BOOK, "factionColours": {}}
        restore(page, old)
        check("an older backup (no Appearance) leaves yours as it is",
              saved(page).get("appearance") == "light" and saved(page).get("palette") == "frost" and mark(page) == "light")
        seed(page, full_settings(appearance="dark", palette="ice"))
        restore(page, {**old, "appearance": "__proto__", "palette": "constructor"})
        check("nonsense Appearance and colour set in a backup are ignored",
              saved(page).get("appearance") == "dark" and saved(page).get("palette") == "ice" and not errors, errors)
        seed(page, full_settings(appearance="light", futureThing={"x": 1}))
        choose(page, "dark")
        check("settings the app doesn't know are kept when it saves (older versions keep Appearance the same way)",
              saved(page).get("futureThing") == {"x": 1})

        # ---------- 7. Help and light-mode screenshots ----------
        print("--- 7. Help and screenshots ---")
        tab(page, "help")
        topic = page.text_content("#help-appearance") or ""
        check("Help has an Appearance topic covering all three choices",
              all(w in topic for w in ["Dark", "Light", "Match my phone"]), topic[:120])
        check("Help explains the deeper stage colours and dark photos", "deeper" in topic and "camera" in topic)
        check("Help's backup topic lists Appearance", "Appearance" in (page.text_content("details:has(> summary:text('Your data and backups'))") or ""))

        os.makedirs(SHOTS, exist_ok=True)
        seed(page, full_settings(appearance="light"))
        for name in ["dashboard", "units", "settings"]:
            tab(page, name)
            page.screenshot(path=os.path.join(SHOTS, f"v20-light-{name}.png"), full_page=True)
        page.evaluate("openRecipeId = null; settings.recipeView = 'palette'; showTab('recipes'); renderRecipes()")
        page.click("#shop-button"); page.wait_for_timeout(100)
        page.locator("#buy-bar .buy-shops button").first.click(); page.wait_for_timeout(100)
        page.screenshot(path=os.path.join(SHOTS, "v20-light-palette-shopping.png"), full_page=True)
        page.evaluate("startImport()")
        page.fill("#import-text", "Armour:\nMacragge Blue\nWet blend 3:1 Kantor Blue:White\nNuln Oil\nSome Unknown Paint")
        page.click("#import-page button.primary-button"); page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SHOTS, "v20-light-paste-preview.png"), full_page=True)
        page.evaluate("closeImport(true)")
        page.evaluate("showToast('Saved', () => {}, 'Undo', 10)"); page.wait_for_timeout(50)
        check("the toast's Undo is readable in light mode", page.evaluate("""() => {
            const t = document.querySelector('.toast'); const s = getComputedStyle(document.documentElement);
            return contrastRatio(s.getPropertyValue('--toast-action').trim(), s.getPropertyValue('--text').trim()) >= 4.5; }"""))
        check("light-mode screenshots saved", all(os.path.exists(os.path.join(SHOTS, f"v20-light-{n}.png"))
              for n in ["dashboard", "units", "settings", "palette-shopping", "paste-preview", "camera"]))
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
