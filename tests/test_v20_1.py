"""v20.1 tests for Minifolio: the warm Forge stage colours and Custom per-stage colours.

Checks:
1. Version numbers, the Updates entry, CNAME and the ocr folder kept, storage names and the data
   version unchanged (still 1).
2. Forge: in the Colours list, readable on dark cards, every stage different from its neighbours
   in dark AND light mode (light mode deepens pale colours), and it survives a reload.
3. Custom: the 6th choice. Starts from the set you had; the colour you pick shows across the app
   and is saved; a too-faint colour gets a warning; light mode shows pale picks deeper; Reset (with
   Undo); switching sets and back keeps your colours; it all survives a reload.
4. Stages with Custom on: reorder, remove and add. Colours move with their stage; a new stage gets
   the colour the starting set gives that spot.
5. Backups carry Custom; restore brings it back; older backups leave yours alone; nonsense values
   are cleaned up. A setting written by an older version (palette back to Ice, Custom kept) still
   shows your colours.
6. Help, no sideways scroll, screenshots, no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright
import fold_opener   # v54: Stages, Import and Your data fold shut; this older test works inside them
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
                                            ("Boyz", "Orks", 0, 10), ("Gaunts", "Tyranids", 2, 10)])]
FORGE = ["#e0452b", "#f2701c", "#f59e0b", "#facc15", "#fde9c0"]
# Eight easy-to-tell-apart custom colours, one per stage.
MINE = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff", "#ff8800", "#ffffff"]

def seed(page, settings=None, units=UNITS):
    page.goto(URL)
    page.evaluate("""([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings])
    page.reload()
    page.wait_for_timeout(300)

def full_settings(**extra):
    s = {"palette": "ice", "tab": "dashboard", "stages": STAGES, "doneFrom": 5}
    s.update(extra)
    return s

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(80)

def saved(page):
    return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings') || '{}'"))

def sh(page, colour):
    """v21.8: how the app SHOWS a stored colour (dark mode lifts a colour that is too dark to read)."""
    return page.evaluate("(c) => forShow([c])[0]", colour)

def shl(page, colours):
    return page.evaluate("(l) => l.map(c => forShow([c])[0])", colours)

def stage_vars(page, n=None):
    return page.evaluate("""(n) => { const s = getComputedStyle(document.documentElement);
        return Array.from({ length: n || STAGES.length }, (u, i) => s.getPropertyValue('--stage-' + i).trim()); }""", n)

def choose_palette(page, value):
    tab(page, "settings")
    page.select_option("#palette-select", value)
    page.wait_for_timeout(100)

def pickers(page):
    return page.locator("#custom-colour-list input[type=color]")

def pick(page, index, colour):
    pickers(page).nth(index).fill(colour)   # fires "input" then "change", like letting go
    page.wait_for_timeout(60)

def restore(page, backup):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json",
                                                  "buffer": json.dumps(backup).encode()}])
    page.wait_for_timeout(700)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=True)

