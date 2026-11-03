"""UX1 tests for Minifolio (fixes from the 2 Nov user testing). New behaviour only:
1. Army list paste: roster lines from other list builders ("10x Intercessors [180pts]") come in with their counts and the
   faction from the roster's top line; "Intercessor Squad" with "1x Sergeant" and "9x Intercessor" lines is one unit of 10;
   a line that can't be read is listed on the check screen ("Not read: line N"), never dropped.
   (The formats that already worked are checked in test_v14, v19, v22, v60 and test_real_export.)
2. Saving a recipe in the full editor never marks a paint Owned when its name isn't in the paint list; "Do you own these?"
   only lists paints that are; the typed paint can still go on the shopping list.
3. A touch tap on "+ Add step" straight after typing in a paint box works first time (the bar used to come back under the
   finger), and the last control of a page can be scrolled clear of the bar, the Mentor button and the back arrow.
4. "Not now" on the kept unfinished recipe question starts the new recipe and keeps the old one; the kept-recipe card is not
   shown behind the question. (Escape still starts nothing: test_v26.)
5b. The army-list reader reads the security review's long-line payload and a 10 KB paste at once; the paste box is capped.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROSTER = """++ Army Roster (Imperium - Space Marines) [2,000pts] ++

Character
Captain in Gravis Armour [95pts]: Master-crafted heavy bolt rifle, Warlord
Lieutenant x1 (75 pts)

Battleline
10x Intercessors [180pts]
  • 9x Intercessor
  • 1x Intercessor Sergeant
5 Assault Intercessors - 75 points
Infiltrators (5) ........ 100

Other
3x Aggressors
Redemptor Dreadnought: Macro plasma incinerator
2 x Outriders
Repulsor Executioner [220pts]
   Hellstorm bolter
~~~~

