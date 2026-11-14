"""UX1 part 2 (UX1b) tests for Minifolio (fixes from the 2 Nov user testing). New behaviour only:
5. Import CSV reads files split by semicolons (Excel's style in much of Europe) or tabs as well as commas; a "status" column is read
   as the stage (everyday words such as primed, WIP and painted are matched to your stages; anything else is listed on the check
   screen); a refused file's message stays on screen until OK is pressed (it used to be a message that went after a few seconds).
6. Small screens and keyboard: the Painting and Tools switches never break a word at 320 px or at 130% zoom; the Add unit, palette
   search and army-list faction hints fit their boxes; switch parts, Close, Tick all and the import rows are 44 px tap targets at
   130% zoom; text sizes are in rem, so they follow the browser's text size and are unchanged at the normal size; Skip to content
   is the first Tab stop; one Tab from Mentor's Close reaches the text box; after Clear examples the focus is on the page's first control.
(The default look at the normal text size was checked pixel for pixel against v125 with before/after screenshots, see the PR.)
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import quiet, wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SEMI = "﻿Name;Game;Faction;Status;Count;Notes\r\nBoyz;Sci-fi;Greens;Primed;10;\"Mob 1; the big one\"\r\nWarboss;Sci-fi;Greens;painted;1;\r\n"
STATUS = ("name,faction,status\nA,X,Primed\nB,X,painted\nC,X,WIP\nD,X,built\nE,X,Lost in the post\nF,X,needs touch-ups\nG,X,3\nH,X,\n")
READ = "(text) => { text = text.replace(/^\\ufeff/, \"\"); const r = csvToUnits(parseCSV(text, csvSeparator(text))); return r.problem ? r : { units: r.units.map(u => [u.name, u.faction, u.stage, u.stageGiven, u.count, u.note]), unknown: [...r.unknownStages] }; }"

# Words broken across two lines inside the switches (a word whose letters sit on more than one line).
BROKEN = """(sel) => { const out = []; for (const b of document.querySelectorAll(sel)) { const n = b.firstChild; if (!n || n.nodeType !== 3) continue;
  const re = /\\S+/g; let m; while ((m = re.exec(n.data))) { const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
  if (new Set([...r.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top))).size > 1) out.push(m[0]); } } return out; }"""
# Placeholders that don't fit inside their box.
CUT = """(ids) => { const c = document.createElement('canvas').getContext('2d'); return ids.filter(id => { const i = document.getElementById(id);
  const cs = getComputedStyle(i); c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
  return c.measureText(i.placeholder).width > i.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) + 0.5; }); }"""
SIZES = """(sel) => [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })"""

def go(page, tab, sub=None):
    page.evaluate("() => { const d = document.activeElement; if (d && d.blur) d.blur(); }")
    page.click(f'nav button[data-tab="{tab}"]'); wait_settled(page); quiet(page)
    if sub:
        page.click(f'#more-seg button[data-page="{sub}"]' if tab == "guides" else f'#recipe-seg button[data-view="{sub}"]'); wait_settled(page); quiet(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page)

        print("--- 5. CSV import ---")
        got = page.evaluate(READ, SEMI)
        check("a semicolon file (Excel's European style) is read: names, faction, count, and a quoted cell keeps its semicolon",
              got.get("units") and [u[0] for u in got["units"]] == ["Boyz", "Warboss"] and got["units"][0][1] == "Greens"
              and got["units"][0][4] == 10 and got["units"][0][5] == "Mob 1; the big one", got)
        got = page.evaluate(READ, "name\tfaction\tcount\nBoyz\tGreens\t10\n")
        check("a tab-separated file is read too", got.get("units") == [["Boyz", "Greens", 0, False, 10, ""]], got)
        got = page.evaluate(READ, "name,notes\nBoyz,\"one; two\"\n")
        check("a comma file with a semicolon inside quotes is still read with commas", got.get("units") and got["units"][0][5] == "one; two", got)
        got = page.evaluate(READ, STATUS)
        stages = {u[0]: (u[2], u[3]) for u in got.get("units", [])}
        want = {"A": (3, True), "B": (5, True), "C": (4, True), "D": (2, True), "E": (0, False), "F": (6, True), "G": (3, True), "H": (0, False)}
        check("a Status column is the stage: Primed, painted (first Done stage), WIP, built, needs touch-ups and a number", stages == want, stages)
        check("…a status it can't match is listed, nothing else", got.get("unknown") == ["Lost in the post"], got.get("unknown"))
        got = page.evaluate(READ, "name,stage,status\nA,Assembled,painted\n")
        check("a stage column is used before a status column", got.get("units") and got["units"][0][2] == 2, got)
        page.evaluate("() => { settings.doneFrom = 4; }")
        got = page.evaluate(READ, "name,status\nA,done\n")
        check("'done' follows where Done starts in your stages", got.get("units") and got["units"][0][2] == 4, got)
        page.evaluate("() => { settings.doneFrom = 5; }")

        go(page, "units")
        page.evaluate("() => placeImportArea('units')")
        page.set_input_files("#csv-file", files=[{"name": "army.csv", "mimeType": "text/csv", "buffer": STATUS.encode()}])
        page.wait_for_selector("#review:not(.hidden)")
        summary = page.inner_text("#review-summary")
        check("the check screen names the status it couldn't match", 'Lost in the post' in summary and "don't match" in summary, summary)
        page.click("#review-cancel"); quiet(page)
        page.set_input_files("#csv-file", files=[{"name": "eu.csv", "mimeType": "text/csv", "buffer": SEMI.encode("utf-8")}])
        page.wait_for_selector("#review:not(.hidden)")
        check("a semicolon file opens the check with its 2 units", page.locator("#review-list li").count() == 2, page.locator("#review-list li").count())
        page.click("#review-cancel"); quiet(page)
        page.set_input_files("#csv-file", files=[{"name": "nonames.csv", "mimeType": "text/csv", "buffer": b"unit_title,faction\nBoyz,Orks\n"}])
        page.wait_for_selector("#dialog-backdrop:not(.hidden)")
        page.wait_for_timeout(1500)
        box = page.evaluate("""() => ({ open: !document.getElementById('dialog-backdrop').classList.contains('hidden'),
            text: document.getElementById('dialog-message').textContent, no: document.getElementById('dialog-no').classList.contains('hidden'),
            ok: document.getElementById('dialog-yes').textContent, focus: document.activeElement.id,
            toast: !document.getElementById('toast').classList.contains('hidden') })""")
        check("a refused file's message stays up (the app's own box, not a message that times out), with one OK button",
              box["open"] and 'no "name" column' in box["text"] and box["no"] and box["ok"] == "OK" and box["focus"] == "dialog-yes" and not box["toast"], box)
        page.keyboard.press("Enter")
        check("…and OK closes it", page.evaluate("() => document.getElementById('dialog-backdrop').classList.contains('hidden')"))
        page.set_input_files("#csv-file", files=[{"name": "titles.csv", "mimeType": "text/csv", "buffer": b"name;faction\n"}])
        page.wait_for_selector("#dialog-backdrop:not(.hidden)")
        check("'No units found' stays up too", "No units found in that file." in page.inner_text("#dialog-message"))
        page.click("#dialog-yes")
        help_text = t.read("index.html")
        check("Help names semicolons, the status column and the message that stays",
              "by semicolons" in help_text and "A <strong>status</strong> column works too" in help_text and "stays until you press OK" in help_text)

        print("\n--- 6. Keyboard ---")
        t.load(page)
        page.goto(t.BASE + "manifest.json")
        page.goto(t.URL + "#units")   # opens straight on Models, with nothing focused yet (as a keyboard user arrives)
        t.app_ready(page)
        page.keyboard.press("Tab")
        first = page.evaluate("() => { const a = document.activeElement, r = a.getBoundingClientRect(); return [a.id, Math.round(r.height), Math.round(r.width), getComputedStyle(a).clip]; }")
        check("Skip to content is the first Tab stop, shown while it has the focus (44 px tall)", first[0] == "skip-link" and first[1] >= 44 and first[2] > 44, first)
        page.keyboard.press("Enter")
        check("…and takes you past the menu bar to the page's first control", page.evaluate("document.activeElement.dataset.mview") == "models", page.evaluate("document.activeElement.outerHTML.slice(0, 120)"))   # WL1: the Models | Wish list switch now sits above Add unit, so it is the first control of Models
        check("the skip link waits above the top of the screen when it doesn't have the focus",
              page.evaluate("() => document.getElementById('skip-link').getBoundingClientRect().bottom <= 0"))
        page.focus("#mentor-button")
        page.keyboard.press("Enter"); quiet(page)
        page.keyboard.press("Tab")
        check("Mentor: one Tab from Close (where it opens) reaches the text box", page.evaluate("document.activeElement.className") == "mentor-input",
              page.evaluate("document.activeElement.className"))
        page.keyboard.press("Shift+Tab")
        check("…and Shift+Tab goes back to Close", page.evaluate("document.activeElement.className") == "mentor-close")
        page.keyboard.press("Escape"); quiet(page)
        go(page, "units")
        page.focus("#examples-card .clear-examples")
        page.keyboard.press("Enter"); quiet(page)
        page.wait_for_timeout(100)
        check("after Clear examples the focus is on the page's first control, not lost", page.evaluate("document.activeElement.dataset.mview") == "models",   # WL1: the first control on Models is now the Models | Wish list switch
              page.evaluate("document.activeElement.tagName + '#' + document.activeElement.id"))

        print("\n--- 6. Text sizes ---")
        sizes = page.evaluate("""() => [getComputedStyle(document.querySelector('.hint')).fontSize, getComputedStyle(document.body).fontSize,
            getComputedStyle(document.querySelector('.arc [data-tab]')).fontSize]""")
        check("at the normal text size the sizes are as before (13 px hints, 16 px body, 11 px menu labels)", sizes == ["13px", "16px", "11px"], sizes)
        css = t.read("index.html").split("<style>", 1)[1].split("</style>", 1)[0]
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        px = [m.group(1).strip()[-60:] for m in re.finditer(r"([^{}]*)\{[^{}]*font-size\s*:\s*[\d.]+px", css)]
        fixed = re.compile(r"\.arc\b|\.mentor-orb|launching|\.basket")
        check("every font size in the styles is in rem, except the fixed-shape menu bar, start circle and basket pill", px and all(fixed.search(s) for s in px), px)
        ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        cdp = ctx.new_cdp_session(page)
        cdp.send("Page.enable")
        cdp.send("Page.setFontSizes", {"fontSizes": {"standard": 20, "fixed": 16}})   # the browser's text size set to 125%
        t.load(page)
        go(page, "units")
        sizes = page.evaluate("""() => [getComputedStyle(document.querySelector('.hint')).fontSize, getComputedStyle(document.body).fontSize,
            getComputedStyle(document.querySelector('#toggle-add')).fontSize]""")
        check("with the browser's text size at 125%, the app's text follows (hints 16.25 px, body 20 px)", sizes[:2] == ["16.25px", "20px"], sizes)
        check("…and nothing scrolls sideways", page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        ctx.close()

        print("\n--- 6. Small screens ---")
        for w, h in [(320, 568), (277, 492)]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", reduced_motion="reduce", has_touch=True, is_mobile=True)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page)
            label = f"{w} px" + (" (360 px at 130% zoom)" if w == 277 else "")
            go(page, "recipes")
            broken = page.evaluate(BROKEN, "#recipe-seg button")
            small = [s for s in page.evaluate(SIZES, "#recipe-seg button") if min(s) < 44]
            go(page, "guides", "settings")
            broken += page.evaluate(BROKEN, "#more-seg button")
            small += [s for s in page.evaluate(SIZES, "#more-seg button") if min(s) < 44]
            check(f"{label}: no Painting or Tools switch label breaks mid-word", not broken, broken)
            check(f"{label}: every switch part is 44 px or more both ways", not small, small)
            check(f"{label}: nothing scrolls sideways", page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
            go(page, "units")
            page.click("#toggle-add"); quiet(page)
            cut = page.evaluate(CUT, ["name-input", "hobby-input", "faction-input"])
            page.click("#add-wh"); quiet(page)
            page.fill("#wh-text", "My list (500 points)\n\nOrks\n\nBoyz (85 points)\n  • 10x Boy\n\nGretchin (40 points)\n  • 10x Gretchin\n")
            page.click("#wh-read"); page.wait_for_selector("#review:not(.hidden)"); quiet(page)
            if w == 320:
                cut += page.evaluate(CUT, ["wh-faction"])
                check(f"{label}: the Add unit and army-list hints fit their boxes", not cut, cut)
            targets = page.evaluate(SIZES, "#units-import-close, #review-all, #review-none, #review-list .review-row > label")
            check(f"{label}: Close, Tick all, Untick all and each import row are 44 px tap targets", len(targets) == 5 and all(min(s) >= 44 for s in targets), targets)
            if w == 320:
                go(page, "recipes", "palette")
                check(f"{label}: the palette search hint fits", not page.evaluate(CUT, ["palette-search"]))
            ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        t.load(page)
        go(page, "recipes")
        widths = {round(s[0]) for s in page.evaluate(SIZES, "#recipe-seg button")}
        tops = page.evaluate("() => new Set([...document.querySelectorAll('#recipe-seg button')].map(b => Math.round(b.getBoundingClientRect().top))).size")
        # AB7b: the Painting tabs are words with a line under the chosen one, each as wide as its word, so "at the same width" no longer holds; one line still does
        check("390 px: the five Painting parts still sit on one line", tops == 1 and len(widths) >= 1, (tops, widths))
        ctx.close()
        browser.close()

    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
