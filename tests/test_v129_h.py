"""Chunk H tests for Minifolio (tidy, and Games Workshop names out of the app's own words).
New behaviour only:
1. "Compendium" (the old tab, now Colour Lab and Guides) and "the Mentor" (Mentor is always just "Mentor") are not in any text a person
   can see: the page's text, its hints and labels, and every Updates entry. Old shopping sources saved as "Compendium: ..." still show
   as "Colour Lab: ...".
2. No Games Workshop army, unit, paint or app name in the app's own words: Help (apart from the brand list the scanner needs and the
   trademark notice), the army list panel, every hint inside a text box, every Updates entry, the army list message and the downloaded
   CSV template. The stage names and the Parchment theme's name wait for a ruling, so they are not checked here.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OLD_NAMES = re.compile(r"Compendium|\b[Tt]he Mentor\b")
# Paint makers named as facts (Citadel, Warhammer Tone Pro) are allowed, as in the brand lists; their paints are not.
GW = re.compile(r"warhammer(?! tone pro)|games workshop|ultramarine|macragge|yriel|gitz|tyranid|genestealer|luxion|wraithbone|agrax|ardcoat|"
                r"lictor|boyz|intercessor|redemptor|dreadnought|lahmian|carmine blades|\bbaal\b|space marine|\borks?\b|sigmar|stormcast|"
                r"\bnuln\b|\b40k\b", re.I)
UNITS = [{"id": 1, "name": "Spearmen", "hobby": "Skirmish", "faction": "Bone warband", "stage": 2, "count": 5}]

def source(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()

def updates_text(app):
    """Every Updates entry, as written in app.js (the list sits between UPDATES_SHOWN and renderUpdates)."""
    block = app[app.index("const UPDATES_SHOWN"):app.index("function renderUpdates")]
    return " ".join(re.findall(r'"((?:[^"\\]|\\.)*)"', block))

# Every text a person can see on the page (hidden parts included, as Help topics open), and every hint, label and title.
PAGE_TEXT = """(skip) => {
    const leave = skip.map(s => document.querySelector(s)).filter(Boolean);
    const out = [];
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
        const p = n.parentElement;
        if (!p || p.closest('script, style') || leave.some(e => e.contains(p))) continue;
        out.push(n.textContent);
    }
    for (const el of document.body.querySelectorAll('[placeholder], [aria-label], [title], [alt]'))
        if (!leave.some(e => e.contains(el))) for (const a of ['placeholder', 'aria-label', 'title', 'alt']) if (el.hasAttribute(a)) out.push(el.getAttribute(a));
    return out.join(' ');
}"""

def main():
    errors = []
    app, html = source("app.js"), source("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=UNITS, settings={"examplesChecked": True, "recipeExamplesChecked": True})

        print("\n--- 1. No Compendium and no 'the Mentor' on screen ---")
        everything = page.evaluate(PAGE_TEXT, [])
        check("the page's text, hints and labels never say Compendium or 'the Mentor'", not OLD_NAMES.findall(everything), OLD_NAMES.findall(everything))
        updates = updates_text(app)
        check("no Updates entry says Compendium or 'the Mentor'", not OLD_NAMES.findall(updates), OLD_NAMES.findall(updates))
        check("Updates entries now name Colour Lab and Mentor's window instead", "Colour Lab: Colour wheel" in updates and "Mentor's window" in updates)
        shown = page.evaluate("() => [shopSourceShown('Compendium: Colour wheel, Blue'), shopSourceShown('Compendium: Ask the Mentor')]")
        check("an old saved 'Compendium: ...' source still shows as Colour Lab", shown == ["Colour Lab: Colour wheel, Blue", "Colour Lab: Paint Picker"], shown)

        print("\n--- 2. No Games Workshop names in the app's own words ---")
        help_text = page.evaluate(PAGE_TEXT.replace("document.body", "document.getElementById('view-help')"), ["#about", "#help-scan-brands"])
        check("Help (apart from the scanner's brand list and the trademark notice) has no Games Workshop name", not GW.findall(help_text), GW.findall(help_text))
        check("Help's examples are invented: bright yellow, Spearmen 1, Goblins, your army list app",
              all(w in help_text for w in ["Eyes: bright yellow, then pale yellow", "Spearmen 1, Spearmen 2", "10x Goblins", "From your army list app"]))
        # LP1: the fan-made notice in How it works > About became the rights line ("not affiliated with, endorsed by or sponsored by ... trade marks of Games Workshop Ltd").
        # The Updates page still carries the old short notice, and the Help trade-mark line is kept.
        check("the trademark notice is unchanged", ("not affiliated with or endorsed by Games Workshop" in html or "not affiliated with, endorsed by or sponsored by Games Workshop" in html) and "trademarks of Games Workshop Ltd" in html and "trade marks of Games Workshop Ltd" in html)
        panel = page.evaluate(PAGE_TEXT.replace("document.body", "document.getElementById('import-area')"), [])
        check("the army list panel and its check have no Games Workshop name", not GW.findall(panel) and "In your army list app" in panel, GW.findall(panel))
        hints = re.findall(r'placeholder\s*=\s*"((?:[^"\\]|\\.)*)"', app) + re.findall(r'placeholder="([^"]*)"', html)
        bad = [h for h in hints if GW.search(h)]
        check(f"none of the {len(hints)} hints inside text boxes (app.js and index.html) names a Games Workshop thing", hints and not bad, bad)
        check("the paste, recipe, scheme and scan hints are the new plain ones",
              all(h in hints for h in ["e.g. My rust knights", "e.g. Blue armour", "Eyes: bright yellow, then pale yellow", "Or type a paint name"])
              and any(h.startswith("Bog goblins") for h in hints), [h for h in hints if h.startswith(("e.g.", "Eyes", "Or type", "Bog"))])
        check("no Updates entry names a Games Workshop army, unit, paint or app", not GW.findall(updates), GW.findall(updates))

        page.evaluate("() => { document.getElementById('wh-panel').classList.remove('hidden'); document.getElementById('wh-text').value = 'this is not an army list'; document.getElementById('wh-read').click(); }")
        page.wait_for_timeout(200)
        msg = page.evaluate("() => document.getElementById('toast-text').textContent")
        check("a paste that is not an army list gets the plain message, with invented examples",
              msg.startswith("That doesn't look like an exported army list.") and "Captain (60 points)" in msg and "10x Goblins" in msg and not GW.search(msg), msg)

        with page.expect_download() as d:
            page.evaluate("document.getElementById('template-button').click()")
        with open(d.value.path(), encoding="utf-8", newline="") as f:
            tpl = f.read().splitlines()
        check("the CSV template has its column titles and three rows, none with a Games Workshop name",
              tpl[0].startswith("name,game,faction,stage") and len(tpl) == 4 and not any(GW.search(l) for l in tpl), tpl)
        check("the template's rows use the invented Spearmen and Bone giant of the Bone warband",
              tpl[1].startswith("Spearmen,Skirmish,Bone warband,") and tpl[3].startswith("Bone giant,Skirmish,Bone warband,") and '"Magnetised, so can swap arms"' in tpl[3], tpl)
        check("no errors on the page", not errors, errors)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
