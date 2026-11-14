"""Chunk RS4b tests for Minifolio: the simpler Check paints review in Paste recipes. New behaviour only.

1. All paints matched: no cards, the line reads "All paints matched.", the matched paints sit behind "Show the N matched" (closed to start).
2. One unclear paint: one card, "You wrote" and the typed text, the best match already picked (with its brand), then Keep as typed.
   The same typed name in two recipes gives one card that says "in 2 recipes", and the choice changes it in both.
3. A paint with no match starts on Keep as typed; Pick a paint opens the paint list in a pop-up and the picked paint becomes the answer.
4. Nothing blocks Save. "Mark these paints as Owned" ticked: new paints are Owned. Unticked: the recipes are added, no status changes,
   and the best match a card started on is not remembered as shorthand.
5. 24 recipes on a phone (390 dark, 360 light, 320 dark): the bar sits above the bottom menu, no sideways scroll, 44 px tap targets,
   and the last step scrolls clear of the bar.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

HERE = os.path.dirname(os.path.abspath(__file__))
KEEP_NOTE = open(os.path.join(HERE, "keep_note.txt"), encoding="utf-8").read()
SETTINGS = {"tab": "recipes", "recipeView": "recipes", "examplesChecked": True}
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read_notes(page, text):
    page.evaluate("startImport()")
    page.fill("#import-text", text)
    page.click("text=Read notes")
    page.wait_for_selector("#import-save")

def card(page, typed):
    return page.locator("#import-page .import-ask", has=page.locator(".import-typed", has_text=typed))

def options(c):
    return c.locator(".import-option").evaluate_all("els => els.map(e => [e.innerText.replace(/\\s+/g, ' ').trim(), e.querySelector('input').checked])")

def status_of(page, name):
    return page.evaluate("n => { const p = book.paints.find(x => x.name === n); return p ? paintStatus(p) : null; }", name)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.load(page, settings=SETTINGS)

        # 1. All matched.
        read_notes(page, "Ultras\n\nArmour:\nMacragge Blue\nNuln Oil")
        check("all matched: title and line", page.inner_text(".import-check h2") == "Check paints"
              and page.inner_text(".import-check-sum") == "All paints matched.", page.inner_text(".import-check"))
        check("all matched: no cards", page.locator(".import-ask").count() == 0)
        tog = page.locator("#import-matched-toggle")
        check("matched list closed to start", tog.inner_text() == "Show the 2 matched" and tog.get_attribute("aria-expanded") == "false"
              and not page.is_visible("#import-matched"), tog.inner_text())
        tog.click()
        rows = page.eval_on_selector_all("#import-matched li", "els => els.map(e => [!!e.querySelector('.swatch'), e.innerText.replace(/\\s+/g, ' ').trim()])")
        check("opened: swatch, name and brand for each", rows == [[True, "Macragge Blue Citadel"], [True, "Nuln Oil Citadel"]], rows)
        check("one recipe: Save reads Save recipe", page.inner_text("#import-save") == "Save recipe", page.inner_text("#import-save"))

        # 2 and 3. Unclear paints.
        page.evaluate("closeImport(false)")
        read_notes(page, "Reds\n\nArmour:\nKhorn red\nNuln Oil\n\nCloak:\nKhorn red\n\nGoo:\nZorblax Goo")
        check("line has the real numbers", page.inner_text(".import-check-sum") == "1 paint matched. 2 need a look.", page.inner_text(".import-check-sum"))
        khorn = card(page, "Khorn red")
        check("one card per typed name", khorn.count() == 1 and page.locator(".import-ask").count() == 2, page.locator(".import-ask").count())
        check("card: You wrote and the typed text in bold", khorn.locator("legend").inner_text() == "You wrote Khorn red"
              and khorn.locator("legend b").inner_text() == "Khorn red", khorn.locator("legend").inner_text())
        check("card: in 2 recipes", khorn.locator(".import-where").inner_text() == "in 2 recipes")
        opts = options(khorn)
        check("best match picked, with its brand, then Keep as typed", opts[0] == ["Khorne Red Citadel", True] and opts[-1] == ["Keep as typed", False]
              and len(opts) <= 3, opts)
        check("no two options look the same", len({o[0] for o in opts}) == len(opts), opts)
        check("nothing blocks Save", page.is_enabled("#import-save") and page.inner_text("#import-save") == "Save 3 recipes", page.inner_text("#import-save"))
        goo = card(page, "Zorblax Goo")
        check("no match: only Keep as typed, picked", options(goo) == [["Keep as typed", True]] and goo.locator(".import-where").count() == 0, options(goo))
        khorn.locator("label", has_text="Keep as typed").click()
        check("the choice changes it in both recipes", page.locator(".import-paint.resolved", has_text="Khorn red → Khorn Red").count() == 2
              and options(card(page, "Khorn red"))[-1] == ["Keep as typed", True], options(card(page, "Khorn red")))
        card(page, "Zorblax Goo").locator("button", has_text="Pick a paint").click()
        check("Pick a paint opens the paint list in the pop-up", page.is_visible("#dialog") and page.is_visible("#import-paint-pick"))
        page.fill("#import-paint-pick", "Mephiston Red")
        page.locator(".combo-option", has_text="Mephiston Red (Citadel)").first.click()
        goo = card(page, "Zorblax Goo")
        check("the picked paint is the answer", page.is_hidden("#dialog") and options(goo)[0] == ["Mephiston Red Citadel", True]
              and page.locator(".import-paint.resolved", has_text="Zorblax Goo → Mephiston Red").count() == 1, options(goo))
        # FX2: the tick now starts UNTICKED (a pasted note must not silently make every paint Owned), so this part ticks it first.
        check("Owned tick: unticked to start, 44 px", page.get_attribute("#import-owned", "aria-checked") == "false"
              and page.locator("#import-owned").bounding_box()["height"] >= 44)
        page.click("#import-owned")
        check("ticking it", page.get_attribute("#import-owned", "aria-checked") == "true")
        page.click("#import-save")
        page.wait_for_function("() => !importDraft")
        check("tick on: new paints marked Owned", status_of(page, "Nuln Oil") == "owned" and status_of(page, "Khorn Red") == "owned"
              and status_of(page, "Mephiston Red") == "owned", [status_of(page, n) for n in ("Nuln Oil", "Khorn Red", "Mephiston Red")])
        check("a paint you picked is remembered", page.evaluate("(book.shorthand['zorblax goo'] || {}).name") == "Mephiston Red")

        # 4. Tick off.
        before = page.evaluate("book.recipes.length")
        read_notes(page, "Dark\n\nArmour:\nBleck Templar\nLeadbelcher")
        check("starts unticked (FX2: no click needed any more)", page.get_attribute("#import-owned", "aria-checked") == "false")
        page.click("#import-save")
        page.wait_for_function("() => !importDraft")
        check("tick off: the recipe is added", page.evaluate("book.recipes.length") == before + 1)
        check("tick off: nothing about owning changes", status_of(page, "Black Templar") == "" and status_of(page, "Leadbelcher") == "",
              [status_of(page, "Black Templar"), status_of(page, "Leadbelcher")])
        check("the best match a card started on is not remembered", "bleck templar" not in page.evaluate("book.shorthand"))

        # 5. 24 recipes on a phone.
        for w, h, mode in [(390, 844, "dark"), (360, 640, "light"), (320, 640, "dark")]:
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, settings={**SETTINGS, "appearance": mode})
            read_notes(page, KEEP_NOTE)
            m = page.evaluate("""() => {
                const r = (s) => document.querySelector(s).getBoundingClientRect();
                const bar = r('#import-bar'), arc = r('.arc');
                const taps = [...document.querySelectorAll('#import-bar button, .import-option, .import-matched-toggle')].map(e => e.getBoundingClientRect().height);
                return { save: document.querySelector('#import-save').textContent, cards: document.querySelectorAll('.import-ask').length,
                         above: bar.bottom <= arc.top + 1, inView: bar.top > 0, sideways: document.documentElement.scrollWidth > innerWidth,
                         small: taps.filter(x => x < 44).length };
            }""")
            check(f"{w} {mode}: 24 recipes, 9 cards, Save ready", m["save"] == "Save 24 recipes" and m["cards"] == 9, m)
            check(f"{w} {mode}: bar above the bottom menu, no sideways scroll, 44 px taps",
                  m["above"] and m["inView"] and not m["sideways"] and m["small"] == 0, m)
            page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            clear = page.evaluate("""() => { const steps = document.querySelectorAll('#import-page .import-steps li');
                return steps[steps.length - 1].getBoundingClientRect().bottom <= document.querySelector('#import-bar').getBoundingClientRect().top; }""")
            check(f"{w} {mode}: the last step scrolls clear of the bar", clear)
            page.screenshot(path=os.path.join(t.SHOTS, f"v125-rs4b-{w}-{mode}.png"))

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
