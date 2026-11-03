"""JF1 tests for Minifolio (James's fixes after v129, 3 Nov). New behaviour only:
1. A tap on a segment of the start circle lights nothing where the bar will be. The tapped segment moves into the bar at once (the copies travel
   while the real bar waits see-through), and the phone's own tap highlight (Android's translucent blue, drawn above the page) went with it, so a
   blue bar piece showed where the bar would be. No tap highlight (and no long-press text selection) on the circle, the bar or the Mentor
   button; while a finger is down and straight after the tap, the bar's place stays the plain page, in all four themes.
2. Start-up uses LR1's loading ring round the start circle's centre again (it fills as the files arrive, also on a slow network); MO6's
   full-screen loading screen is gone, code and styles.
3. The app icon (icon-192.png, icon-512.png) is the round 7 Futuristic Mentor, not the old ring with a dot, centred on the app's dark background
   with room for a round or squircle mask, and the manifest lists both sizes for "any" and "maskable".
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, json, math, os, struct, sys
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_ring_done

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

def seed(page, settings=None):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("""(s) => { localStorage.clear(); localStorage.setItem('shades-of-grey-recipes', JSON.stringify({ parts: [], techniques: [], paints: [], recipes: [], schemes: [], shorthand: {}, v15: true }));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", settings)

SETTLED = """() => !document.querySelector('.mo-tr, .mo-load, html > .tabs') && !document.body.classList.contains('mo-travelling')
    && !document.body.classList.contains('ring-loading') && document.querySelector('nav.tabs').getAnimations({ subtree: true }).length === 0"""
# the tap highlight and text selection of the circle's segments, the Mentor button and (from inside) the bar
PRESS_LOOK = """() => [...document.querySelectorAll('nav.tabs .arc > button')].map(b => { const c = getComputedStyle(b);
    return [b.dataset.tab || b.id, c.webkitTapHighlightColor, b.matches('[data-tab]') ? c.userSelect : 'none']; })"""
# every frame: is any of the real bar drawn (a real segment seen, the bar's own fade seen) while the copies travel?
WATCH = """() => { window.__bar = []; const segs = [...document.querySelectorAll('nav.tabs .arc [data-tab]')];
    const seen = (el) => { let e = el, o = 1; while (e && e.nodeType === 1) { const c = getComputedStyle(e); if (c.display === 'none' || c.visibility === 'hidden') return 0; o *= parseFloat(c.opacity); e = e.parentElement; } return o; };
    const rec = () => { const b = document.body; if (b.classList.contains('mo-travelling')) window.__bar.push({ segs: segs.map(seen),
        fade: getComputedStyle(document.querySelector('nav.tabs'), '::before').visibility, copies: document.querySelectorAll('.mo-tr .w').length });
      if (window.__bar.length < 600 && !window.__barStop) requestAnimationFrame(rec); };
    requestAnimationFrame(rec); }"""

def band(png, top):
    """The largest difference (any channel) between the page colour and a pixel in the strip from `top` to the bottom of the screenshot."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = im.size
    px = im.load()
    base = px[w // 2, h - 2]
    worst = 0
    for y in range(top, h, 3):
        for x in range(0, w, 3):
            c = px[x, y]
            worst = max(worst, max(abs(c[i] - base[i]) for i in range(3)))
    return worst, base

def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else None

def main():
    html, app, early = t.read("index.html"), t.read("app.js"), t.read("early.js")
    manifest = json.loads(t.read("manifest.json"))
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        print("--- 1. A tap on the start circle lights nothing where the bar will be ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        cdp = ctx.new_cdp_session(page)
        for theme, mode in (("classic", "dark"), ("parchment", "light"), ("forge", "dark"), ("bench", "light")):
            seed(page, {"theme": theme, "appearance": mode})
            page.goto(t.URL)
            wait_ring_done(page)
            page.wait_for_function(SETTLED, timeout=15000)
            look = page.evaluate(PRESS_LOOK)
            check(f"{theme} {mode}: no tap highlight and no text selection on the circle's segments or the Mentor button",
                  len(look) == 5 and all(c == "rgba(0, 0, 0, 0)" and s == "none" for _, c, s in look), look)
            box = page.evaluate("() => { const r = document.querySelector('nav.tabs .arc [data-tab=units]').getBoundingClientRect(); return [r.left + r.width * 0.3, r.top + r.height * 0.35]; }")
            # a finger held down on Models: nothing lights at the bottom of the screen, and the bar has no pressed look
            empty, base = band(page.screenshot(), 844 - 120)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": box[0], "y": box[1]}]})
            page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            held, _ = band(page.screenshot(), 844 - 120)
            pressed = page.evaluate("() => document.querySelectorAll('nav.tabs .lq-press, nav.tabs .ripple').length")
            cdp.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
            check(f"{theme} {mode}: while a finger is on a segment, the bar's place stays the plain page", held <= max(14, empty + 4) and pressed == 0, (held, empty, pressed, base))
            # the tap itself, with every move slowed to a tenth so the frames straight after it can be looked at
            cdp.send("Animation.enable")
            cdp.send("Animation.setPlaybackRate", {"playbackRate": 0.1})
            page.evaluate(WATCH)
            page.touchscreen.tap(box[0], box[1])
            after, _ = band(page.screenshot(), 844 - 120)
            state = page.evaluate("() => ({ travelling: document.body.classList.contains('mo-travelling'), launching: document.body.classList.contains('launching') })")
            check(f"{theme} {mode}: straight after the tap the copies set off and the bar's place is still the plain page", state["travelling"] and not state["launching"] and after <= max(14, empty + 4), (after, empty, state))
            cdp.send("Animation.setPlaybackRate", {"playbackRate": 1})
            if theme in ("classic", "bench"):   # the whole travel, frame by frame, in one dark and one light theme (the file stays quick)
                page.wait_for_function(SETTLED, timeout=15000)
                frames = page.evaluate("() => { window.__barStop = true; return window.__bar; }")
                lit = [f for f in frames if f["copies"] and (max(f["segs"]) > 0 or f["fade"] != "hidden")]
                check(f"{theme} {mode}: in every frame of the travel the real bar is not drawn (segments and fade unseen) until the copies have landed",
                      len(frames) > 5 and not lit, (len(frames), lit[:3]))
            else:
                page.evaluate("() => { window.__barStop = true; document.getAnimations().forEach(a => { if (a.effect.getComputedTiming().iterations !== Infinity) a.finish(); }); }")
                page.wait_for_function(SETTLED, timeout=15000)
            if theme == "classic":
                look = page.evaluate(PRESS_LOOK)
                check("in the bar too: no tap highlight on the pieces or the Mentor button", all(c == "rgba(0, 0, 0, 0)" for _, c, _ in look), look)
        ctx.close()

        print("\n--- 2. Start-up uses LR1's ring again; MO6's loading screen is gone ---")
        body = html[html.find("\n<body") + 1:]
        arc = body[body.find('<div class="arc">'):]
        check("index.html: LR1's ring is inside the start circle, before its segments, and no MO6 loading screen or its styles are left",
              arc.find('<svg class="mo-load"') > 0 and arc.find('<svg class="mo-load"') < arc.find("<button data-tab=")
              and not any(k in html for k in ("mo6-load", "mo6-ring", "mo6-bg", "mo6-spot", "mo6-handing", "display-mode: standalone")), arc[:120])
        check("app.js and early.js: the loading screen's code is gone (no hand-over, no screen fade, no --l0 to --l4 lighting)",
              not any(k in app for k in ("mo6-load", "function handOver", "fadeLoadBox", "mo6-handing"))
              and "mo6" not in early and ".lr-s" in early and "--l\" + i" not in early)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        seed(page)
        page.route("**/*.js*", lambda r: r.abort())
        page.goto(t.URL, wait_until="domcontentloaded")
        s = page.evaluate("""() => { const r = document.querySelector('.mo-load'), o = document.getElementById('mentor-button');
            const a = r && r.getBoundingClientRect(), b = o.getBoundingClientRect();
            // anything (other than the start circle's own layer) laid over the whole screen, as MO6's loading screen was
            const cover = [...document.body.querySelectorAll('*')].filter(e => !e.closest('nav.tabs') && getComputedStyle(e).position === 'fixed' && getComputedStyle(e).visibility !== 'hidden'
                && getComputedStyle(e).display !== 'none' && (() => { const q = e.getBoundingClientRect(); return q.width >= innerWidth * 0.9 && q.height >= innerHeight * 0.9; })()).map(e => e.className);
            return { inArc: !!(r && r.closest('nav.tabs .arc')), role: r && r.getAttribute('role'), dx: a ? a.left + a.width / 2 - (b.left + b.width / 2) : 99,
                     dy: a ? a.top + a.height / 2 - (b.top + b.height / 2) : 99, button: getComputedStyle(o).opacity, cover, onTop: cover.length === 0 }; }""")
        check("with every script blocked: the first frame is LR1's ring round the Mentor button, which shows (no screen over it)",
              s["inArc"] and s["role"] == "progressbar" and abs(s["dx"]) < 1.5 and abs(s["dy"]) < 1.5 and s["button"] == "1" and s["onTop"], s)
        page.unroute("**/*.js*")
        # a cold start on a slow network and a slow phone: the ring still fills, step by step, then goes
        cdp = ctx.new_cdp_session(page)
        seed(page)
        page.add_init_script("""(() => { window.__now = []; new MutationObserver(() => { const r = document.querySelector('.mo-load');
            if (r) { const v = +r.getAttribute('aria-valuenow'); if (window.__now[window.__now.length - 1] !== v) window.__now.push(v); } })
            .observe(document, { attributes: true, subtree: true, attributeFilter: ['aria-valuenow'] }); })();""")
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 120, "downloadThroughput": 2_000_000, "uploadThroughput": 500_000})
        page.goto(t.URL)
        wait_ring_done(page, timeout=30000)
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
        now = page.evaluate("() => window.__now")
        check("slow cold start: the ring fills in many steps, never back, to full, then goes and the circle can be used",
              len(now) >= 6 and now == sorted(now) and now[-1] == 100 and page.evaluate(
                  "() => !document.querySelector('.mo-load, .ring-hold') && [...document.querySelectorAll('.arc [data-tab]')].every(b => getComputedStyle(b).pointerEvents !== 'none')"), now)
        ctx.close()

        print("\n--- 3. The app icon is the round 7 Futuristic Mentor ---")
        BG = (0x0b, 0x12, 0x20)
        OLD = [(0x64, 0x74, 0x8b), (0x63, 0x66, 0xf1), (0x38, 0xbd, 0xf8), (0x22, 0xd3, 0xee), (0xa7, 0xf3, 0xd0), (0x7d, 0xd3, 0xfc), (0x22, 0x30, 0x4a)]
        R7 = {"mint (t1)": (0x5e, 0xea, 0xd4), "violet (t2)": (0xc4, 0xb5, 0xfd), "slate (t3)": (0x81, 0x93, 0xad)}
        d = lambda a, b: max(abs(a[i] - b[i]) for i in range(3))
        for size in (192, 512):
            path = os.path.join(t.ROOT, f"icon-{size}.png")
            im = Image.open(path).convert("RGB")
            px = im.load()
            pts = [(x, y) for x in range(0, size, max(1, size // 64)) for y in range(0, size, max(1, size // 64))]
            fg = [px[q] for q in pts if d(px[q], BG) > 24]
            old_like = sum(1 for c in fg if min(d(c, o) for o in OLD) <= 24) / max(1, len(fg))
            r7 = {k: sum(1 for c in fg if d(c, v) <= 24) for k, v in R7.items()}
            edge = [px[int(size / 2 + 0.42 * size * math.cos(a * math.pi / 90)), int(size / 2 + 0.42 * size * math.sin(a * math.pi / 90))] for a in range(180)]
            check(f"icon-{size}.png: {size} x {size}, the dark page colour in the corners and all round outside the middle 84% (room for a round or squircle mask)",
                  png_size(path) == (size, size) and d(px[1, 1], BG) <= 2 and all(d(c, BG) <= 6 for c in edge), (png_size(path), px[1, 1]))
            check(f"icon-{size}.png: drawn from round 7's Futuristic look (its mint, violet and slate ring, its grey housing), not the old ring and dot",
                  old_like < 0.5 and all(n >= 10 for n in r7.values()) and len(fg) > 300, (round(old_like, 2), r7, len(fg)))
        icons = manifest.get("icons", [])
        listed = {(i.get("src"), i.get("sizes"), i.get("purpose")) for i in icons}
        check("manifest.json lists both icons for any and for maskable, on the dark background colour",
              {("icon-192.png", "192x192", "any"), ("icon-512.png", "512x512", "any"), ("icon-192.png", "192x192", "maskable"), ("icon-512.png", "512x512", "maskable")} <= listed
              and manifest.get("background_color") == "#0b1220", listed)
        check("the page's own icons (tab and home screen) are the same file", '<link rel="icon" href="icon-192.png">' in html and '<link rel="apple-touch-icon" href="icon-192.png">' in html)
        check("no page errors", not errors, errors[:3])
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
