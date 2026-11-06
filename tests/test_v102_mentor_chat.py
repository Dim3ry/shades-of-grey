"""X6b tests for Minifolio (typing, chips and answers in the Mentor window). New behaviour only:
1. Typing: Send and Enter, empty and long input, the box keeps focus, a typed tag shows as plain text.
2. Answers: lead, paint rows with their actions, Sources buttons, a no-answer line with chips, starter chips that drop out once used.
3. Source buttons open the guide or Colour Lab; the conversation survives closing; the 30 message cap.
4. Nothing stored or sent while talking; the notice and the status line for screen readers.
5. Sizes: 360 and 390 px, dark and light, a short screen, wide screens, reduced motion.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

HERE = os.path.dirname(os.path.abspath(__file__))
results = []

# Test-only sample entries, so the chips and a guide source have something to show (the real library is filled by X8).
SAMPLE = """const GUIDE_ENTRIES = [{ key: "thin-paint", category: "techniques", title: "Thinning paint", summary: "Thin paint with a little water so it flows.",
  body: ["Add water a drop at a time."], related: [], keywords: ["thin paint", "thinning", "water"] }];
const GUIDE_STARTERS = [{ key: "s-thin", text: "How do I thin paint?", targets: ["thin-paint"] },
  { key: "s-water", text: "Why add water?", targets: ["thin-paint"] }];"""

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")   # grown to full size

def closed(page):
    page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
    return True

def send_typed(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

def count(page, sel):
    return page.locator(sel).count()

def rect(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom, r.width, r.height]; }", sel)

def main():
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        ctx.route("**/guides-data.js*", lambda route: route.fulfill(body=SAMPLE, content_type="text/javascript"))
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.on("request", lambda r: requests.append(r.url) if not r.url.startswith(("http://localhost", "http://127.0.0.1", "data:", "blob:")) else None)

        t.fresh(page)
        page.evaluate("""() => { window.__sets = 0; const set = Storage.prototype.setItem;
            Storage.prototype.setItem = function (...a) { window.__sets++; return set.apply(this, a); }; }""")
        open_it(page)
        page.wait_for_function("() => mentorWarm === true")

        print("\n--- 1. Typing ---")
        inp = page.locator(".mentor-input")
        check("the box is a real labelled input and Send is a button of 44 px or more",
              inp.is_enabled() and inp.get_attribute("aria-label") == "Ask Mentor" and rect(page, ".mentor-send")[4] >= 44 and rect(page, ".mentor-send")[5] >= 44)
        page.fill(".mentor-input", "armour blue")
        page.click(".mentor-send")
        check("Send shows the question as a bubble and an answer under it", page.locator(".mentor-me").first.inner_text() == "armour blue" and count(page, ".mentor-reply .mentor-lead") == 1)
        check("the box is emptied and keeps focus", inp.input_value() == "" and page.evaluate("() => document.activeElement.className") == "mentor-input")
        send_typed(page, "how do I thin paint")
        check("Enter sends too", count(page, ".mentor-me") == 2 and "Thinning paint" in page.locator(".mentor-reply").nth(1).inner_text())
        before = count(page, ".mentor-msg")
        send_typed(page, "")
        page.fill(".mentor-input", "   ")
        page.keyboard.press("Enter")
        check("empty and spaces-only messages do nothing", count(page, ".mentor-msg") == before)
        check("the box stops typing at 300 characters", (page.fill(".mentor-input", "x" * 400), len(inp.input_value()))[1] == 300)
        page.evaluate("() => { document.querySelector('.mentor-input').value = 'y'.repeat(450); }")
        page.keyboard.press("Enter")
        check("a longer message is cut at 300 with no error", len(page.locator(".mentor-me").last.inner_text()) == 300 and not errors, errors)
        send_typed(page, "<b>test</b>")
        bubble = page.locator(".mentor-me").last
        check("a typed tag shows as plain text, no HTML made", bubble.inner_text() == "<b>test</b>" and bubble.locator("b").count() == 0)

        print("\n--- 2. Answers ---")
        reply = page.locator(".mentor-reply").first
        rows = reply.locator(".idea-list > li")
        check("a colour and a part give the Paint Picker's own rows", rows.count() >= 1 and reply.locator(".idea-name").count() >= 1)
        check("the rows carry their actions (shopping list for a paint you do not have)", reply.get_by_role("button", name="Add to shopping list").count() >= 1)
        srcs = reply.locator(".mentor-source")
        # v136 (AT-12): the "Sources" label is gone; the sources are plain links, still 44 px rows
        check("a row of source links follows, 44 px or more, with no Sources label", reply.locator(".mentor-sources-label").count() == 0 and srcs.count() >= 1
              and all(h >= 44 for h in srcs.evaluate_all("els => els.map(e => e.getBoundingClientRect().height)")))
        check("a source button has a clear name", (srcs.first.get_attribute("aria-label") or "").startswith("Open ") and srcs.first.inner_text().strip() in srcs.first.get_attribute("aria-label"))
        send_typed(page, "zzqx qwerty")
        none = page.locator(".mentor-reply").nth(count(page, ".mentor-reply") - 1)
        # E: the no-answer line is now "I do not know that yet." (was "I could not find that yet."), so the two wording checks here follow it
        check("no answer: one short line, no sources", none.locator(".mentor-lead").inner_text() == "I do not know that yet." and none.locator(".mentor-source").count() == 0)
        sug = none.locator(".mentor-chips-in .mentor-chip")
        check("no answer: the suggestions are chips", sug.count() >= 1, sug.count())
        status = page.locator(".mentor-window [role=status]")
        check("the answer is announced politely", status.get_attribute("aria-live") == "polite" and status.inner_text() == "I do not know that yet.")
        # MW2 (v129): the starter questions are no longer a strip of chips under the conversation (redrawn after every answer); they are rows
        # inside one closed Suggestions pill under the latest answer, Paint Picker first, and after a no-answer reply the pill leaves out the
        # questions that reply already shows. So these checks open the pill and read its rows (they read the chip strip before), and the A1
        # check that the strip wraps became a check that the rows never run sideways.
        sug_texts = sug.evaluate_all("els => els.map(e => e.textContent)")
        page.locator(".mentor-suggest").click()
        top_rows = page.locator(".mentor-rows .mentor-row").evaluate_all("els => els.map(e => e.textContent)")
        check("the starter questions sit after Paint Picker in the pill, leaving out the ones the no-answer reply shows",
              top_rows[0] == "Paint Picker" and not set(top_rows[1:]) & set(sug_texts) and {"Why add water?", "How do I thin paint?"} <= set(top_rows[1:]) | set(sug_texts), (top_rows, sug_texts))
        check("the rows never run sideways", page.evaluate(
            "() => { const s = document.querySelector('.mentor-scroll'), r = s.getBoundingClientRect(); return s.scrollWidth <= s.clientWidth && [...document.querySelectorAll('.mentor-row')].every(x => x.getBoundingClientRect().right <= r.right + 0.5); }"))
        water = "Why add water?"   # a row in the pill, or (when the no-answer reply already shows it) that reply's chip
        (page.locator(".mentor-rows") if water in top_rows else none).get_by_text(water, exact=True).click()
        check("a starter question sends itself as if typed", page.locator(".mentor-me").last.inner_text() == water and count(page, ".mentor-reply .mentor-source") >= 2, water)
        again = page.locator(".mentor-chip, .mentor-row").evaluate_all("els => els.map(e => e.textContent)")
        check("a used chip drops out of every row, and focus stays inside the window", water not in again and page.evaluate("() => !!document.activeElement.closest('.mentor-window')"), again)
        none.locator(".mentor-chip").first.click()
        check("a suggestion chip in a no-answer message works too and goes", page.locator(".mentor-me").last.inner_text() == "How do I thin paint?"
              and "How do I thin paint?" not in page.locator(".mentor-chip, .mentor-row").evaluate_all("els => els.map(e => e.textContent)"))   # MW2: and from the pill's rows

        print("\n--- 3. Sources, memory, cap ---")
        n = count(page, ".mentor-msg")
        page.locator(".mentor-reply").last.locator(".mentor-source").first.click()
        closed(page)
        check("a guide source closes the window and opens that Guides entry", page.evaluate("() => settings.tab === 'guides' && guidesState.key === 'thin-paint'"))
        open_it(page)
        check("reopening shows the same conversation", count(page, ".mentor-msg") == n and page.locator(".mentor-window").evaluate("e => e.classList.contains('mentor-chatting')"))
        colour_src = page.locator(".mentor-reply").first.locator(".mentor-source").first
        check("a colour source has a swatch and says Colour Lab", "Colour Lab" in colour_src.inner_text() and colour_src.locator(".swatch").count() == 1)
        colour_src.click()
        closed(page)
        check("a colour source opens Colour Lab", page.evaluate("() => settings.tab === 'recipes' && settings.recipeView === 'colourlab'"))
        open_it(page)
        page.locator(".mentor-reply").first.get_by_role("button", name="Add to shopping list").first.click()
        check("a row's action works inside the window, which stays open, with its own answer in place",
              page.locator(".mentor-reply").first.locator(".shop-onlist").count() >= 1 and count(page, ".mentor-window") == 1)
        page.evaluate("() => showToast('Test notice')")
        tr = rect(page, "#toast")
        hit = page.evaluate("""(t) => [...document.querySelectorAll('.mentor-window button, .mentor-window input')].some(b => { const r = b.getBoundingClientRect();
            return r.width && r.left < t[2] && r.right > t[0] && r.top < t[3] && r.bottom > t[1]; })""", tr)
        check("a notice shows above the window and never over a button in it", not hit and page.evaluate("() => +getComputedStyle(document.getElementById('toast')).zIndex") > 200, tr)
        page.evaluate("() => { for (let i = 0; i < 17; i++) mentorSend('thin paint'); }")
        check("the conversation is capped at the last 30 messages", page.evaluate("() => mentorMessages.length") == 30 and count(page, ".mentor-msg") == 30)
        page.locator(".mentor-reply").last.locator(".mentor-source").first.click()
        closed(page)
        page.evaluate("() => { showTab('dashboard'); }")
        open_it(page)
        pick_reply = [i for i in range(count(page, ".mentor-reply")) if page.locator(".mentor-reply").nth(i).locator(".idea-list").count()]
        check("older rows are gone with the cap (the colour answer scrolled out), newer stay", pick_reply == [], pick_reply)
        send_typed(page, "teal weapon")
        page.locator(".mentor-reply").last.get_by_role("button", name="Use in a recipe").first.click()
        closed(page)
        check("Use in a recipe leaves the window first, then starts the recipe", page.evaluate("() => settings.tab === 'recipes' && !!recipeDraft"))

        print("\n--- 4. Nothing stored or sent while talking ---")
        # MW1 (v127): the window now takes 240 ms to close (was 120), so the recipe draft that Use in a recipe started (written 300 ms after
        # the last tap) could land after the count was reset. It is written now, before counting; it is not a message.
        page.evaluate("() => { showTab('dashboard'); syncDrafts(); window.__sets = 0; }")
        open_it(page)
        send_typed(page, "what goes with red")
        send_typed(page, "zzqx qwerty")
        page.locator(".mentor-suggest").hover()   # MW2 (v129): the Suggestions pill (Paint Picker is inside it now)
        check("sending messages writes nothing to storage", page.evaluate("() => window.__sets") == 0)
        check("no network use, no pop-ups, no page errors", not requests and not errors, (requests, errors))
        page.keyboard.press("Escape"); closed(page)

        print("\n--- 5. Sizes, themes, wide screens, motion ---")
        for w, h, dark in ((390, 844, True), (360, 740, True), (360, 740, False), (390, 844, False)):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(d) => { document.documentElement.setAttribute('data-appearance', d ? 'dark' : 'light'); }", dark)
            open_it(page)
            r = rect(page, ".mentor-window")
            fits = r[0] >= 0 and r[2] <= w and r[1] >= 0 and r[3] <= h
            flat = page.evaluate("() => document.documentElement.scrollWidth <= innerWidth && (w => w.scrollWidth <= w.clientWidth)(document.querySelector('.mentor-window'))")
            small = page.evaluate("""() => [...document.querySelectorAll('.mentor-window button, .mentor-window input')].filter(b => b.getClientRects().length && !b.closest('.idea-list') && !b.closest('.shop-add-row'))
                .filter(b => { const r = b.getBoundingClientRect(); return r.height < 44 || r.width < 44; }).map(b => b.className)""")
            flat_tx = page.evaluate("() => [...document.querySelectorAll('.mentor-send, .mentor-chip, .mentor-source, .mentor-suggest, .mentor-row')].every(b => getComputedStyle(b).transform === 'none')")
            check(f"{w}x{h} {'dark' if dark else 'light'}: window on screen, no sideways scroll, taps 44 px+, no resting transform", fits and flat and not small and flat_tx, (r, flat, small, flat_tx))
            page.keyboard.press("Escape"); closed(page)
        page.evaluate("() => document.documentElement.removeAttribute('data-appearance')")
        page.set_viewport_size({"width": 390, "height": 420})
        open_it(page)
        send_typed(page, "thin paint")
        sr, ir, wr = rect(page, ".mentor-send"), rect(page, ".mentor-input"), rect(page, ".mentor-window")
        check("a short screen (390x420): the box and Send stay in view", sr[3] <= 420 and ir[3] <= 420 and wr[1] >= 0, (sr, ir, wr))
        page.focus(".mentor-input")
        check("while typing the menu bar hides and the window drops to the bottom edge", page.evaluate("() => document.body.classList.contains('typing')")
              and page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.mentor-backdrop')).paddingBottom)") <= 12)
        page.keyboard.press("Escape"); closed(page)
        page.set_viewport_size({"width": 1280, "height": 800})
        open_it(page)
        send_typed(page, "armour red")
        r = rect(page, ".mentor-window")
        check("1280 px: still the small window, answer shown, Send in view", r[4] <= 380 and r[3] <= 800 and rect(page, ".mentor-send")[3] <= 800 and page.locator(".mentor-reply").last.locator(".idea-list").count() == 1, r)
        page.keyboard.press("Escape"); closed(page)
        page.emulate_media(reduced_motion="reduce")
        open_it(page)
        send_typed(page, "thin paint")
        check("reduce motion: a new message has no animation", page.evaluate("() => getComputedStyle(document.querySelector('.mentor-msg:last-child')).animationName") == "none")
        page.keyboard.press("Escape"); closed(page)
        check("no page errors or pop-ups at the end", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
