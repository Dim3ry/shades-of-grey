"""X5 tests for Minifolio (the Mentor pop-up window). New behaviour only:
1. The round button opens a window (on the start circle and from each main section); greeting from the list; text box switched off; chip text.
2. Dialog: focus goes in and stays in, X / scrim / Escape / Back close it and focus returns to the button; the page behind does not scroll.
3. The Paint Picker chip closes it and lands on Painting > Colour Lab > Paint Picker.
4. Motion: opens out of the button (MW1), idle movement only while open (U6b: the look's own motion, no lens wake); reduced motion has none.
5. Nothing stored or sent. 360 and 390 px, dark and light, wide screen: inside the screen, taps 44 px or more.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t
from launch_helpers import quiet

results = []
# U6b (v126): James's script has eight greetings (the first three are these), so the list grew
GREETINGS = ["How can I help?", "What are you painting?", "Ready when you are.", "What's on the bench today?", "What would you like to know?",
             "Ask me about paints or techniques.", "Tell me what you are working on.", "Pick a question or type your own."]

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def is_open(page):
    return page.locator(".mentor-window").count() == 1

def closed(page):
    page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
    return True

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")

def box(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)

def main():
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("http://localhost", "http://127.0.0.1", "data:", "blob:")) else None)
        # X8: the knowledge base's 20 starter questions show as chips after Paint Picker; this test is about the window, so it uses empty guide lists (starter chips are tested in test_v102)
        ctx.route("**/guides-data.js*", lambda route: route.fulfill(body="const GUIDE_ENTRIES = [];\nconst GUIDE_STARTERS = [];\n", content_type="text/javascript"))

        print("\n--- 1. Opening ---")
        t.fresh(page)
        page.evaluate("() => document.getElementById('home-button').click()")
        page.wait_for_function("() => document.body.classList.contains('launching')")
        open_it(page)
        check("opens over the start circle, which stays", is_open(page) and page.evaluate("() => document.body.classList.contains('launching')"))
        page.keyboard.press("Escape"); closed(page)
        seen = set()
        for tab in ("dashboard", "units", "recipes", "guides"):
            t.main_tab(page, tab)
            open_it(page)
            seen.add(page.inner_text(".mentor-greeting"))
            check(f"opens from {tab}, and the section behind is unchanged", is_open(page) and page.evaluate("(n) => settings.tab === n", tab), tab)
            page.keyboard.press("Escape"); closed(page)
        check("greeting always comes from the list", seen <= set(GREETINGS), seen)
        picks = set()
        for _ in range(12):
            open_it(page); picks.add(page.inner_text(".mentor-greeting")); page.keyboard.press("Escape"); closed(page)
        check("greeting varies between opens", len(picks) > 1 and picks <= set(GREETINGS), picks)
        open_it(page)
        check("window is named Mentor, modal, with a close X", page.get_attribute(".mentor-window", "role") == "dialog"
              and page.get_attribute(".mentor-window", "aria-modal") == "true" and page.get_attribute(".mentor-window", "aria-label") == "Mentor"
              and page.get_attribute(".mentor-close", "aria-label") == "Close Mentor")
        # X6b: typing is on, so the box is a working input and there is a Send button (an arrow with no words), still only the one chip
        check("one chip, Paint Picker; no other chips (and the Send button)", page.locator(".mentor-window button").evaluate_all("els => els.filter(e => e.getClientRects().length).map(e => e.textContent.trim() || e.getAttribute('aria-label'))") == ["Paint Picker", "Send", "✕"])   # chunk D: the hidden Back button (chat view only) is not counted
        inp = page.locator(".mentor-input")
        check("text box is on: enabled, Ask Mentor, full strength", inp.is_enabled() and inp.get_attribute("placeholder") == "Ask Mentor"
              and float(page.evaluate("() => getComputedStyle(document.querySelector('.mentor-input')).opacity")) == 1)
        # U6b (v126): the lists are filled from James's script now (it was two picker lines and empty thinking, answer and finished lists)
        check("phrases object holds the lists", page.evaluate(
            "() => MENTOR_TYPING === true && ['greeting','picker','thinking','answer','unsure','finished','actions'].every(k => Array.isArray(MENTOR_PHRASES[k])) && mentorMessages.length === 0"))
        check("no 'the Mentor' in the window", "the Mentor" not in page.inner_text(".mentor-window"))

        print("\n--- 2. Dialog behaviour ---")
        check("focus moved into the window", page.evaluate("() => !!document.activeElement.closest('.mentor-window')"))
        seq = []
        for _ in range(4):
            page.keyboard.press("Tab"); seq.append(page.evaluate("() => document.activeElement.className"))
        # X6b: the box and Send are now tab stops too
        check("Tab stays inside (chip, box, Send and X)", set(seq) == {"mentor-chip", "mentor-input", "mentor-send", "mentor-close"}, seq)
        page.keyboard.press("Shift+Tab")
        check("Shift+Tab stays inside too", page.evaluate("() => !!document.activeElement.closest('.mentor-window')"))
        check("page behind does not scroll", page.evaluate("() => document.body.style.overflow") == "hidden")
        page.click(".mentor-close"); closed(page)
        check("X closes it, focus returns to the Mentor button, scroll is back", page.evaluate("() => document.activeElement.id") == "mentor-button"
              and page.evaluate("() => document.body.style.overflow") == "")
        open_it(page); page.keyboard.press("Escape"); closed(page)
        check("Escape closes it and returns focus", page.evaluate("() => document.activeElement.id") == "mentor-button")
        open_it(page); page.mouse.click(195, 60); closed(page)
        check("a tap on the dimmed area closes it", not is_open(page))
        open_it(page); page.click(".mentor-window .mentor-greeting")
        check("a tap inside the window does not close it", is_open(page))
        page.keyboard.press("Escape"); closed(page)
        open_it(page)
        page.evaluate("() => history.back()")   # the phone's Back button
        closed(page)
        check("Back closes it and stays in the same section", page.evaluate("() => settings.tab") == "guides")

        print("\n--- 3. Paint Picker chip ---")
        t.main_tab(page, "dashboard")
        open_it(page); page.click(".mentor-chip"); page.wait_for_selector("#cmp-lab-picker")
        closed(page)
        check("lands on Painting > Colour Lab > Paint Picker", page.evaluate("() => [settings.tab, settings.recipeView, compendiumState.lab].join()") == "recipes,colourlab,picker"
              and page.get_attribute('#lab-seg [data-lab="picker"]', "aria-selected") == "true" and page.inner_text('#lab-seg [data-lab="picker"]') == "Paint Picker")
        check("the section works without the window (Paint Picker has its base box)", page.locator("#cmp-mentor-base").count() == 1)

        print("\n--- 4. Motion ---")
        t.main_tab(page, "dashboard")
        page.click("#mentor-button")
        # MW1 (v127): the X5 grow from the button's centre (mp-grow, --mp-ox/--mp-oy, 240 ms) became the round button's circle opening out into
        # the window (app.js plays it: a clip-path and a translate, 320 ms); test_v127_mw1 checks where it starts and ends.
        info = page.evaluate("""() => { const w = document.querySelector('.mentor-window');
            const anims = w.getAnimations({subtree: true}).map(a => [a.animationName || null, a.effect.getTiming().duration, a.effect.getTiming().delay]);
            const own = w.getAnimations().map(a => [a.effect.getTiming().duration, a.effect.getKeyframes().map(k => k.clipPath)]);
            return { anims, own }; }""")
        names = {a[0]: a for a in info["anims"]}
        # v129 (MO6, James 3 Nov evening: "much slower so it feels fluid"): the move now takes --motion-flow, 800 ms (it was 320 ms)
        check("opens out of the button: the window's own move is an 800 ms clip-path (no mp-grow)", "mp-grow" not in names
              and len(info["own"]) == 1 and info["own"][0][0] == 800 and str(info["own"][0][1][0]).startswith("inset("), info)
        # U6b (v126): the window's orb is the chosen look (Futuristic here), so the old lens orb's wake, glance and 40 s ring turn are gone;
        # the whole-orb float stays, and the look's own motion runs (Thinking's slow 14 s turn while Mentor gets ready, then the 6 s glow)
        # U7 (round 7's drawings): the look's own motion has new names and timings (a 6.5 s bob, a blink, and so on), so this checks that some
        # slow motion of the look's own (an ml- animation of 3 s or longer) runs, not one named animation. U7 also took away the app's own 4 s float
        # (mp-float): every round 7 look brings its own bob, and the two were stacked (the parent's decision), so the check is now that it is gone.
        check("idle: the look's own slow motion, and no second float on top of it", "mp-float" not in names
              and any(k and k.startswith("ml-") and v[1] >= 3000 for k, v in names.items()), names)
        check("the orb is the Futuristic look, in its own box", page.locator(".mentor-window .mentor-orbbox.ml-live svg.ml-futuristic").count() == 1)
        page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().length === 0")   # MW1: opened in full first
        # T6: the close animation is read as soon as Escape has been handled (on a busy machine a read made afterwards could miss it);
        # if the move starts a moment later, it is read straight after the key press instead.
        page.evaluate("""() => { window.__closing = null; document.addEventListener('keydown', () => setTimeout(() => { const w = document.querySelector('.mentor-window');
            window.__closing = w ? w.getAnimations().map(a => [a.effect.getTiming().duration, a.effect.getTiming().direction]) : null; }, 0), { capture: true, once: true }); }""")
        page.keyboard.press("Escape")
        closing = page.evaluate("() => window.__closing") or page.evaluate("() => { const w = document.querySelector('.mentor-window'); return w ? w.getAnimations().map(a => [a.effect.getTiming().duration, a.effect.getTiming().direction]) : null; }")
        # MW1 (v127): closing is the same move backwards into the button, 240 ms (X5 shrank it with mp-grow in reverse in 120 ms)
        # v129 (MO6): closing is two thirds of the open, 533 ms (it was 240 ms)
        check("close is the same move in reverse, 533 ms", closing and [533, "reverse"] in closing, closing)
        closed(page)
        check("nothing keeps running once closed", page.evaluate("() => document.getAnimations().filter(a => String(a.animationName || '').startsWith('mp-')).length") == 0)
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = rm.new_page(); rp.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(rp)
        rp.click("#mentor-button"); rp.wait_for_selector(".mentor-window")
        check("reduce motion: no animation at all while open", rp.evaluate("() => document.querySelector('.mentor-window').getAnimations({subtree: true}).length") == 0)
        rp.keyboard.press("Escape")
        check("reduce motion: it is gone at once", rp.locator(".mentor-backdrop").count() == 0)
        rm.close()

        print("\n--- 5. Nothing stored or sent ---")
        before = page.evaluate("() => JSON.stringify(Object.entries(localStorage))")
        open_it(page); page.keyboard.press("Escape"); closed(page)
        check("opening and closing writes no storage", page.evaluate("() => JSON.stringify(Object.entries(localStorage))") == before)
        check("no network use", not requests, requests)

        print("\n--- 6. Sizes, themes, wide screens ---")
        for width, height, scheme in ((390, 844, "dark"), (360, 640, "light"), (390, 844, "light"), (1280, 800, "dark")):
            c2 = browser.new_context(viewport={"width": width, "height": height}, service_workers="block", color_scheme=scheme)
            pg = c2.new_page(); pg.on("pageerror", lambda x: errors.append(str(x)))
            t.fresh(pg)
            open_it(pg); quiet(pg)
            w, c, x, ch = box(pg, ".mentor-window"), box(pg, ".mentor-chip"), box(pg, ".mentor-close"), box(pg, ".mentor-input")
            bar = box(pg, ".tabs .arc")
            ok_in = w[0] >= 0 and w[0] + w[2] <= width and w[1] >= 0 and w[1] + w[3] <= bar[1] + bar[3]
            check(f"{width} px {scheme}: window inside the screen, above the bar, no wider than 380 px", ok_in and w[2] <= 380.5, w)
            check(f"{width} px {scheme}: close X and chip are 44 px or more, nothing runs past the window", min(c[2], c[3], x[2], x[3]) >= 44
                  and c[0] + c[2] <= w[0] + w[2] and ch[0] + ch[2] <= w[0] + w[2] and pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"), (c, x))
            if width == 1280:
                check("wide screen: window is centred", abs((w[0] + w[2] / 2) - width / 2) < 2, w)
            check(f"{width} px {scheme}: no resting transform on the X, chip or window", pg.evaluate(
                "() => ['.mentor-close', '.mentor-chip'].every(s => getComputedStyle(document.querySelector(s)).transform === 'none')"))
            c2.close()
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
