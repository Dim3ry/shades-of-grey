"""AB6 tests for Minifolio (colours, from the approved AI-tells items). New behaviour only:
1. AT-13: Classic's re-mixed base colours (dark and light) and the new page colour.
2. AT-14: with no stage colour set picked, each look uses its own set; a saved pick (Ice included) is left alone and nothing is saved by looking.
3. AT-58: the loading ring's conic sweep (.lr-sweep) is gone.
4. Every stage colour, as shown, passes contrast against its look's card colour.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

DARK = {"--danger": "#ef6f5e", "--bad": "#f2a39a", "--warn": "#e8d58c", "--caution": "#e3a43a", "--wish": "#8fb4e6",
        "--grey-status": "#8d9aa8", "--background": "#0c1418", "--accent": "#5fe0ea"}
LIGHT = {"--danger": "#a8261c", "--note": "#5440b8", "--warn": "#6e5a10", "--wish": "#2a55b0", "--grey-status": "#4d5a68"}
SETS = {"parchment": ["#7a6a55", "#8f4a3a", "#b8303c", "#c48a2c", "#e8dcc0"],
        "bench": ["#7d8077", "#4f7a8c", "#6f8f3a", "#c9a227", "#efe6cc"]}
THEMES = ["classic", "parchment", "forge", "bench"]

def hexrgb(h):
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def var(page, name):
    return page.evaluate("n => getComputedStyle(document.documentElement).getPropertyValue(n).trim()", name)

def open_look(page, theme, appearance, extra=None):
    s = {"theme": theme, "appearance": appearance}
    s.update(extra or {})
    t.load(page, units=[], settings=s)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. AT-13 Classic's colours ---")
        open_look(page, "classic", "dark")
        bad = {k: (var(page, k), v) for k, v in DARK.items() if var(page, k).lower() != v and hexrgb(v) not in var(page, k)}
        check("Classic dark: the re-mixed colours and the new page colour", not bad, bad)
        open_look(page, "classic", "light")
        light_bad = {k: var(page, k) for k, v in LIGHT.items() if k != "--note" and var(page, k).lower() != v}
        check("Classic light: re-mixed danger, warn, wish and grey status", not light_bad, light_bad)
        base = t.read("index.html")
        check("the base light note is #5440b8", "--note: #5440b8;" in base)
        check("the page colour agrees in index.html, early.js and app.js", all("#0c1418" in t.read(f) for f in ("index.html", "early.js", "app.js")))

        print("\n--- 2. AT-14 each look's own set ---")
        for theme in THEMES:
            open_look(page, theme, "dark")
            got = [page.evaluate("i => getComputedStyle(document.documentElement).getPropertyValue('--mentor-s'+i).trim()", i) for i in range(5)]
            want = page.evaluate("th => THEME_SETS[th]", theme)
            check(f"{theme}: no pick uses its own five colours (orb ring variables)", [g.lower() for g in got] == want, (got, want))
        check("Parchment and Bench sets are the ones in the prompt", page.evaluate("() => [THEME_SETS.parchment, THEME_SETS.bench]") == [SETS["parchment"], SETS["bench"]])
        check("Forge uses its existing forge set", page.evaluate("() => THEME_SETS.forge") == page.evaluate("() => PALETTES.forge.colours"))
        check("Classic's set is off the Tailwind Ice values", page.evaluate("() => THEME_SETS.classic.every((c, i) => c !== PALETTES.ice.colours[i])"))

        print("\n--- 3. A saved pick is left alone ---")
        open_look(page, "parchment", "dark", {"palette": "ice"})
        check("Ice picked: still the Ice colours in Parchment", page.evaluate("() => stageColours(settings.palette, 5)") == page.evaluate("() => PALETTES.ice.colours"))
        check("Ice picked: the stored choice is still ice", json.loads(page.evaluate("() => localStorage.getItem('shades-of-grey-settings')") or "{}").get("palette", "ice") == "ice")
        open_look(page, "classic", "dark", {"palette": "greyscale"})
        check("another set picked: that set is used", page.evaluate("() => stageColours(settings.palette, 5)") == page.evaluate("() => PALETTES.greyscale.colours"))
        open_look(page, "bench", "dark")
        page.evaluate("() => saveSettings()")
        saved = json.loads(page.evaluate("() => localStorage.getItem('shades-of-grey-settings')"))
        check("a fresh install saves no palette choice by looking", "palette" not in saved, saved.get("palette"))
        check("the Stage colours menu shows Match the look when nothing was picked", page.evaluate("() => document.getElementById('palette-select').value") == "theme")
        page.evaluate("() => { const s = document.getElementById('palette-select'); s.value = 'ice'; s.dispatchEvent(new Event('change')); }")
        check("picking Ice saves ice", json.loads(page.evaluate("() => localStorage.getItem('shades-of-grey-settings')")).get("palette") == "ice")
        page.evaluate("() => { const s = document.getElementById('palette-select'); s.value = 'theme'; s.dispatchEvent(new Event('change')); }")
        check("picking Match the look goes back to the look's own set", "palette" not in json.loads(page.evaluate("() => localStorage.getItem('shades-of-grey-settings')")))

        print("\n--- 4. AT-58 the loading ring sweep ---")
        check("no .lr-sweep in the page or the script", "lr-sweep" not in base and "lr-sweep" not in t.read("app.js"))
        page.goto(t.URL)
        check("no sweep element on the start page", page.locator(".lr-sweep").count() == 0)

        print("\n--- 5. Stage colours pass contrast against each look's card ---")
        worst = {}
        for theme in THEMES:
            for mode in ("dark", "light"):
                open_look(page, theme, mode)
                low = page.evaluate("""([th, m]) => { const card = THEME_SURFACES[th][m].card; const out = [];
                    for (let i = 0; i < STAGES.length; i++) { const c = getComputedStyle(document.documentElement).getPropertyValue('--stage-' + i).trim();
                      const r = contrastRatio(c, card); if (r < 3) out.push([i, c, r]); } return out; }""", [theme, mode])
                if low:
                    worst[f"{theme} {mode}"] = low
        check("every shown stage colour is at least 3 against the card (4 looks, dark and light)", not worst, worst)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)} passed, {len(results) - sum(results)} failed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
