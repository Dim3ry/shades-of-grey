"""MW1 tests for Minifolio: Mentor opens out of its sphere, and the orb sits above the chat (James, 3 Nov). New behaviour only:
1. Opening: the round button's circle grows into the window. The move starts on the round button's box (a circle) and ends on the
   window's box; the button's colour covers it on the way and the words fade in only once the shape has arrived; the orb travels from
   the button's drawing to its place. The round button itself does not move or change.
2. Orb placement: centred above the greeting, the starter questions and the box (by boxes), and larger than before (68 px) on a phone.
   In the chat view it shrinks smoothly but stays above the conversation, centred between Back and Close.
3. 360x640: nothing overlaps a button or chip, the window fits above the bar, and Back and Close keep their places and sizes.
4. Closing: the same move backwards, ending on the round button's box; focus goes back to the button. Closed while still opening, it turns round.
5. Wide screen (1280): the same stacked layout and the same move.
6. Reduced motion: no growing, no travel and no clip; only a quick fade.
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

def near(a, b, tol=1.5):
    return a is not None and b is not None and all(abs(x - y) <= tol for x, y in zip(a, b))

def centre(r):
    return [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]

def closed(page):
    page.wait_for_function("() => !document.querySelector('.mentor-backdrop')")

def settled(page):
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations({ subtree: true }).every(a => a.animationName || a.playState !== 'running')")

# Pauses the window's move (the script animations, not the CSS idle motion) at a fraction of its length and returns what shows on screen:
# the visible box (the window's box with its translate, cut by its clip-path inset), the round of the clip, the orb's box, the skin and the words.
AT = """(f) => { const w = document.querySelector('.mentor-window');
  const moves = w.getAnimations({ subtree: true }).filter(a => !a.animationName && !a.transitionProperty);
  moves.forEach(a => { a.pause(); a.currentTime = f * a.effect.getTiming().duration; });
  const r = w.getBoundingClientRect(), cs = getComputedStyle(w);
  const m = /inset\\(([^)]*?)(?: round ([\\d.]+)px)?\\)/.exec(cs.clipPath);
  let box = [r.left, r.top, r.right, r.bottom], round = null;
  if (m) { const v = m[1].trim().split(/\\s+/).map(parseFloat); const [t, rt, b, l] = [v[0], v[1] ?? v[0], v[2] ?? v[0], v[3] ?? v[1] ?? v[0]];
    box = [r.left + l, r.top + t, r.right - rt, r.bottom - b]; round = m[2] ? parseFloat(m[2]) : 0; }
  const o = document.querySelector('.mentor-orbbox').getBoundingClientRect();
  return { n: moves.length, box, round, clip: cs.clipPath, orb: [o.left, o.top, o.right, o.bottom],
           skin: parseFloat(getComputedStyle(document.querySelector('.mp-skin')).opacity), words: parseFloat(getComputedStyle(document.querySelector('.mentor-col')).opacity) }; }"""
RESUME = "() => document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName).forEach(a => a.play())"
BUTTON = """() => { const b = document.getElementById('mentor-button'), r = b.getBoundingClientRect(), s = b.querySelector('svg').getBoundingClientRect();
  return { box: [r.left, r.top, r.right, r.bottom], svg: [s.left, s.top, s.right, s.bottom], look: b.querySelector('svg').getAttribute('class') }; }"""
# Every visible button, chip or box in the window that the orb's box overlaps (a row scrolled out of the conversation or the chip strip is cut by it, so only its shown part counts)
OVER = """() => { const o = document.querySelector('.mentor-orbbox').getBoundingClientRect();
  return [...document.querySelectorAll('.mentor-window button, .mentor-window input')].filter(b => { const r = b.getBoundingClientRect();
    const c = (b.closest('.mentor-scroll, .mentor-chips:not(.mentor-chips-in)') || b.closest('.mentor-window')).getBoundingClientRect();
    const top = Math.max(r.top, c.top), bottom = Math.min(r.bottom, c.bottom);
    return r.width && bottom > top && r.left < o.right && r.right > o.left && top < o.bottom && bottom > o.top; }).map(b => b.className); }"""
BORDER = "() => parseFloat(getComputedStyle(document.querySelector('.mentor-window')).borderTopWidth)"

# The moves are paused in the same step that starts them, so a busy test machine cannot let them finish before they are looked at.
PAUSE = "document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName && !a.transitionProperty).forEach(a => a.pause())"

def opened_paused(page):
    page.evaluate("() => { document.getElementById('mentor-button').click(); " + PAUSE + "; }")

def escape_paused(page):
    page.evaluate("() => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); " + PAUSE + "; }")

# Sends a question (or presses Back) and returns the first frame of the orb drawing's move, read in the same step.
ORB_MOVE = """(what) => { if (what === 'back') document.querySelector('.mentor-back').click();
  else { document.querySelector('.mentor-input').value = what; document.querySelector('.mentor-form').requestSubmit(); }
  return document.querySelector('.mentor-orbbox svg').getAnimations().filter(x => !x.animationName).map(x => x.effect.getKeyframes()[0].transform); }"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.fresh(page)
        t.main_tab(page, "dashboard")

        print("--- 1. Opening out of the round button ---")
        before = page.evaluate(BUTTON)
        opened_paused(page)
        props = page.evaluate("""() => { const moves = document.querySelector('.mentor-window').getAnimations({ subtree: true }).filter(a => !a.animationName);
            const props = new Set(); for (const a of moves) for (const k of a.effect.getKeyframes()) for (const p of Object.keys(k)) if (!['offset', 'easing', 'composite', 'computedOffset'].includes(p)) props.add(p);
            return { props: [...props], ms: moves.map(a => a.effect.getTiming().duration) }; }""")
        start = page.evaluate(AT, 0)
        bw = before["box"][2] - before["box"][0]
        check("the move starts on the round button's box, as a circle", start["n"] >= 4 and near(start["box"], before["box"]) and abs(start["round"] - bw / 2) < 1, (start, before))
        check("at the start the button's colour covers it and the words are hidden", start["skin"] == 1 and start["words"] == 0, start)
        orb_scale = page.evaluate("() => { const b = document.querySelector('#mentor-button svg'), o = document.querySelector('.mentor-orbbox svg'); return (b.getBoundingClientRect().width / b.viewBox.baseVal.width) / (o.getBoundingClientRect().width / o.viewBox.baseVal.width); }")
        check("the orb starts on the button's drawing, at the same drawing size", near(centre(start["orb"]), centre(before["svg"]), 2) and abs(orb_scale - 1) < 0.03, (start["orb"], before["svg"], orb_scale))
        mid = page.evaluate(AT, 0.35)
        check("half way the shape is between the button and the window, still covered, words still hidden",
              mid["box"][1] < start["box"][1] and mid["box"][3] - mid["box"][1] > bw and mid["skin"] == 1 and mid["words"] == 0, mid)
        arrived = page.evaluate(AT, 0.7)
        page.evaluate(RESUME)
        settled(page)
        win = rect(page, ".mentor-window")
        orb = rect(page, ".mentor-orbbox")
        check("the shape arrives on the window's own box (rounded like the window) before the words show",
              near(arrived["box"], win) and arrived["round"] == 18 and arrived["words"] == 0, (arrived, win))
        check("the orb has reached its place when the shape arrives", near(arrived["orb"], orb), (arrived["orb"], orb))
        end = page.evaluate("() => { const w = document.querySelector('.mentor-window'), cs = getComputedStyle(w); return [cs.clipPath, cs.transform, getComputedStyle(document.querySelector('.mp-skin')).opacity, getComputedStyle(document.querySelector('.mentor-col')).opacity]; }")
        check("once open: no clip, no transform, the skin gone and the words in full", end == ["none", "none", "0", "1"], end)
        check("only transform, opacity and clip-path move, and the move is about 320 ms", props["props"] and set(props["props"]) <= {"transform", "opacity", "clipPath"}
              and props["ms"] and max(props["ms"]) <= 360, props)
        after = page.evaluate(BUTTON)
        check("the round button stays where it is and shows no mood", after["box"] == before["box"] and "ml-neutral" in after["look"], (before, after))

        print("\n--- 2. The orb above the chat ---")
        # MW2 (v129): the strip of starter chips became one Suggestions pill, centred under the greeting, so the chip strip's box here became the
        # pill's, and "the chips use the window's full width" became "the pill is centred" (the box still uses the full width)
        g, chips, form = rect(page, ".mentor-greeting"), rect(page, ".mentor-suggest"), rect(page, ".mentor-form")
        ow = orb[2] - orb[0]
        check("the orb is larger than before (68 px), 84 to 96 px", 84 <= ow <= 96, ow)
        check("the orb sits above the greeting, the Suggestions pill and the box", orb[3] <= g[1] + 0.5 and g[3] <= chips[1] + 0.5 and chips[3] <= form[1] + 0.5, (orb, g, chips, form))
        check("the orb is centred in the window", abs(centre(orb)[0] - centre(win)[0]) < 1.5, (orb, win))
        check("the pill is centred and the box uses the window's full width", abs(centre(chips)[0] - centre(win)[0]) < 1.5 and form[2] - form[0] > win[2] - win[0] - 40, (chips, form, win))
        shrink = page.evaluate(ORB_MOVE, "how do I thin paint")
        check("in the chat view the orb shrinks smoothly (it starts from its old size)", len(shrink) == 1 and "scale(1." in shrink[0], shrink)
        page.wait_for_function("() => document.querySelector('.mentor-orbbox svg').getAnimations().every(a => a.animationName)")
        orb2, sc, back, close = rect(page, ".mentor-orbbox"), rect(page, ".mentor-scroll"), rect(page, ".mentor-back"), rect(page, ".mentor-close")
        win2 = rect(page, ".mentor-window")
        ow2 = orb2[2] - orb2[0]
        check("chat view: the orb is smaller (40 to 60 px) and stays above the conversation", 40 <= ow2 <= 60 and ow2 < ow and orb2[3] <= sc[1] + 0.5, (orb2, sc))
        check("chat view: the orb is centred between Back and Close and touches neither", abs(centre(orb2)[0] - centre(win2)[0]) < 1.5 and back[2] <= orb2[0] and orb2[2] <= close[0], (orb2, back, close))
        check("chat view: the conversation keeps most of the window below the orb", sc[1] - win2[1] <= 64, (sc, win2))
        grow = page.evaluate(ORB_MOVE, "back")
        check("Back to the start view: the orb grows back smoothly", len(grow) == 1 and "scale(0." in grow[0], grow)

        print("\n--- 4. Closing into the button ---")
        settled(page)
        escape_paused(page)
        shut = page.evaluate(AT, 1)
        check("closing ends on the round button's box, as a circle", near(shut["box"], before["box"]) and abs(shut["round"] - bw / 2) < 1, (shut, before))
        page.evaluate(RESUME)
        closed(page)
        check("focus goes back to the round button", page.evaluate("() => document.activeElement.id") == "mentor-button")
        # Escape 100 ms into the opening (the moves are put there and played on, all in one step, so a busy machine cannot finish them first)
        # (a turned animation reports its new, negative rate once its next frame has started)
        turned = page.evaluate("""() => new Promise(done => { document.getElementById('mentor-button').click();
            const w = document.querySelector('.mentor-window');
            const moves = w.getAnimations({ subtree: true }).filter(a => !a.animationName);
            moves.forEach(a => { a.currentTime = 100; a.play(); });
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
            const own = w.getAnimations();
            Promise.all(own.map(a => a.ready)).then(() => done(own.map(x => [x.playState === 'finished' ? 'running' : x.playState, x.playbackRate]))); })""")
        turned = [r for s, r in turned if s == "running"] if turned else None
        check("closed while still opening, the opening turns round", turned and all(r < 0 for r in turned), turned)
        closed(page)

        print("\n--- 3. 360x640, light and dark, three themes ---")
        for (w, h, mode, theme, look) in ((360, 640, "light", "classic", "magical"), (360, 640, "dark", "forge", "grounded"), (320, 568, "dark", "parchment", "futuristic")):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("""([th, m, l]) => { Object.assign(settings, { theme: th, appearance: m, mentorLook: l }); applyPalette(settings.palette); applyMentorLook(); mentorClear(); }""", [theme, mode, look])
            page.click("#mentor-button")
            settled(page)
            win, bar = rect(page, ".mentor-window"), rect(page, ".tabs .arc")
            close, edge = rect(page, ".mentor-close"), 6 + page.evaluate(BORDER)   # Back and Close sit 6 px inside the window's border, as before
            check(f"{w}x{h} {mode} {theme} {look}: start view fits above the bar, Close 44 px in its corner, the orb over nothing",
                  win[1] >= 0 and win[3] <= bar[1] + 1 and near([close[2] - close[0], close[3] - close[1]], [44, 44], 0.5)
                  and near([win[2] - close[2], close[1] - win[1]], [edge, edge], 1) and page.evaluate(OVER) == [], (win, bar, close, edge, page.evaluate(OVER)))
            page.fill(".mentor-input", "red armour"); page.keyboard.press("Enter")
            page.evaluate("() => document.activeElement.blur()")
            page.wait_for_function("() => document.querySelector('.mentor-orbbox svg').getAnimations().every(a => a.animationName)")
            win, back, close = rect(page, ".mentor-window"), rect(page, ".mentor-back"), rect(page, ".mentor-close")
            check(f"{w}x{h} {mode} {theme}: chat view: Back and Close keep their places and sizes, the orb over nothing, no sideways scroll",
                  near([back[0] - win[0], back[1] - win[1], back[2] - back[0], back[3] - back[1]], [edge, edge, 44, 44], 1)
                  and near([win[2] - close[2], close[1] - win[1], close[2] - close[0]], [edge, edge, 44], 1)
                  and page.evaluate(OVER) == [] and page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"), (win, back, close, page.evaluate(OVER)))
            page.keyboard.press("Escape"); closed(page)

        print("\n--- 5. Wide screen ---")
        page.set_viewport_size({"width": 1280, "height": 800})
        t.quiet(page)
        page.evaluate("() => mentorClear()")   # the start view
        b = page.evaluate(BUTTON)
        opened_paused(page)
        s = page.evaluate(AT, 0)
        page.evaluate(RESUME)
        settled(page)
        win, orb, g = rect(page, ".mentor-window"), rect(page, ".mentor-orbbox"), rect(page, ".mentor-greeting")
        check("1280: the move starts on the round button and the orb sits centred above the greeting",
              near(s["box"], b["box"]) and orb[3] <= g[1] + 0.5 and abs(centre(orb)[0] - centre(win)[0]) < 1.5, (s, b, orb, g))
        page.keyboard.press("Escape"); closed(page)

        print("\n--- 6. Reduced motion ---")
        rp = page   # the same page, with the setting switched on
        rp.set_viewport_size({"width": 390, "height": 844})
        rp.emulate_media(reduced_motion="reduce")
        rp.click("#mentor-button")
        rp.wait_for_selector(".mentor-window")
        info = rp.evaluate("""() => { const w = document.querySelector('.mentor-window'), cs = getComputedStyle(w), bd = document.querySelector('.mentor-backdrop');
            return { inside: w.getAnimations({ subtree: true }).length, clip: cs.clipPath, transform: cs.transform,
                     fade: bd.getAnimations().map(a => [a.effect.getTiming().duration, a.effect.getKeyframes().map(k => Object.keys(k).filter(x => !['offset', 'easing', 'composite', 'computedOffset'].includes(x)).join())]) }; }""")
        check("reduced motion: no growing, no travel, no clip; only a quick fade of opacity", info["inside"] == 0 and info["clip"] == "none" and info["transform"] == "none"
              and info["fade"] and all(d <= 150 and set(k) == {"opacity"} for d, k in info["fade"]), info)
        rp.keyboard.press("Escape")
        check("reduced motion: closing is at once and focus returns to the button", rp.locator(".mentor-backdrop").count() == 0 and rp.evaluate("() => document.activeElement.id") == "mentor-button")
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
