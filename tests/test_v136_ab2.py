"""AB2 tests for Minifolio (display tidy from the approved AI-tells list). New behaviour only:
1. Mentor's sources: no "Sources" label; each source is a link (button) with the guide's own title, one per line, 44 px rows.
2. (FB1: the version tag is shown again beside the title) Updates says "This is vNNN.".
3. The scheme check: no Fine / Look at this / Suggestion tags (the words for screen readers are hidden); a tick or cross icon with words; the new verdicts; "Spot colour".
4. Moving a unit to Done: "<name> are done." / "<name> is done.", "First one off the pile." for the first, "That's the whole <army>." for the last of an army; Undo still works.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import version_helpers as vh

results = []
STAGE_NAMES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted", "Tabletop ready", "Needs touch-ups", "Display ready"]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, name, stage, count=1, faction="Green army"):
    return {"id": i, "name": name, "hobby": "Sci-fi", "faction": faction, "stage": stage, "count": count, "added": "2026-10-01", "log": [["2026-10-01", stage]]}

def toast(page):
    return page.evaluate("() => document.getElementById('toast-text').textContent")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1. Mentor's sources ---")
        t.load(page, units=[])
        page.evaluate("() => document.getElementById('mentor-button').click()"); t.quiet(page)
        page.fill(".mentor-input", "how do I paint a metal armour")
        page.click(".mentor-send")
        page.wait_for_selector(".mentor-source", timeout=8000)
        info = page.evaluate("""() => { const g = document.querySelector('.mentor-sources'); const rows = [...g.querySelectorAll('.mentor-source')];
            return { label: !!document.querySelector('.mentor-sources-label'), words: g.parentElement.textContent.includes('Sources'),
              n: rows.length, tags: rows.map(r => r.tagName), h: rows.map(r => r.getBoundingClientRect().height),
              tops: rows.map(r => r.getBoundingClientRect().top), svg: rows.every(r => r.querySelector('svg') || r.querySelector('.swatch')),
              names: rows.map(r => r.textContent.trim()), seeAlsoClass: g.classList.contains('guides-seealso') }; }""")
        check("no 'Sources' label", not info["label"] and not info["words"], info)
        check("each source is a link-style button with a title", info["n"] >= 1 and all(x == "BUTTON" for x in info["tags"]) and all(n for n in info["names"]), info)
        check("rows are 44 px or more, one per line", all(h >= 43.9 for h in info["h"]) and info["tops"] == sorted(set(info["tops"])), info)
        check("each has a small icon and uses the See also style", info["svg"] and info["seeAlsoClass"], info)
        page.click(".mentor-source")
        page.wait_for_timeout(600)
        check("a source still opens its guide", page.evaluate("() => settings.tab") in ("guides", "colour", "colours", "recipes"), page.evaluate("() => settings.tab"))

        print("\n--- 2. Version number ---")
        t.load(page, units=[])
        shown = page.evaluate("() => { const e = document.getElementById('version-tag'); return getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }")
        # FB1 (George, 8 Nov): the version is back at the top of every screen, so the v136 "not shown" check now expects it to be shown.
        check("the version tag is shown on a section (FB1, replaces the v136 check)", shown)
        page.evaluate("() => document.querySelector('nav button[data-tab=more]') && document.querySelector('nav button[data-tab=more]').click()")
        note = page.evaluate("() => (document.getElementById('version-note') || {}).textContent || ''")
        ver = vh.current()
        check("Updates says 'This is vNNN.'", note == f"This is {ver}.", note)
        helptext = open(os.path.join(t.ROOT, "index.html"), encoding="utf-8").read()
        check("Help no longer says the number is next to the title", "next to the title on every page" not in helptext)

        print("\n--- 3. Scheme check ---")
        out = page.evaluate("""() => { const C = MinifolioColour;
            const bad = schemeCheckWords(C.schemeCheck([{ colour: '#e02020', uses: 1 }, { colour: '#2040e0', uses: 1 }, { colour: '#e0d020', uses: 1 }, { colour: '#20c030', uses: 1 }]));
            const good = schemeCheckWords(C.schemeCheck([{ colour: '#0d407f', uses: 3 }, { colour: '#f4741c', uses: 1 }, { colour: '#0b0b0b', uses: 1 }]));
            return { bad, good }; }""")
        check("a good scheme reads 'Hangs together.'", out["good"]["verdict"] == "Hangs together.", out["good"]["verdict"])
        check("a failing scheme reads a fix verdict", out["bad"]["verdict"] in ("Nearly. One thing to fix.", "Not yet. Two things to fix."), out["bad"]["verdict"])
        check("the loud colours line is plain and a cross", out["bad"]["rows"][0]["label"] == "Loud colours" and out["bad"]["rows"][0]["ok"] is False and out["bad"]["rows"][0]["text"].endswith("at once will fight."), out["bad"]["rows"][0])
        check("the third line is called Spot colour", out["good"]["rows"][2]["label"] == "Spot colour", out["good"]["rows"][2])
        page.evaluate("""() => { colourIdeasState.check = true; const box = buildSchemeCheck([{ colour: '#e02020', uses: 1 }, { colour: '#2040e0', uses: 1 }, { colour: '#e0d020', uses: 1 }, { colour: '#20c030', uses: 1 }], () => {});
            box.id = 'ab2-check'; document.body.appendChild(box); }""")
        dom = page.evaluate("""() => { const b = document.getElementById('ab2-check'); return { tags: b.querySelectorAll('.idea-tag').length,
            icons: [...b.querySelectorAll('.scheme-list li')].map(li => !!li.querySelector('svg.scheme-mark[aria-hidden=true]') && !!li.querySelector('.sr-only')),
            text: b.innerText }; }""")
        check("no Fine / Look at this / Suggestion tags (the words for screen readers are hidden)", dom["tags"] == 0 and not any(w in dom["text"] for w in ("Look at this", "Suggestion")), dom["text"])
        check("every line has an icon and words for screen readers", all(dom["icons"]) and len(dom["icons"]) == 3, dom)

        print("\n--- 4. Done messages ---")
        def move(units, uid):
            t.load(page, units=units, settings={"stages": STAGE_NAMES, "doneFrom": 5, "examplesChecked": True})
            page.evaluate("(i) => changeStage(i, 1)", uid)
            page.wait_for_timeout(500)
            return toast(page)
        check("ordinary unit of many: 'Brutes are done.'", move([unit(1, "Captain", 5, 1, "Blue army"), unit(2, "Brutes", 4, 10, "Green army"), unit(3, "Scouts", 2, 5, "Green army")], 2) == "Brutes are done.")
        check("ordinary single model: 'Captain is done.'", move([unit(1, "Guardians", 5, 5, "Gold army"), unit(2, "Captain", 4, 1, "Blue army"), unit(3, "Scouts", 1, 3, "Blue army")], 2) == "Captain is done.")
        check("first ever: 'First one off the pile.'", move([unit(1, "Brutes", 4, 10), unit(2, "Scouts", 1, 3)], 1) == "First one off the pile.")
        check("example units do not stop the first one", move([dict(unit(1, "Guardians", 6, 5, "Gold army"), example=True), unit(2, "Brutes", 4, 10)], 2) == "First one off the pile.")
        check("last of an army: the whole army", move([unit(1, "Guardians", 5, 5, "Gold army"), unit(2, "Brutes", 5, 10, "Green army"), unit(3, "Scouts", 4, 3, "Green army")], 3) == "That's the whole Green army.")
        check("an army name without 'army' gets the word added", move([unit(1, "Guardians", 5, 5, "Orks"), unit(2, "Boyz", 5, 10, "Orks"), unit(3, "Nobz", 4, 3, "Orks")], 3) == "That's the whole Orks army.")
        check("no pride line when the unit is not yet Done", move([unit(1, "Guardians", 5, 5, "Gold army"), unit(2, "Brutes", 2, 10, "Green army")], 2).startswith("Brutes"), "")
        check("no exclamation marks", "!" not in toast(page))
        msg = move([unit(1, "Guardians", 5, 5, "Gold army"), unit(2, "Brutes", 4, 10, "Green army")], 2)
        page.click("#toast-undo"); page.wait_for_timeout(300)
        check("Undo puts the unit back a stage", page.evaluate("() => models.find(m => m.id === 2).stage") == 4)
        check("no sideways scroll", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
