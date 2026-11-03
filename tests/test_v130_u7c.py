"""U7c tests for Minifolio (James, 3 Nov, late: Grounded's tap drops go random ways, in random avatar colours, and further). New behaviour only:
1. Two taps send the six drops different ways; on every tap they reach round the whole circle and never bunch (every gap 20 to 100 degrees).
2. Every drop's colour is one of the Grounded drawing's own paint colours (in two themes), the colours change between taps and no two
   drops side by side share one.
3. The drops travel further: at least 40 units of the drawing out from where they start (it was 22), still fading to nothing, and at the end
   of the move every drop is inside the drawing and the window, with no sideways scroll, at 360 and 390 px.
4. Reduce motion: a tap on Grounded starts nothing.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def open_grounded(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")
    page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
    page.evaluate("() => { settings.mentorLook = 'grounded'; applyMentorLook(); }")

# The drops' angles (from each holder's rotate), their fills, and the fills of the drawing's own painted shapes (everything else with an ml-g- class)
DROPS = """() => { const s = document.querySelector('.mentor-orbbox svg'), drops = [...s.querySelectorAll('.ml-spl')];
    const own = [...s.querySelectorAll('[class*="ml-g-"]')].filter(e => !e.classList.contains('ml-spl')).map(e => getComputedStyle(e).fill);
    return { n: drops.length, angles: drops.map(d => +/rotate\\(([-\\d.]+)/.exec(d.parentElement.getAttribute('transform'))[1]),
             fills: drops.map(d => getComputedStyle(d).fill), own: [...new Set(own)],
             names: s.getAnimations({ subtree: true }).filter(a => (a.animationName || '').startsWith('ml-tap-')).map(a => a.animationName) }; }"""

# Stop the move at its start and at its end, and measure each drop's centre (in drawing units) from the pool's centre (its holder's rotate centre),
# its opacity at the end, and whether it is inside the drawing and the window there
REACH = """() => { const s = document.querySelector('.mentor-orbbox svg'), vb = s.viewBox.baseVal, box = s.getBoundingClientRect(), k = box.width / vb.width;
    const all = s.getAnimations({ subtree: true }); all.forEach(a => a.pause());
    const drops = [...s.querySelectorAll('.ml-spl')], moves = drops.map(d => d.getAnimations().find(a => a.animationName === 'ml-tap-drop'));
    const centre = d => { const m = /rotate\\([-\\d.]+ ([-\\d.]+) ([-\\d.]+)/.exec(d.parentElement.getAttribute('transform')); return [+m[1], +m[2]]; };
    const reach = d => { const r = d.getBoundingClientRect(), [cx, cy] = centre(d);
      return Math.hypot(vb.x + (r.left + r.width / 2 - box.left) / k - cx, vb.y + (r.top + r.height / 2 - box.top) / k - cy); };
    moves.forEach(a => { a.currentTime = 0; }); const start = drops.map(reach);
    moves.forEach(a => { a.currentTime = a.effect.getComputedTiming().duration * 0.999; }); const end = drops.map(reach);
    const inside = drops.every(d => { const r = d.getBoundingClientRect(); return r.left >= box.left && r.right <= box.right && r.top >= box.top && r.bottom <= box.bottom
      && r.left >= 0 && r.right <= innerWidth; });
    const opacity = Math.max(...drops.map(d => +getComputedStyle(d).opacity));
    const scroll = document.documentElement.scrollWidth - innerWidth;
    all.forEach(a => a.play()); moves.forEach(a => a.finish());
    return { travel: end.map((e, i) => Math.round((e - start[i]) * 10) / 10), inside, opacity, scroll, found: moves.every(Boolean) }; }"""

GONE = "() => !document.querySelector('.mentor-orbbox svg.ml-tap')"

def gaps(angles):
    a = sorted(x % 360 for x in angles)
    return [((a[(i + 1) % len(a)] - a[i]) + 360) % 360 for i in range(len(a))]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 360, "height": 780}, service_workers="block")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=[], settings={"examplesChecked": True}, launch=True)
        open_grounded(page)

        print("--- 1. Random directions ---")
        taps = []
        for _ in range(5):
            page.click(".mentor-orbbox")
            taps.append(page.evaluate(DROPS))
            page.wait_for_function(GONE, timeout=3000)
        check("still six drops, and each tap plays the drop move on all six", all(d["n"] == 6 and d["names"] == ["ml-tap-drop"] * 6 for d in taps), taps[0])
        check("two taps send the drops different ways", taps[0]["angles"] != taps[1]["angles"], (taps[0]["angles"], taps[1]["angles"]))
        check("the directions are not six fixed angles: five taps give five different sets",
              len({tuple(sorted(round(a) % 360 for a in d["angles"])) for d in taps}) == 5, [d["angles"] for d in taps])
        spread = [gaps(d["angles"]) for d in taps]
        check("on every tap the drops reach round the whole circle and never bunch (every gap between neighbours 20 to 100 degrees)",
              all(19.5 <= g <= 100.5 for gs in spread for g in gs), spread)

        print("\n--- 2. Random avatar colours ---")
        check("every drop colour is one of the Grounded drawing's own paint colours (Classic, dark)",
              all(f in d["own"] for d in taps for f in d["fills"]), [(d["fills"], d["own"]) for d in taps[:2]])
        check("the colours change from tap to tap", len({tuple(d["fills"]) for d in taps}) >= 2, [d["fills"] for d in taps])
        check("no two drops side by side share a colour", all(d["fills"][i] != d["fills"][i - 1] for d in taps for i in range(1, 6)), [d["fills"] for d in taps])
        page.evaluate("() => { Object.assign(settings, { theme: 'parchment', appearance: 'light' }); applyPalette(settings.palette); }")
        other = []
        for _ in range(3):
            page.click(".mentor-orbbox")
            other.append(page.evaluate(DROPS))
            page.wait_for_function(GONE, timeout=3000)
        check("in another theme (Parchment, light) the drops take that theme's avatar colours",
              all(f in d["own"] for d in other for f in d["fills"]) and set(other[0]["own"]) != set(taps[0]["own"]), [(d["fills"], d["own"]) for d in other[:1]])

        print("\n--- 3. Further, and nothing cut or scrolling ---")
        for width in (360, 390):
            page.set_viewport_size({"width": width, "height": 780})
            page.wait_for_timeout(100)
            page.click(".mentor-orbbox")
            r = page.evaluate(REACH)
            page.wait_for_function(GONE, timeout=3000)
            if width == 360:
                check("the drops travel at least 40 units of the drawing out (twice the old 22), and have faded to nothing at the end",
                      r["found"] and all(40 <= x <= 50 for x in r["travel"]) and r["opacity"] < 0.05, r)
            check(f"{width} px: at the end of the move every drop is inside the drawing and the window, and nothing scrolls sideways",
                  r["inside"] and r["scroll"] <= 0, r)
        page.keyboard.press("Escape")
        check("no page errors", not errors, errors[:3])
        ctx.close()

        print("\n--- 4. Reduce motion ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = rm.new_page()
        t.load(rp, paints=[], settings={"examplesChecked": True, "mentorLook": "grounded"}, launch=False)
        rp.click("#mentor-button")
        rp.wait_for_selector(".mentor-window")
        rp.click(".mentor-orbbox")
        check("reduce motion: a tap on Grounded starts nothing",
              rp.evaluate("() => document.querySelector('.mentor-orbbox svg.ml-grounded') && document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).length === 0"))
        rm.close()
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