Total: 2,000pts
"""
ROSTER_WANT = [["Captain in Gravis Armour", 1], ["Lieutenant", 1], ["Intercessors", 10], ["Assault Intercessors", 5],
               ["Infiltrators", 5], ["Aggressors", 3], ["Redemptor Dreadnought", 1], ["Outriders", 2], ["Repulsor Executioner", 1]]
SQUADS = ("My Marines (1000 Points)\r\n\r\nSpace Marines\r\nGladius Task Force\r\nIncursion (1000 Points)\r\n\r\nCHARACTERS\r\n\r\n"
          "Captain (80 Points)\r\n  • Warlord\r\n  • 1x Master-crafted boltgun\r\n\r\nBATTLELINE\r\n\r\n"
          "Intercessor Squad (160 Points)\r\n  • 1x Sergeant\r\n  • 9x Intercessor\r\n  • 1x Astartes grenade launcher\r\n\r\n"
          "Terminator Squad (170 points)\r\n  • 1x Terminator Sergeant\r\n  • 4x Terminator\r\n\r\n"
          "Exported with App Version: v1.24.0 (1), Data Version: v541\r\n")

# The last control on the page, and the top of the bar, the Mentor button and the back arrow (whichever is highest).
CLEARANCE = r"""() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'
    && !e.closest('.tabs, .back-menu, #mentor-backdrop, .toast, #dialog-backdrop, .hidden, [hidden]')
    && !(e.closest('details:not([open])') && !e.matches('summary')); };
  const els = [...document.querySelectorAll('main button, main a[href], main input, main select, main textarea, main summary')].filter(vis);
  const last = Math.max(...els.map(e => e.getBoundingClientRect().bottom));
  const back = document.querySelector('.back-menu');
  const tops = [document.querySelector('.arc').getBoundingClientRect().top, document.querySelector('#mentor-button').getBoundingClientRect().top];
  if (back && getComputedStyle(back).visibility !== 'hidden') tops.push(back.getBoundingClientRect().top);
  return Math.round(Math.min(...tops) - last);
}"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.load(page, units=[])

        print("--- 1. Army list paste ---")
        got = page.evaluate("(text) => parseWarhammerList(text)", ROSTER)
        check("a list builder's roster: every unit with its count", got and [[u["name"], u["count"]] for u in got["units"]] == ROSTER_WANT, got)
        check("…the faction comes from the roster's top line", got and got["faction"] == "Space Marines", got and got["faction"])
        check("…the line it can't read is listed by number, headings and the total are not", got and got.get("notRead") == [20], got and got.get("notRead"))
        got = page.evaluate("(text) => parseWarhammerList(text)", SQUADS)
        check("Intercessor Squad with 1x Sergeant and 9x Intercessor is one unit of 10; wargear lines don't count",
              got and [[u["name"], u["count"]] for u in got["units"]] == [["Captain", 1], ["Intercessor Squad", 10], ["Terminator Squad", 5]], got)
        got = page.evaluate("() => parseWarhammerList('Intercessor Squad\\n  • 1x Sergeant\\n  • 9x Intercessor\\nCaptain\\n  • 1x Master-crafted boltgun')")
        check("…the same in a list typed by hand", got and [[u["name"], u["count"]] for u in got["units"]] == [["Intercessor Squad", 10], ["Captain", 1]], got)

        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(200)
        page.click("#toggle-add")
        page.click("#add-wh")
        page.fill("#wh-text", ROSTER)
        page.click("#wh-read")
        page.wait_for_selector("#review:not(.hidden)")
        check("the check screen shows all 9 units", page.locator("#review-list li").count() == 9, page.locator("#review-list li").count())
        line = page.locator("#review-not-read")
        check("…and one line naming the line it couldn't read", line.is_visible() and line.inner_text().strip() == "Not read: line 20.", line.inner_text())
        check("…with the roster's faction in the faction box", page.input_value("#wh-faction") == "Space Marines", page.input_value("#wh-faction"))
        page.click("#review-cancel")

        print("\n--- 5b. Long pastes read at once ---")
        timing = page.evaluate("""() => {
            const tabs = '\\t'.repeat(1500);
            let t0 = performance.now(); parseWarhammerList('My list\\nOrks\\n' + tabs + 'x' + tabs); const a = performance.now() - t0;
            let big = 'My list\\nOrks\\n'; while (big.length < 10000) big += 'x' + ' '.repeat(140) + 'y (' + ' '.repeat(140) + '\\n';
            let big2 = ''; while (big2.length < 10000) big2 += '10x ' + ' '.repeat(140) + 'a' + ' '.repeat(140) + 'x5\\n';
            t0 = performance.now(); parseWarhammerList(big); parseWarhammerList(big2); const b = performance.now() - t0;
            return [Math.round(a), Math.round(b)]; }""")
        check("the review's 3 KB payload and two 10 KB pastes read in well under a second", timing[0] < 200 and timing[1] < 300, timing)
        check("the paste box holds at most 50,000 characters", page.get_attribute("#wh-text", "maxlength") == "50000")
        long_line = page.evaluate("() => parseWarhammerList('10x Boyz\\n' + 'Gretchin '.repeat(40) + '\\n5x Nobz')")
        check("a line over 300 characters is not read, and is listed", long_line and long_line.get("notRead") == [2] and len(long_line["units"]) == 2, long_line)

        print("\n--- 2. Typed paints are not marked Owned ---")
        t.load(page, paints=[], recipes=[], units=[], settings={"examplesChecked": True})
        t.open_editor(page)
        page.fill('input[placeholder="e.g. Ultramarine blue armour"]', "Blue armour")
        t.set_step_paint(page, 0, "Macragge Blue")
        t.add_step(page)
        t.set_step_paint(page, 1, "macrag")
        own = page.locator("#recipe-own")
        check("Do you own these? lists only the paint in the paint list",
              own.is_visible() and "Macragge Blue" in own.inner_text() and "macrag" not in own.locator(".own-names").inner_text(), own.inner_text())
        page.click("#recipe-page button:has-text('Save recipe')")
        page.wait_for_timeout(300)
        status = page.evaluate("() => Object.fromEntries(book.paints.map(p => [p.name, paintStatus(p)]))")
        check("the known paint follows the answer (All: Owned); the typed one is Not owned",
              status.get("Macragge Blue") == "owned" and status.get("macrag") == "notowned", status)
        shop = page.locator("#recipe-page .recipe-shop-add")
        check("the typed paint can go on the shopping list from the recipe", shop.count() == 1 and "(1)" in shop.inner_text(), shop.count() and shop.inner_text())
        if shop.count():
            shop.click()
            page.wait_for_timeout(200)
            check("…and it does", page.evaluate("() => paintStatus(book.paints.find(p => p.name === 'macrag'))") == "wishlist")

        print("\n--- 4. Not now starts the new recipe ---")
        t.open_editor(page)
        page.fill('input[placeholder="e.g. Ultramarine blue armour"]', "Half written")
        page.wait_for_function("() => { try { return !!JSON.parse(localStorage.getItem('shades-of-grey-drafts')).recipe } catch (e) { return false } }")
        page.reload()
        t.app_ready(page)
        t.leave_launch(page)
        page.click('nav button[data-tab="recipes"]')
        page.wait_for_timeout(300)
        kept = page.evaluate("localStorage.getItem('shades-of-grey-drafts')")
        check("the kept recipe's card shows on the list", page.is_visible("#draft-card-recipe"))
        page.click("#new-recipe")
        page.wait_for_timeout(250)
        check("+ New recipe asks once: the question is up and the card behind it is hidden",
              page.is_visible("#dialog-backdrop") and not page.is_visible("#draft-card-recipe"))
        page.click("#dialog-no")
        page.wait_for_timeout(300)
        check("Not now opens the new recipe with the cursor in its box",
              page.evaluate("!!recipeDraft && !!recipeDraft.quick") and page.evaluate("document.activeElement && document.activeElement.id") == "quick-lines")
        check("…and the old one is kept, untouched", page.evaluate("localStorage.getItem('shades-of-grey-drafts')") == kept)
        ctx.close()

        print("\n--- 3. Taps near the bar ---")
        for (w, h, dark) in [(390, 844, True), (360, 640, False)]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True, service_workers="block",
                                      reduced_motion="reduce", color_scheme="dark" if dark else "light")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, units=[], settings={"examplesChecked": True})
            t.open_editor(page)
            page.locator('[data-key="step-0-paint-0"]').fill("Macragge Blue")
            button = page.locator("#recipe-page button.add-step")
            button.scroll_into_view_if_needed()
            covered = page.evaluate("""() => { const r = document.querySelector('#recipe-page button.add-step').getBoundingClientRect();
                return document.body.classList.contains('typing') && r.bottom > document.querySelector('.arc').getBoundingClientRect().top; }""")
            box = button.bounding_box()
            page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(400)
            check(f"{w} px: the first tap on + Add step, just after typing, adds a step (the bar was hidden over it: {covered})",
                  page.locator("#recipe-page [data-key='step-1-paint-0']").count() == 1)
            gaps = {}
            for name in ["recipes", "settings"]:
                if name == "recipes":
                    t.blur(page)
                else:
                    page.evaluate("recipeDraft = null; renderRecipes(); showTab('guides')")
                    page.click('#more-seg button[data-page="settings"]')
                page.wait_for_timeout(300)
                page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(200)
                gaps[name] = page.evaluate(CLEARANCE)
            check(f"{w} px: scrolled to the end, the last control sits clear of the bar (editor, Settings)", all(g >= 0 for g in gaps.values()), gaps)
            ctx.close()
        browser.close()

    check("no page errors", not errors, errors)
    check("no browser pop-ups", not dialogs, dialogs)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