def main():
    sw = read("sw.js")
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        fold_opener.open_cards_on_load(page)   # v54: open the folded Settings cards whenever the app loads
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        DialogAnswers(page)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v20.1 or later", float(version[1:]) >= 20.1, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        entry = [i for i, h in enumerate(heads) if h.startswith("v20.1")]
        if page.evaluate("['v20.1'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab has a v20.1 entry", bool(entry), heads[:3])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab has a v20.1 entry')
        if entry:
            text = page.locator("#changelog .release").nth(entry[0]).inner_text()
            check("the v20.1 entry mentions Forge, Custom and backups", all(w in text for w in ["Forge", "Custom", "backups"]), text[:200])
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("the ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm", "README.md"]))
        check("the data version is still 1", page.evaluate("DATA_VERSION") == 1)
        check("storage names unchanged", all(k in html for k in
              ["'mini-tracker-models'".strip("'"), "shades-of-grey-settings", "shades-of-grey-recipes"]))

        # ---------- 2. Forge ----------
        print("--- 2. Forge ---")
        seed(page, full_settings())
        tab(page, "settings")
        options = page.locator("#palette-select option").all_inner_texts()
        check("Colours lists 6 choices: the 4 old sets, Forge and Custom",
              len(options) == 6 and any(o.startswith("Forge") for o in options) and options[-1].startswith("Custom")
              and all(any(o.startswith(w) for o in options) for w in ["Ice", "Frost", "Greyscale", "Colour-blind"]), options)
        check("Forge's colours are ember red → amber → gold → cream", page.evaluate("PALETTES.forge.colours") == FORGE)
        choose_palette(page, "forge")
        check("choosing Forge saves it", saved(page).get("palette") == "forge" and saved(page).get("useCustom") is not True)
        check("Forge shows across the app in dark mode (first and last stage)",
              stage_vars(page)[0] == sh(page, FORGE[0]) and stage_vars(page)[-1] == sh(page, FORGE[-1]), stage_vars(page))
        dark_ok = page.evaluate("""() => [2, 5, 8, 10].every(n => stageColours('forge', n).every(c => contrastRatio(c, '#141d2f') >= 3))""")
        check("every Forge stage reads on the dark cards (2, 5, 8 and 10 stages)", dark_ok)
        # Neighbouring stages must look different: some colour channel differs by 8 or more.
        # (Forge's closest pair is 9 apart, in light mode at 10 stages: the two gold steps.
        # Ice's closest is also 9 and Greyscale's 4, so Forge is as distinct as the old sets.)
        distinct = """(light) => [2, 5, 8, 10].every(n => {
            const cs = stageColours('forge', n).map(c => light ? deepenForLight(c) : c);
            const ch = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
            return cs.every((c, i) => i === 0 || Math.max(...ch(c).map((v, k) => Math.abs(v - ch(cs[i - 1])[k]))) >= 8)
                && new Set(cs).size === n; })"""
        check("Forge's stages are all different from their neighbours in dark mode", page.evaluate(distinct, False))
        check("Forge's stages stay different in light mode too (after deepening)", page.evaluate(distinct, True))
        check("in light mode every Forge stage reads at 4.5 on the light cards", page.evaluate(
            """() => [2, 5, 8, 10].every(n => stageColours('forge', n).every(c => contrastRatio(deepenForLight(c), LIGHT_CARD) >= 4.5))"""))
        page.reload(); page.wait_for_timeout(300); tab(page, "settings")
        check("Forge survives a reload", page.input_value("#palette-select") == "forge" and stage_vars(page)[0] == sh(page, FORGE[0]))
        tab(page, "dashboard"); shot(page, "v20.1-forge-dark-dashboard.png")
        tab(page, "units"); shot(page, "v20.1-forge-dark-units.png")
        seed(page, full_settings(palette="forge", appearance="light"))
        check("Forge in light mode: the cream end is shown deeper", stage_vars(page)[-1] != FORGE[-1]
              and page.evaluate("(c) => contrastRatio(c, LIGHT_CARD) >= 4.5", stage_vars(page)[-1]), stage_vars(page))
        tab(page, "dashboard"); shot(page, "v20.1-forge-light-dashboard.png")
        tab(page, "units"); shot(page, "v20.1-forge-light-units.png")

        # ---------- 3. Custom ----------
        print("--- 3. Custom ---")
        seed(page, full_settings(palette="forge"))
        tab(page, "settings")
        check("the Custom list is hidden while a named set is chosen", page.locator("#custom-colours").is_hidden())
        choose_palette(page, "custom")
        s = saved(page)
        start = page.evaluate("stageColours('forge', STAGES.length)")
        check("choosing Custom turns it on and keeps Forge as the starting set",
              s.get("useCustom") is True and s.get("palette") == "forge", s)
        check("Custom starts from the set you had (Forge)", s.get("customColours") == start, s.get("customColours"))
        check("Custom shows one colour square per stage, named after the stage",
              pickers(page).count() == len(STAGES) and page.locator("#custom-colour-list strong").all_inner_texts() == STAGES)
        check("the squares start with Forge's colours", [pickers(page).nth(i).input_value() for i in range(len(STAGES))] == start)
        check("Reset names the set it goes back to", "Forge" in page.inner_text("#custom-reset"))
        pick(page, 2, "#00ffaa")
        check("a picked colour shows across the app at once", stage_vars(page)[2] == "#00ffaa", stage_vars(page))
        check("a picked colour is saved", saved(page).get("customColours", [None] * 3)[2] == "#00ffaa")
        check("the stage editor's dot shows the picked colour",
              page.evaluate("getComputedStyle(document.querySelectorAll('#stage-list .stage-row .dot')[2]).getPropertyValue('--dot').trim()") == "#00ffaa")
        warn = page.locator("#custom-colour-list .custom-colour-row").nth(4).locator("small")
        check("a normal colour has no warning", warn.is_hidden())
        pick(page, 4, "#1c2333")
        check("a too-faint colour gets a warning", warn.is_visible() and "faint" in warn.inner_text().lower(), warn.inner_text())
        tab(page, "settings"); shot(page, "v20.1-custom-faint-warning.png")
        pick(page, 4, "#a855f7")
        check("the warning goes when you pick a readable colour", "faint" not in warn.inner_text().lower())
        # Undo-able Reset
        page.click("#custom-reset"); page.wait_for_timeout(100)
        check("Reset puts every stage back to the starting set", saved(page).get("customColours") == start and stage_vars(page) == shl(page, start))
        check("Reset says so, with Undo", "reset" in page.inner_text("#toast").lower() and page.locator("#toast-undo").is_visible())
        page.click("#toast-undo"); page.wait_for_timeout(100)
        cc = saved(page).get("customColours")
        check("Undo brings your colours back", cc[2] == "#00ffaa" and cc[4] == "#a855f7", cc)
        # Switch away and back
        choose_palette(page, "ice")
        check("picking a named set turns Custom off and shows that set",
              saved(page).get("useCustom") is False and stage_vars(page)[0] == page.evaluate("forShow([stageColours('ice', 8)[0]])[0]"))
        choose_palette(page, "custom")
        check("switching back to Custom keeps your colours", stage_vars(page)[2] == "#00ffaa" and stage_vars(page)[4] == sh(page, "#a855f7"))
        check("…and Reset now goes back to Ice (the set you came from)", "Ice" in page.inner_text("#custom-reset"))
        page.reload(); page.wait_for_timeout(300); tab(page, "settings")
        check("Custom survives a reload", page.input_value("#palette-select") == "custom"
              and stage_vars(page)[2] == "#00ffaa" and pickers(page).nth(4).input_value() == "#a855f7")
        # Set a full custom set for the screenshots and the stage tests.
        page.evaluate("(c) => { settings.customColours = c; settings.useCustom = true; saveSettings(); applyPalette(settings.palette); renderSettings(); }", MINE)
        tab(page, "settings"); shot(page, "v20.1-custom-dark-settings.png")
        tab(page, "dashboard"); shot(page, "v20.1-custom-dark-dashboard.png")
        # Light mode: pale picks are shown deeper, the picked colour stays saved as picked.
        page.evaluate("settings.appearance = 'light'; saveSettings(); applyPalette(settings.palette); render(); renderSettings()")
        light = stage_vars(page)
        check("light mode shows pale custom colours deeper (white and yellow)", light[7] != "#ffffff" and light[3] != "#ffff00", light)
        check("light mode: every custom colour reads at 4.5 on the light cards",
              page.evaluate("(cs) => cs.every(c => contrastRatio(c, LIGHT_CARD) >= 4.5)", light))
        check("light mode: the colours you picked are still saved as picked", saved(page).get("customColours") == MINE)
        tab(page, "settings")
        note = page.locator("#custom-colour-list .custom-colour-row").nth(7).locator("small")
        check("light mode: a pale colour's row says it's shown deeper", note.is_visible() and "deeper" in note.inner_text(), note.inner_text())
        check("light mode: a too-faint-on-dark colour still gets its warning", (pick(page, 0, "#1c2333") or True)
              and page.locator("#custom-colour-list .custom-colour-row").nth(0).locator("small.faint").is_visible())
        pick(page, 0, MINE[0])
        shot(page, "v20.1-custom-light-settings.png")
        tab(page, "dashboard"); shot(page, "v20.1-custom-light-dashboard.png")
        check("no sideways scroll on Settings with Custom open",
              page.evaluate("(tab => document.documentElement.scrollWidth <= window.innerWidth)()"))

        # ---------- 4. Stages with Custom on ----------
        print("--- 4. Stages: reorder, remove, add ---")
        seed(page, full_settings(palette="ice", useCustom=True, customColours=MINE))
        tab(page, "settings")
        page.click(f"#stage-list button[aria-label='Move {STAGES[0]} down']")
        dots = page.evaluate("[...document.querySelectorAll('#stage-list .stage-row .dot')].map(d => d.style.getPropertyValue('--dot'))")
        check("before saving, the editor's dots already show each colour moving with its stage", dots[:2] == shl(page, [MINE[1], MINE[0]]), dots[:3])
        page.click("#save-stages"); page.wait_for_timeout(150)
        s = saved(page)
        check("reorder: the first two stages swapped places", s.get("stages", [])[:2] == [STAGES[1], STAGES[0]], s.get("stages"))
        check("reorder: their colours moved with them", s.get("customColours", [])[:2] == [MINE[1], MINE[0]], s.get("customColours"))
        check("reorder: shown across the app", stage_vars(page)[:2] == shl(page, [MINE[1], MINE[0]]))
        names = s["stages"]
        page.click(f"#stage-list button[aria-label='Remove {names[2]}']")
        page.click("#save-stages"); page.wait_for_timeout(150)
        s = saved(page)
        expect = [MINE[1], MINE[0]] + MINE[3:]
        check("remove: 7 stages left", len(s.get("stages", [])) == 7)
        check("remove: the removed stage's colour went with it, the rest kept theirs", s.get("customColours") == expect, s.get("customColours"))
        page.click("#add-stage")
        page.fill("#stage-list .stage-row:last-child input", "Based")
        page.click("#save-stages"); page.wait_for_timeout(150)
        s = saved(page)
        default = page.evaluate("stageColours('ice', 8)[7]")
        check("add: 8 stages again, the new one last", len(s.get("stages", [])) == 8 and s["stages"][-1] == "Based")
        check("add: the old stages keep their colours", s.get("customColours", [])[:7] == expect)
        check("add: the new stage gets the starting set's colour for that spot", s.get("customColours", [None] * 8)[7] == default,
              (s.get("customColours"), default))
        tab(page, "settings")
        check("the Custom list follows the new stages",
              page.locator("#custom-colour-list strong").all_inner_texts() == s["stages"] and pickers(page).nth(7).input_value() == default)
        shot(page, "v20.1-custom-after-stage-changes.png")
        # Custom switched off: colours still follow their stages for when it's switched back on.
        seed(page, full_settings(palette="forge", useCustom=False, customColours=MINE))
        tab(page, "settings")
        page.click(f"#stage-list button[aria-label='Move {STAGES[0]} down']")
        page.click("#save-stages"); page.wait_for_timeout(150)
        check("with Custom off, saved custom colours still move with their stages",
              saved(page).get("customColours", [])[:2] == [MINE[1], MINE[0]])
        check("…and the named set's colours are shown, not yours", stage_vars(page)[0] == sh(page, FORGE[0]))

        # ---------- 5. Backups ----------
        print("--- 5. Backups ---")
        seed(page, full_settings(palette="forge", useCustom=True, customColours=MINE))
        b = page.evaluate("backupData()")
        check("a backup carries Custom (on, the starting set and the colours)",
              b.get("useCustom") is True and b.get("palette") == "forge" and b.get("customColours") == MINE, b.get("customColours"))
        check("a backup's data version is still 1", b.get("dataVersion") == 1)
        seed(page, full_settings(palette="ice"))
        restore(page, b)
        s = saved(page)
        tab(page, "settings")
        check("restoring brings Custom back", s.get("useCustom") is True and s.get("customColours") == MINE
              and s.get("palette") == "forge" and page.input_value("#palette-select") == "custom" and stage_vars(page) == shl(page, MINE),
              (s.get("useCustom"), s.get("customColours")))
        page.reload(); page.wait_for_timeout(300)
        check("…and it survives a reload after the restore", stage_vars(page) == shl(page, MINE))
        seed(page, full_settings(palette="forge"))
        fb = page.evaluate("backupData()")
        seed(page, full_settings(palette="ice"))
        restore(page, fb)
        check("restoring a Forge backup brings Forge back", saved(page).get("palette") == "forge" and stage_vars(page)[0] == sh(page, FORGE[0]))
        old = {"app": "Minifolio", "version": 6, "dataVersion": 1, "stages": STAGES, "doneFrom": 5, "models": UNITS,
               "recipes": {"paints": [], "recipes": [], "schemes": []}, "factionColours": {}, "palette": "ice", "appearance": "dark"}
        seed(page, full_settings(palette="forge", useCustom=True, customColours=MINE))
        restore(page, {k: v for k, v in old.items() if k != "palette"})
        check("an older backup (no Custom) leaves your Custom colours alone",
              saved(page).get("useCustom") is True and saved(page).get("customColours") == MINE and stage_vars(page) == shl(page, MINE))
        seed(page, full_settings(palette="ice"))
        restore(page, {**old, "useCustom": True,
                       "customColours": ["red", "#12345", "url(javascript:alert(1))", 7, None, "#ABCDEF", {"x": 1}, "#0f0f0f"]})
        cc = saved(page).get("customColours")
        check("nonsense colours in a backup are cleaned up (only real colours kept)",
              isinstance(cc, list) and cc[5] == "#abcdef" and cc[7] == "#0f0f0f" and all(c in ("", "#abcdef", "#0f0f0f") for c in cc), cc)
        shown = stage_vars(page)
        check("…and broken entries show the starting set's colour instead", shown[0] == page.evaluate("forShow([stageColours('ice', 8)[0]])[0]")
              and shown[5] == sh(page, "#abcdef") and not errors, (shown, errors))
        seed(page, full_settings(palette="ice"))
        restore(page, {**old, "useCustom": "yes", "customColours": "nope"})
        check("a nonsense Custom switch in a backup is ignored", saved(page).get("useCustom") is not True and not errors, errors)
        # An older version (v20) can't show Custom or Forge: it shows Ice and may save "ice" back,
        # but keeps the settings it doesn't know. Coming back to v20.1 still shows your colours.
        seed(page, full_settings(palette="ice", useCustom=True, customColours=MINE))
        tab(page, "settings")
        check("after an older version reset the set to Ice, your Custom colours still show",
              stage_vars(page) == shl(page, MINE) and page.input_value("#palette-select") == "custom")
        seed(page, full_settings(palette="forge", useCustom=True, customColours=MINE[:5]))
        check("a short colour list (stages added by an older version) fills the gap from the starting set",
              stage_vars(page)[:5] == shl(page, MINE[:5]) and stage_vars(page)[5:] == page.evaluate("stageColours('forge', 8).slice(5).map(c => forShow([c])[0])"))
        seed(page, full_settings(palette="constructor", useCustom="maybe"))
        check("a broken saved set or switch falls back safely", stage_vars(page)[0] == page.evaluate("forShow([stageColours('ice', 8)[0]])[0]") and not errors, errors)

        # ---------- 6. Help ----------
        print("--- 6. Help ---")
        seed(page, full_settings())
        tab(page, "help")
        topic = page.text_content("#help-appearance") or ""
        check("Help covers Forge and Custom", "Forge" in topic and "Custom" in topic)
        check("Help covers the warning, Reset and stages keeping their colours",
              "warning" in topic and "Reset" in topic and "reorder" in topic)
        check("Help's backup line mentions Custom colours", "Custom colours" in topic)
        check("v20.1 screenshots saved", all(os.path.exists(os.path.join(SHOTS, f)) for f in [
            "v20.1-forge-dark-dashboard.png", "v20.1-forge-light-dashboard.png", "v20.1-custom-dark-settings.png",
            "v20.1-custom-light-settings.png", "v20.1-custom-faint-warning.png", "v20.1-custom-after-stage-changes.png"]))
        check("no page errors", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
