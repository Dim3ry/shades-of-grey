"""MW2 tests for Minifolio: Mentor's starter questions sit inside one Suggestions pill (James, 3 Nov). New behaviour only:
1. The opening view shows one closed Suggestions pill (a button with aria-expanded) and no starter chips.
2. Opening it shows Paint Picker and the starter questions as plain rows (44 px buttons); focus goes to the first row. It unrolls
   (clip-path) while what moves glides by transform, on the motion tokens; the text box stays where it is.
3. Tapping it again rolls the list up and focus stays on the pill. A row asks its question and the list closes.
4. After an answer there is one closed pill, under the latest answer. After an "I do not know" answer its suggestions still show, and the
   pill holds the rest. Paint Picker goes to Colour Lab.
5. Escape closes the list first, then the window. Back returns to the start view with the pill focused.
6. 360x640 and 320x568 in three themes: with the list open the window fits above the bar and nothing sits over a button.
7. Reduce motion: the list opens at once, with no animation.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def rect(page, sel):
    return page.evaluate("(s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }", sel)

MOVES = "() => document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName && !a.transitionProperty)"
# (a finished animation's finish event comes with the next frame, so this waits for that frame)
FINISH = """async () => { document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName && !a.transitionProperty).forEach(a => a.finish());
  await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))); }"""
# Taps the pill and reads the fold's animations in the same step (so a busy machine cannot let them finish first)
TOGGLE = """() => { document.querySelector('.mentor-suggest').click();
  const own = document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName && !a.transitionProperty);
  return own.map(a => ({ el: a.effect.target.className && a.effect.target.className.baseVal === undefined ? a.effect.target.className : 'svg',
    ms: a.effect.getTiming().duration, easing: a.effect.getTiming().easing,
    frames: a.effect.getKeyframes().map(k => { const o = {}; for (const p of Object.keys(k)) if (!['offset', 'easing', 'composite', 'computedOffset'].includes(p)) o[p] = k[p]; return o; }) })); }"""
STATE = """() => { const p = document.querySelector('.mentor-suggest'), l = document.getElementById(p.getAttribute('aria-controls'));
  return { pills: document.querySelectorAll('.mentor-suggest').length, expanded: p.getAttribute('aria-expanded'), tag: p.tagName, text: p.textContent.trim(),
           shown: !!l && !l.hidden && l.getClientRects().length > 0, focus: document.activeElement.className, focusText: document.activeElement.textContent }; }"""
ROWS = "() => [...document.querySelectorAll('.mentor-rows .mentor-row')].map(r => r.textContent)"
# every visible button or box in the window that another one overlaps (inside the conversation only the part that shows counts)
OVER = """() => { const seen = [...document.querySelectorAll('.mentor-window button, .mentor-window input')].filter(b => b.getClientRects().length).map(b => {
    const r = b.getBoundingClientRect(), c = (b.closest('.mentor-scroll') || b.closest('.mentor-window')).getBoundingClientRect();
    return { n: b.className, l: r.left, r: r.right, t: Math.max(r.top, c.top), b: Math.min(r.bottom, c.bottom) }; }).filter(x => x.b - x.t > 1);
  const out = []; for (let i = 0; i < seen.length; i++) for (let j = i + 1; j < seen.length; j++) { const a = seen[i], b = seen[j];
    if (a.l < b.r - 0.5 && b.l < a.r - 0.5 && a.t < b.b - 0.5 && b.t < a.b - 0.5) out.push(a.n + ' / ' + b.n); } return out; }"""

def open_window(page):
    page.click("#mentor-button")
    page.wait_for_function("() => { const w = document.querySelector('.mentor-window'); return w && w.getAnimations().length === 0; }")

def ask(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(page)
        t.main_tab(page, "dashboard")
        starters = page.evaluate("() => knowledgeIndex().list({ kind: 'starter' }).map(e => e.title)")

        print("--- 1. The opening view ---")
        open_window(page)
        st = page.evaluate(STATE)
        check("one closed Suggestions pill, a button with aria-expanded", st["pills"] == 1 and st["tag"] == "BUTTON" and st["text"] == "Suggestions"
              and st["expanded"] == "false" and not st["shown"], st)
        check("no starter chips on the opening view", page.locator(".mentor-window .mentor-chip").count() == 0)
        pill, g, form = rect(page, ".mentor-suggest"), rect(page, ".mentor-greeting"), rect(page, ".mentor-form")
        check("the pill sits under the greeting, above the box, 44 px high", g[3] <= pill[1] + 0.5 and pill[3] <= form[1] and pill[3] - pill[1] >= 44, (g, pill, form))

        print("\n--- 2. Opening the list ---")
        moves = page.evaluate(TOGGLE)
        props = {k for m in moves for f in m["frames"] for k in f}
        lst = [m for m in moves if m["el"] == "mentor-rows"]
        check("the list unrolls from the top (clip-path), moving with the pill", len(lst) == 1 and lst[0]["frames"][0]["clipPath"].startswith("inset(0px 0px 100%")
              and lst[0]["frames"][-1]["clipPath"] in ("inset(0px)", "inset(0px 0px 0px 0px)"), lst)
        check("only transform and clip-path move, on the --motion-med time", props <= {"transform", "clipPath"} and moves and all(m["ms"] == 240 for m in moves), (props, [m["ms"] for m in moves]))
        glide = [m for m in moves if m["el"] in ("mentor-orbbox ml-live", "mentor-greeting", "mentor-suggest", "mentor-close")]
        check("the window grows upward: the orb, greeting, pill and Close glide up into place by transform",
              len(glide) == 4 and all(m["frames"][0]["transform"].startswith("translateY(") and m["frames"][-1]["transform"] == "translateY(0px)" for m in glide), glide)
        page.evaluate(FINISH)
        st = page.evaluate(STATE)
        rows = page.evaluate(ROWS)
        check("open: aria-expanded is true and the list shows", st["expanded"] == "true" and st["shown"], st)
        check("Paint Picker is the first row, then every starter question", rows[0] == "Paint Picker" and rows[1:] == starters, rows)
        sizes = page.evaluate("() => [...document.querySelectorAll('.mentor-rows .mentor-row')].map(r => [r.tagName, r.getBoundingClientRect().height, r.getBoundingClientRect().width])")
        win = rect(page, ".mentor-window")
        check("rows are buttons, 44 px or more, the window's width", all(tag == "BUTTON" and h >= 44 and w >= win[2] - win[0] - 40 for tag, h, w in sizes), sizes[:3])
        short = page.evaluate("() => [...document.querySelectorAll('.mentor-row')].filter(r => r.textContent.length < 30).map(r => r.getBoundingClientRect().height)")
        check("a short question is one line", short and max(short) <= 46, short)
        check("focus goes to the first row", st["focusText"] == "Paint Picker", st)
        check("the text box stays where it is", rect(page, ".mentor-form") == form, (rect(page, ".mentor-form"), form))
        check("once open nothing is left clipped or moved", page.evaluate("() => [...document.querySelectorAll('.mentor-window, .mentor-window *')].every(e => { const c = getComputedStyle(e); return c.clipPath === 'none' && (c.transform === 'none' || e.closest('svg')); })"))

        print("\n--- 3. Closing, and asking a row ---")
        page.focus(".mentor-suggest")
        back = page.evaluate(TOGGLE)
        lst = [m for m in back if m["el"] == "mentor-rows"]
        check("tapping the pill again rolls the list up (the same frames backwards)", len(lst) == 1 and lst[0]["frames"][-1]["clipPath"].startswith("inset(0px 0px 100%")
              and page.evaluate(STATE)["expanded"] == "false", lst)
        page.evaluate(FINISH)
        st = page.evaluate(STATE)
        check("closed: the list is gone, focus stays on the pill, nothing left moved", not st["shown"] and st["focus"] == "mentor-suggest"
              and len(page.evaluate(MOVES)) == 0 and rect(page, ".mentor-form") == form, st)
        page.click(".mentor-suggest")
        page.evaluate(FINISH)
        question = page.evaluate(ROWS)[2]
        page.locator(".mentor-rows").get_by_text(question, exact=True).click()
        check("a row asks its question", page.locator(".mentor-me").last.inner_text() == question and page.locator(".mentor-reply").count() == 1)

        print("\n--- 4. After an answer ---")
        st = page.evaluate(STATE)
        check("one closed pill, and no starter chips", st["pills"] == 1 and st["expanded"] == "false" and not st["shown"] and page.locator(".mentor-window .mentor-chip").count() == 0, st)
        check("the pill sits under the latest answer", page.evaluate("() => { const r = [...document.querySelectorAll('.mentor-reply')].pop(); return r.compareDocumentPosition(document.querySelector('.mentor-suggest')) & Node.DOCUMENT_POSITION_FOLLOWING; }") > 0)
        check("it holds the starters not yet asked", page.evaluate(ROWS) == ["Paint Picker"] + [s for s in starters if s != question], page.evaluate(ROWS))
        ask(page, "zzqx flibber")
        reply = page.locator(".mentor-reply").last
        sug = reply.locator(".mentor-chips-in .mentor-chip").evaluate_all("els => els.filter(e => e.getClientRects().length).map(e => e.textContent)")
        rows = page.evaluate(ROWS)
        check("I do not know: its suggested questions still show under the line", reply.locator(".mentor-lead").inner_text() == "I do not know that yet." and len(sug) >= 2, sug)   # three, less any already asked
        check("and the pill holds the rest", page.locator(".mentor-suggest").count() == 1 and rows[0] == "Paint Picker"
              and sorted(rows[1:] + sug) == sorted(s for s in starters if s != question), (rows, sug))
        # the chat view: the list opens inside the conversation, which is scrolled so the rows show; the window itself does not move
        page.evaluate("() => document.activeElement.blur()")   # the box loses focus (typing moves the window to the bottom edge)
        page.wait_for_function("() => !document.body.classList.contains('typing')")
        win = rect(page, ".mentor-window")
        moves = page.evaluate(TOGGLE)
        page.evaluate(FINISH)
        first = rect(page, ".mentor-rows .mentor-row")
        sc = rect(page, ".mentor-scroll")
        check("chat view: the window keeps its size and the open rows are in view", rect(page, ".mentor-window") == win and not any(m["el"].startswith("mentor-window") for m in moves)
              and sc[1] <= first[1] and first[3] <= sc[3], (win, first, sc))

        print("\n--- 5. Escape, Back and Paint Picker ---")
        page.keyboard.press("Escape")
        page.evaluate(FINISH)
        st = page.evaluate(STATE)
        check("Escape closes the list first, focus back on the pill, the window stays", page.locator(".mentor-window").count() == 1 and not st["shown"]
              and st["expanded"] == "false" and st["focus"] == "mentor-suggest", st)
        page.click(".mentor-back")
        st = page.evaluate(STATE)
        check("Back: the start view, one closed pill, focused, all the starters back", page.locator(".mentor-msg").count() == 0 and st["pills"] == 1
              and st["expanded"] == "false" and st["focus"] == "mentor-suggest" and page.evaluate(ROWS) == ["Paint Picker"] + starters, st)
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")
        check("Escape with the list closed closes the window", page.locator(".mentor-window").count() == 0)
        open_window(page)
        page.click(".mentor-suggest")
        page.click(".mentor-row >> text=Paint Picker")
        page.wait_for_selector("#cmp-lab-picker")
        check("the Paint Picker row goes to Painting > Colour Lab > Paint Picker", page.evaluate("() => [settings.tab, settings.recipeView, compendiumState.lab].join()") == "recipes,colourlab,picker")

        print("\n--- 6. Small phones, themes ---")
        for (w, h, mode, theme) in ((360, 640, "light", "classic"), (360, 640, "dark", "forge"), (320, 568, "dark", "parchment"), (360, 640, "light", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("([th, m]) => { Object.assign(settings, { theme: th, appearance: m }); applyPalette(settings.palette); mentorClear(); showTab('dashboard'); }", [theme, mode])
            open_window(page)
            form = rect(page, ".mentor-form")
            page.click(".mentor-suggest"); page.evaluate(FINISH)
            win, bar = rect(page, ".mentor-window"), rect(page, ".tabs .arc")
            over = page.evaluate(OVER)
            check(f"{w}x{h} {mode} {theme}: list open, the window fits above the bar, the box stays put, nothing over a button, no sideways scroll",
                  win[1] >= 0 and win[3] <= bar[1] + 1 and rect(page, ".mentor-form") == form and over == []
                  and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"), (win, bar, over))
            seen = page.wait_for_function("""() => { const s = document.querySelector('.mentor-scroll').getBoundingClientRect(), p = document.querySelector('.mentor-suggest').getBoundingClientRect();
                const n = [...document.querySelectorAll('.mentor-row')].filter(r => { const b = r.getBoundingClientRect(); return b.top >= s.top - 0.5 && b.bottom <= s.bottom + 0.5; }).length;
                return p.top >= s.top - 0.5 && n >= 2 ? n : false; }""", timeout=3000).json_value()
            check(f"{w}x{h} {theme}: the pill and at least two whole rows show (the greeting scrolls away if it must)", seen >= 2, seen)
            page.keyboard.press("Escape"); page.keyboard.press("Escape")
            page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")

        print("\n--- 7. Reduce motion ---")
        page.set_viewport_size({"width": 390, "height": 844})
        page.emulate_media(reduced_motion="reduce")
        page.evaluate("() => mentorClear()")
        page.click("#mentor-button")
        page.wait_for_selector(".mentor-window")
        moves = page.evaluate(TOGGLE)
        st = page.evaluate(STATE)
        check("reduce motion: the list opens at once, with no animation", moves == [] and st["shown"] and st["expanded"] == "true", (moves, st))
        back = page.evaluate(TOGGLE)
        check("reduce motion: and closes at once", back == [] and not page.evaluate(STATE)["shown"], back)
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
