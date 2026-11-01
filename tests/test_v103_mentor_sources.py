"""X7 tests for Minifolio (Mentor source links that land on the exact thing). New behaviour only:
1. Each source type (guide, detail recipe, basing tip, Mentor tip, colour) lands on the right place with the right state.
2. The window closes first, then the screen moves; focus lands on the destination; the conversation comes back.
3. A retired key shows one calm line and does not crash; Back after a jump behaves as in the rest of the app.
4. Reduced motion: no move layers left behind.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import use_sample_tips
import test_v24 as t

results = []

# Test-only sample guide, so a guide source has something to open (the real library is filled by X8).
SAMPLE = """const GUIDE_ENTRIES = [{ key: "thin-paint", category: "techniques", title: "Thinning paint", summary: "Thin paint with a little water so it flows.",
  body: ["Add water a drop at a time."], related: [], keywords: ["thin paint", "thinning", "water"] }];
const GUIDE_STARTERS = [];"""

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")

def ask(page, text):
    page.fill(".mentor-input", text)
    n = page.locator(".mentor-reply").count() + 1
    page.keyboard.press("Enter")
    page.wait_for_function("(n) => document.querySelectorAll('.mentor-reply').length >= n", arg=n)

def jump(page, message_sources):
    """Show a Mentor message with these sources in the window (as the engine would), then tap its first source."""
    page.evaluate("(s) => mentorMessages.push({ who: 'mentor', text: 'Here.', sources: s })", message_sources)
    open_it(page)
    page.locator(".mentor-reply").last.locator(".mentor-source").first.click()

def where(page):
    return page.evaluate("() => ({ tab: settings.tab, view: settings.recipeView, win: !!document.querySelector('.mentor-backdrop'), "
                         "focus: document.activeElement && document.activeElement.id || '' })")

def home(page):
    page.evaluate("() => { showTab('dashboard'); }")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        use_sample_tips(ctx)   # A1: the real file no longer holds the sample tips; this test puts them back in memory
        ctx.route("**/guides-data.js*", lambda route: route.fulfill(body=SAMPLE, content_type="text/javascript"))
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.fresh(page)

        # --- a guide, asked for in words ---
        open_it(page)
        ask(page, "thin paint")
        page.locator(".mentor-reply").last.locator(".mentor-source").first.click()
        page.wait_for_function("() => settings.tab === 'guides'")
        w = where(page)
        check("a guide source: the window is already gone when the screen moves", not w["win"])
        check("a guide source opens that entry", page.evaluate("() => guidesState.key === 'thin-paint' && guidesState.kind === 'guide'"))
        check("focus lands on the entry", page.evaluate("() => document.activeElement.id === knowledgeIndex().get('thin-paint', 'guide').id"), w)
        open_it(page)
        check("Ask Mentor brings the same conversation back", page.locator(".mentor-me").count() == 1 and page.locator(".mentor-reply").count() == 1)
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")

        # --- a detail recipe, a basing tip and a Mentor tip (the first of each that the app has) ---
        for label, typ, expr, check_js in [
            ("detail recipe", "recipe", "DETAIL_RECIPES[0].key", "() => guidesState.kind === 'detail' && compendiumState.detail === DETAIL_RECIPES[0].key"),
            ("basing tip", "basing", "BASING_TIPS[0].key", "() => guidesState.kind === 'basing' && compendiumState.basing === BASING_TIPS[0].key"),
            ("Mentor tip", "tip", "MENTOR_TIPS[0].key", "() => guidesState.kind === 'tip' && guidesState.key === MENTOR_TIPS[0].key"),
        ]:
            home(page)
            key = page.evaluate(expr)
            jump(page, [{"type": typ, "key": key, "label": "x"}])
            page.wait_for_function("() => settings.tab === 'guides'")
            check(f"a {label} source lands on that entry", page.evaluate(check_js))
            check(f"a {label} source: focus is inside Guides, the window is closed", where(page)["focus"] != "" and not where(page)["win"], where(page))
            if label == "Mentor tip":
                check("a Mentor tip's focus is on its own entry", page.evaluate("() => document.activeElement.id === knowledgeIndex().get(guidesState.key, 'tip').id"))
            page.evaluate("() => { mentorMessages.length = 0; }")

        # --- colour sources: a hue colour opens its groups, a centre colour is selected ---
        home(page)
        page.evaluate("() => { mentorMessages.length = 0; }")
        open_it(page)
        ask(page, "armour red")
        colour = page.locator(".mentor-reply").last.locator(".mentor-source", has_text="Colour Lab").first
        colour.click()
        page.wait_for_function("() => settings.tab === 'recipes' && settings.recipeView === 'colourlab'")
        w = where(page)
        check("a colour source opens the wheel with that colour chosen", page.evaluate("() => compendiumState.lab === 'wheel' && compendiumState.wheelZoom === 'red' && compendiumState.paintOpen === ''"))
        check("focus lands on the wheel heading line, in view", w["focus"].endswith("wheel-hint") and page.evaluate("() => { const r = document.activeElement.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }"), w)
        check("the window is gone", not w["win"])
        home(page)
        jump(page, [{"type": "colour-lab", "key": "wheel:white", "label": "Colour Lab: Whites", "colour": "#f2f2f0"}])
        page.wait_for_function("() => settings.tab === 'recipes' && settings.recipeView === 'colourlab'")
        check("a centre colour is selected on the wheel", page.evaluate("() => compendiumState.wheel === 'white' && !compendiumState.wheelZoom && !!document.querySelector('[data-wheel=\"white\"][aria-pressed=\"true\"]')"))

        # --- retired keys: one calm line, no crash ---
        home(page)
        jump(page, [{"type": "guide", "key": "retired-key", "label": "Old guide"}])
        page.wait_for_function("() => settings.tab === 'guides'")
        check("a retired guide shows one calm line, focused", page.evaluate("() => { const m = document.getElementById('guides-missing'); return !!m && m.textContent === 'That guide could not be found.' && document.activeElement === m; }"))
        home(page)
        jump(page, [{"type": "colour-lab", "key": "wheel:retired", "label": "Colour Lab: Old"}])
        page.wait_for_function("() => document.querySelector('.toast, #toast') && /could not be found/.test(document.body.innerText)")
        check("a retired colour shows one line and stays where it was", where(page)["tab"] == "dashboard" and not where(page)["win"])
        page.evaluate("() => { mentorMessages.length = 0; }")

        # --- Back after a jump goes where Back goes everywhere else (to the Dashboard), not out of the app ---
        jump(page, [{"type": "guide", "key": "thin-paint", "label": "x"}])
        page.wait_for_function("() => settings.tab === 'guides'")
        page.evaluate("() => history.length")
        page.wait_for_function("() => history.state && history.state.minifolio === 'back'")
        page.go_back()
        page.wait_for_function("() => settings.tab === 'dashboard'")
        check("Back after a source jump goes to the Dashboard and keeps the app open", page.evaluate("() => document.body.innerText.includes('Minifolio')"))

        # --- reduced motion: no move layers or windows left behind ---
        page.evaluate("() => { mentorMessages.length = 0; }")
        page.emulate_media(reduced_motion="reduce")
        jump(page, [{"type": "guide", "key": "thin-paint", "label": "x"}])
        page.wait_for_function("() => settings.tab === 'guides'")
        check("reduce motion: the jump is instant and nothing is left over", page.evaluate("() => !document.querySelector('.mentor-backdrop') && !document.querySelector('.mo-out')"))

        check("no page errors or pop-ups", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
