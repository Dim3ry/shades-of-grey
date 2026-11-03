"""U7 tests for Minifolio (Mentor looks round 7: James's own drawings, with round 6 kept as a fallback). New behaviour only:
1. Round 6 is kept: mentor-looks-r6.js is there with its one comment line, and nothing the app ships loads or caches it (only mentor-looks.js
   names it, in SWITCHING BACK, which lists the steps back).
2. The looks file: three looks with all five states; every class starts ml-; no ids, scripts, images, gradients or filters; the CSS uses only
   --mentor-* variables, defines none and has no fixed colours; nothing uses --mentor-s0 to --mentor-s4; every animation is inside .ml-live,
   and reduced motion (and .ml-still) stops it.
3. Theme colours: every theme sets --mentor-t1 to --mentor-t3 (the same in light and dark); the colour set no longer changes the avatars or the
   loading ring; LR1's five ring strokes are the theme colours, matching the round button's ring.
4. The round button's inline drawing is MENTOR_LOOKS.futuristic.neutral; the window orb has no viewBox crop and nothing round it clips it;
   switching the look redraws the button and the window at once; the window's buttons and chips stay still while the orb moves.
5. James's tweaks to Magical (3 Nov, evening): no backing disc, a few solid faceted crystals, each its own size, lean and shade, a couple of
   loose shards, and the stone ring turning slowly (window only, steady, and on through a mood change).
6. The moods can be told apart at 50 px in greyscale with motion off: every pair of states differs in at least 6% of pixels.
7. James's second round (3 Nov, evening): one outline (every outlined edge in all three looks has the same colour, width and joins at 50, 64 and
   88 px; Magical's outlines are drawn last in their groups and its inner lines share one thinner width); Magical's loose fragments vibrate, in the
   window only; a tap on the window's orb plays the look's one-off move (Futuristic: four of six bolts at random; Magical: the ring spins once;
   Grounded: six paint drops), keeps the focus in the text box, asks nothing and ignores a second tap while it plays; reduced motion plays none.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import io, itertools, os, re, sys
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []
LOOKS = ["futuristic", "magical", "grounded"]
STATES = ["neutral", "thinking", "pleased", "unsure", "finished"]
THEMES = ["classic", "parchment", "forge", "bench"]
# Classic and Parchment as James gave them; Grim Forge and Paint Bench are their own dark-mode good, note and muted (TH2 and TH4 changed them)
WANT_T = {"classic": ["#5eead4", "#c4b5fd", "#8193ad"], "parchment": ["#8cbf7a", "#6fb8a6", "#a79877"]}

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def hexrgb(h):
    h = h.strip().lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"

def open_window(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")

def css_rules(css):
    """The top-level rules of MENTOR_LOOKS_CSS as (selector, body), leaving out @keyframes and unwrapping @media."""
    out, i = [], 0
    while i < len(css):
        j = css.find("{", i)
        if j < 0:
            break
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while depth and k < len(css):
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        if sel.startswith("@media"):
            out += [(sel + " " + s, b) for s, b in css_rules(body)]
        elif not sel.startswith("@keyframes"):
            out.append((sel, body))
        i = k
    return out

def main():
    root = t.ROOT
    src = t.read("mentor-looks.js")
    r6 = t.read("mentor-looks-r6.js")
    html = t.read("index.html")
    print("--- 1. Round 6 is kept ---")
    check("mentor-looks-r6.js is round 6 with its one comment line on top",
          r6.split("\n")[0] == "// Round 6 Mentor looks, kept in case George prefers them. To switch back, see SWITCHING BACK in mentor-looks.js."
          and "const MENTOR_LOOKS = {" in r6 and "--mentor-s0" in r6)
    shipped = [n for n in os.listdir(root) if n.endswith((".js", ".html", ".json")) and n not in ("mentor-looks.js", "mentor-looks-r6.js")]
    named = [n for n in shipped if re.search(r"""["'/]mentor-looks-r6\.js""", open(os.path.join(root, n), encoding="utf-8").read())]
    check("nothing the app ships loads or caches round 6 (no page, script or worker file asks for it)", shipped and not named, named)
    head = src[:src.find("const MENTOR_LOOKS")]
    check("SWITCHING BACK at the top of mentor-looks.js lists the way back", head.startswith("// ===== SWITCHING BACK") and all(w in head for w in
          ("mentor-looks-r6.js", "cache list", "#mentor-button", "25 25 150 150", "--mentor-s0", "--mentor-s4", "Bump the version")))

    print("\n--- 2. The looks file ---")
    css = src.split("const MENTOR_LOOKS_CSS = ", 1)[1]
    drawings = src.split("const MENTOR_LOOKS_CSS", 1)[0]
    classes = set(c for m in re.findall(r"class='([^']+)'", drawings) for c in m.split()) | set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    check("every class starts ml-", classes and all(c.startswith("ml-") for c in classes), sorted(c for c in classes if not c.startswith("ml-")))
    bad = re.findall(r"\sid=|<script|<image|<img|<use|href|[Gg]radient|<filter|filter\s*:|url\(|\son[a-z]+=", src.split("const MENTOR_LOOKS", 1)[1])
    check("no ids, scripts, images, gradients or filters in the drawings or styles", not bad, bad[:5])
    check("the CSS uses only --mentor-* variables, defines none and has no fixed colours",
          all(v.startswith("--mentor-") for v in re.findall(r"var\((--[\w-]+)", css)) and not re.search(r"[{;]\s*--[\w-]+\s*:", css)
          and not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|\b(white|black|red|blue|green|gray|grey|transparent|currentColor)\b",
                            re.sub(r"\.[a-zA-Z][\w-]*", "", css)))   # class names such as .ml-g-green are not colours
    check("nothing in mentor-looks.js uses --mentor-s0 to --mentor-s4", not re.search(r"--mentor-s\d", src.split("const MENTOR_LOOKS", 1)[1]))
    rules = css_rules(css.strip().strip('";'))
    animated = [s for s, b in rules if re.search(r"(^|;)animation(-name)?:(?!none)", b)]
    stops = [s for s, b in rules if "animation:none!important" in b]
    check("every animation runs only inside .ml-live", animated and all(part.strip().startswith(".ml-live") for s in animated for part in s.split(",")),
          [s for s in animated if not all(p.strip().startswith(".ml-live") for p in s.split(","))][:3])
    check("reduced motion and .ml-still stop all of it", any("prefers-reduced-motion:reduce" in s for s in stops) and any(".ml-still" in s for s in stops), stops)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, paints=[], settings={"examplesChecked": True}, launch=True)
        shape = page.evaluate("() => Object.fromEntries(Object.entries(MENTOR_LOOKS).map(([k, v]) => [k, Object.keys(v)]))")
        check("three looks, each with all five states", sorted(shape) == sorted(LOOKS) and all(sorted(v) == sorted(STATES) for v in shape.values()), shape)

        print("\n--- 3. Theme colours ---")
        TV = """() => { const cs = getComputedStyle(document.documentElement);
            return [1, 2, 3].map(i => cs.getPropertyValue('--mentor-t' + i).trim().toLowerCase()).concat(['good', 'note', 'muted'].map(n => cs.getPropertyValue('--' + n).trim().toLowerCase())); }"""
        SET = """([th, m]) => { Object.assign(settings, { theme: th, appearance: m }); applyPalette(settings.palette); }"""
        for theme in THEMES:
            got = {}
            for mode in ("dark", "light"):
                page.evaluate(SET, [theme, mode])
                got[mode] = page.evaluate(TV)
            want = WANT_T.get(theme, got["dark"][3:])
            check(f"{theme}: --mentor-t1 to --mentor-t3 are set, the same in light and dark ({', '.join(want)})",
                  got["dark"][:3] == got["light"][:3] == [w.lower() for w in want], got)
        # v129: MO6 replaced LR1's ring with the loading screen's icon ring (.mo6-load .mo6-ring), which draws round 7's own segments (.ml-segs .ml-k0
        # to .ml-k4). A stand-in of that ring (the real one is gone once the app has loaded), so its five strokes can be read in any theme.
        STROKES = """() => { const NS = 'http://www.w3.org/2000/svg', box = document.createElement('div'), svg = document.createElementNS(NS, 'svg'); box.className = 'mo-load mo6-load';
            svg.setAttribute('class', 'mo6-ring mo6-icon'); const g = document.createElementNS(NS, 'g'); g.setAttribute('class', 'ml-segs'); svg.appendChild(g);
            for (let i = 0; i < 5; i++) { const c = document.createElementNS(NS, 'circle'); c.setAttribute('class', 'ml-k' + i); g.appendChild(c); }
            box.appendChild(svg); document.body.appendChild(box);
            const lr = [0, 1, 2, 3, 4].map(i => getComputedStyle(box.querySelector('.ml-k' + i)).stroke); box.remove();
            const ring = [0, 1, 2, 3, 4].map(i => getComputedStyle(document.querySelector('#mentor-button .ml-segs .ml-k' + i)).stroke);
            return { lr, ring }; }"""
        same = []
        for theme in THEMES:
            for mode in ("dark", "light"):
                page.evaluate(SET, [theme, mode])
                s = page.evaluate(STROKES)
                same.append(s["lr"] == s["ring"] and len(set(s["lr"])) == 5)
        check("the loading ring's five segments are the round button's ring colours, in every theme, light and dark", all(same), same)
        # v129: LR1's own strokes went with MO6; the loading screen in index.html now draws round 7's five segments itself
        load_html = html[html.find('class="mo-load mo6-load"'):]
        load_html = load_html[:load_html.find("</div>")]
        check("the loading screen draws round 7's five ring segments (ml-k0 to ml-k4), so it has the theme colours (t3, t2, half t2 and half dot, dot, t1)",
              all(f"ml-k{i}" in load_html for i in range(5)) and "ml-segs" in load_html, load_html[:200])
        page.evaluate(SET, ["forge", "dark"])
        before = page.evaluate(STROKES)
        page.evaluate("() => { settings.palette = 'greyscale'; applyPalette('greyscale'); }")
        after = page.evaluate(STROKES)
        page.evaluate("() => { settings.palette = 'ice'; applyPalette('ice'); }")
        check("switching the colour set changes neither the avatar's ring nor the loading ring", before == after, (before, after))

        print("\n--- 4. The round button and the window orb ---")
        page.evaluate(SET, ["classic", "dark"])
        key = 'id="mentor-button" aria-label="Ask Mentor">'
        i = html.index(key) + len(key)
        inline = html[i:html.index("</svg>", i) + 6]
        check("the round button's inline drawing is MENTOR_LOOKS.futuristic.neutral, exactly", inline == page.evaluate("() => MENTOR_LOOKS.futuristic.neutral"))
        check("app.js no longer crops the window orb", 'setAttribute("viewBox", "25 25 150 150")' not in t.read("app.js"))
        page.click('.tabs button[data-tab="dashboard"]')
        t.quiet(page)
        open_window(page)
        page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
        vb = page.evaluate("""() => ['futuristic', 'magical', 'grounded'].map(l => { settings.mentorLook = l; applyMentorLook();
            const own = new DOMParser().parseFromString(MENTOR_LOOKS[l].neutral, 'image/svg+xml').documentElement.getAttribute('viewBox');
            return [own, document.querySelector('.mentor-orbbox svg').getAttribute('viewBox'), document.querySelector('.mentor-orbbox svg').classList.contains('ml-' + l),
                    document.querySelector('#mentor-button svg').classList.contains('ml-' + l)]; })""")
        check("the window orb uses each drawing's own viewBox (no crop)", all(a == b == "16.67 16.67 166.67 166.67" for a, b, _, _ in vb), vb)
        check("switching the look redraws the round button and the open window at once", all(w and b for _, _, w, b in vb), vb)
        clip = page.evaluate("""() => { const out = []; for (let e = document.querySelector('.mentor-orbbox'); e && e !== document.body; e = e.parentElement) {
            const cs = getComputedStyle(e); if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible' || cs.clipPath !== 'none') out.push(e.className); } return out; }""")
        check("nothing round the window orb clips it (the orb box and every parent inside the page)", clip == [], clip)
        still = page.evaluate("""async () => { const rects = () => [...document.querySelectorAll('.mentor-window button, .mentor-window input')].map(b => { const r = b.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(Math.round).join(); });
            const a = rects(); await new Promise(r => setTimeout(r, 900)); const b = rects();
            const moving = document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).filter(x => x.playState === 'running').length;
            const own = [...document.querySelectorAll('.mentor-window button, .mentor-window input')].filter(x => x.getAnimations().length || getComputedStyle(x).transform !== 'none').length;
            return { same: a.join('|') === b.join('|'), moving, own }; }""")
        check("while the orb moves, no button, chip or box in the window moves", still["same"] and still["moving"] > 0 and still["own"] == 0, still)
        rest = page.evaluate("() => [...document.querySelectorAll('#mentor-button *, [data-mentor-look] *')].filter(e => e.getAnimations().length).length")
        check("the round button and the Settings look chips never move", rest == 0, rest)

        print("\n--- 5. James's tweaks to Magical ---")
        page.evaluate("() => { settings.mentorLook = 'magical'; applyMentorLook(); }")
        m = page.evaluate("""() => { const s = document.querySelector('.mentor-orbbox svg');
            const big = [...s.querySelectorAll('circle')].filter(c => +c.getAttribute('r') >= 20 && !c.closest('.ml-fglow')).length;
            const disc = s.querySelectorAll('[class*="disc"], [class*="tring"], [class*="tile"], [class*="glow1"], [class*="glow2"]').length;
            const crystals = [...s.querySelectorAll('.ml-cg [class*="ml-m-cr"]')];
            const faces = crystals.map(c => [...c.parentElement.children].map(k => k.getAttribute('class')).filter(n => /ml-m-f[abc]/.test(n)).length);
            const fills = new Set(crystals.map(c => getComputedStyle(c).fill));
            const sizes = crystals.map(c => { const b = c.getBBox(); return [Math.round(b.width * 2) / 2, Math.round(b.height * 2) / 2].join('x'); });
            const angles = crystals.map(c => +/rotate\\(([-\\d.]+)/.exec(c.closest('[transform]').getAttribute('transform'))[1]).sort((a, b) => a - b);
            const gaps = angles.map((a, i) => ((angles[(i + 1) % angles.length] - a) + 360) % 360);
            const tips = crystals.map(c => { const pts = c.getAttribute('d').match(/-?[\\d.]+/g).map(Number); return Math.round((pts[4] - 100) * 10); });
            return { big, disc, n: crystals.length, faces, fills: fills.size, sizes: new Set(sizes).size, gaps: new Set(gaps.map(Math.round)).size, leans: new Set(tips).size,
                     shards: s.querySelectorAll('.ml-fly').length }; }""")
        check("Magical: no backing disc, rim, rings or glow circle behind the crystals", m["big"] == 0 and m["disc"] == 0, m)
        check("Magical: a few solid crystals (5 to 10), each with lit, shaded and tip facets", 5 <= m["n"] <= 10 and all(f == 3 for f in m["faces"]), m)
        check("Magical: no two crystals alike (each its own size and lean, uneven spacing, at least four shades)",
              m["sizes"] == m["n"] and m["leans"] >= m["n"] - 1 and m["gaps"] >= 4 and m["fills"] >= 4, m)
        # James's third round (his picture): eight small fragments round the ring, where the first round had cut thirteen to three
        check("Magical: about eight small loose fragments (6 to 10)", 6 <= m["shards"] <= 10, m)
        ring = page.evaluate("""() => { const s = document.querySelector('.mentor-orbbox svg'), slabs = [...s.querySelectorAll('.ml-orbit [class^="ml-m-st"]')];
            const boxes = slabs.map(e => e.getBBox()); let touching = 0;
            const lines = [...s.querySelectorAll('.ml-orbit .ml-m-line')];
            for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) { const a = lines[i], b = lines[j], la = a.getTotalLength(), lb = b.getTotalLength();
              for (let p = 0; p < la; p += 1.5) { const q = a.getPointAtLength(p); for (let r = 0; r < lb; r += 1.5) { const w = b.getPointAtLength(r); if (Math.hypot(q.x - w.x, q.y - w.y) < 2.2) { touching++; p = la; break; } } } }
            return { n: slabs.length, fills: new Set(slabs.map(e => getComputedStyle(e).fill)).size, sides: s.querySelectorAll('.ml-orbit [class^="ml-m-sd"]').length,
                     cracks: slabs.map(e => e.parentElement.querySelectorAll('.ml-crack').length), streaks: s.querySelectorAll('.ml-orbit .ml-m-hl').length, touching }; }""")
        check("Magical: the ring is four chunky slabs in four colours, each with a side face, a streak and 2 to 5 cracks, and no two outlines touch",
              ring["n"] == 4 and ring["fills"] == 4 and ring["sides"] == 4 and ring["streaks"] == 4 and all(2 <= k <= 5 for k in ring["cracks"]) and ring["touching"] == 0, ring)
        ORBIT = """() => { const g = document.querySelector('.mentor-orbbox .ml-orbit'); const a = g && g.getAnimations()[0];
            if (!a) return null; const tm = a.effect.getComputedTiming(), kf = a.effect.getKeyframes();
            return { name: a.animationName, dur: tm.duration, it: tm.iterations, ease: getComputedStyle(g).animationTimingFunction, end: kf[kf.length - 1].transform, p: tm.progress }; }"""
        o = page.evaluate(ORBIT)
        check("Magical: the stone ring turns as one in the window, one steady turn every 30 to 60 s",
              o and 30000 <= o["dur"] <= 60000 and o["it"] == float("inf") and o["ease"] == "linear" and "360deg" in o["end"], o)
        page.wait_for_timeout(1200)
        p1 = page.evaluate(ORBIT)["p"]
        page.evaluate("() => mentorMood('pleased')")
        p2 = page.evaluate(ORBIT)["p"]
        turn = abs(p2 - p1) % 1
        check("Magical: a mood change does not send the ring back to the start (it turns on from where it was)", min(turn, 1 - turn) < 0.01, (p1, p2))
        page.evaluate("() => document.querySelector('.mentor-orbbox').classList.add('ml-still')")
        check("Magical: .ml-still stops the ring", page.evaluate(ORBIT) is None)
        page.evaluate("() => document.querySelector('.mentor-orbbox').classList.remove('ml-still')")

        print("\n--- 7. James's second round: one outline, vibrating fragments, tap moves ---")
        # every outlined edge: the same colour and width on screen in all three looks, at the button (50), the start circle (64) and the window (88)
        ol = page.evaluate("""() => { const box = document.createElement('div'); document.body.appendChild(box);   /* still drawings: a drip mid-fall is scaled on purpose */ const out = {};
            for (const l of ['futuristic', 'magical', 'grounded']) for (const px of [50, 64, 88]) {
              const svg = minifolioLook.svg(l, 'neutral'); svg.style.width = svg.style.height = px + 'px'; box.replaceChildren(svg);
              const sil = [...svg.querySelectorAll('.ml-sil')];
              out[l + px] = [...new Set(sil.map(e => [getComputedStyle(e).stroke, Math.round(parseFloat(getComputedStyle(e).strokeWidth) * Math.hypot(e.getScreenCTM().a, e.getScreenCTM().b) * 1000) / 1000, getComputedStyle(e).strokeLinejoin].join(' ')))];
              if (l === 'magical' && px === 88) {
                const stroked = [...svg.querySelectorAll('*')].filter(e => !['svg', 'g'].includes(e.tagName) && getComputedStyle(e).stroke !== 'none');
                out.inner = [...new Set(stroked.filter(e => !e.classList.contains('ml-sil')).map(e => e.getAttribute('class') + ' ' + getComputedStyle(e).strokeWidth))];
                out.last = [...svg.querySelectorAll('.ml-m-line')].every(e => !e.nextElementSibling && getComputedStyle(e).fill === 'none');
                out.lines = svg.querySelectorAll('.ml-m-line').length;
              } }
            box.remove(); return out; }""")
        per = {k: v for k, v in ol.items() if k[-2:] in ("50", "64", "88")}
        check("one outline: every outlined edge in all three looks has the same colour, width and round joins, at 50, 64 and 88 px",
              all(len(v) == 1 for v in per.values()) and all(ol["futuristic" + s] == ol["magical" + s] == ol["grounded" + s] for s in ("50", "64", "88")), ol)
        check("Magical: each outline is drawn last in its group (nothing covers half of it), and the inner lines are all one thinner width",
              ol["last"] and ol["lines"] >= 20 and ol["inner"] == ["ml-crack 1.1px"], (ol["last"], ol["lines"], ol["inner"]))
        fly = page.evaluate("""() => [...document.querySelectorAll('.mentor-orbbox .ml-fly')].map(f => { const a = f.getAnimations()[0];
            return a ? [a.effect.getComputedTiming().duration, a.effect.getComputedTiming().iterations, a.effect.getTiming().delay] : null; })""")
        check("Magical: every loose fragment vibrates quickly (under 0.6 s a cycle, endless), each at its own pace",
              fly and all(f and f[0] < 600 and f[1] == float("inf") for f in fly) and len({(f[0], f[2]) for f in fly}) == len(fly), fly)
        page.evaluate("() => { settings.mentorLook = 'magical'; applyMentorLook(); }")
        check("Magical: the round button's fragments stay still", page.evaluate("() => [...document.querySelectorAll('#mentor-button .ml-fly')].every(f => f.getAnimations().length === 0)"))
        TAP = """() => { const s = document.querySelector('.mentor-orbbox svg');
            const anims = s.getAnimations({ subtree: true }).filter(a => (a.animationName || '').startsWith('ml-tap-'));
            return { tap: s.classList.contains('ml-tap'), names: anims.map(a => a.animationName), durs: [...new Set(anims.map(a => a.effect.getComputedTiming().duration))],
                     its: [...new Set(anims.map(a => a.effect.getComputedTiming().iterations))], picked: [...s.querySelectorAll('.ml-picked')].map(b => b.getAttribute('class')).sort().join(),
                     bolts: s.querySelectorAll('.ml-bolt').length, focus: document.activeElement && document.activeElement.className, open: !!document.querySelector('.mentor-window'),
                     msgs: document.querySelectorAll('.mentor-msg').length, mood: document.querySelector('.mentor-orbbox').dataset.mood }; }"""
        page.wait_for_function("() => document.querySelector('.mentor-orbbox').dataset.mood === 'neutral'", timeout=6000)
        page.focus(".mentor-input")
        before = page.evaluate(TAP)
        page.click(".mentor-orbbox")
        a = page.evaluate(TAP)
        check("Magical tap: the stone ring spins once (about 1.1 s), the text box keeps the focus, nothing is asked and the window stays open",
              a["tap"] and a["names"] == ["ml-tap-spin"] and all(900 <= d <= 1200 for d in a["durs"]) and a["its"] == [1]
              and "mentor-input" in (a["focus"] or "") and a["open"] and a["msgs"] == before["msgs"], a)
        page.click(".mentor-orbbox")
        check("a tap while the move plays is ignored (it does not start again)", len(page.evaluate(TAP)["names"]) == 1)
        page.wait_for_function("() => !document.querySelector('.mentor-orbbox svg.ml-tap')", timeout=3000)
        o2 = page.evaluate(ORBIT)
        check("after the spin the ring carries on its slow turn and the mood is unchanged", o2 and o2["dur"] >= 30000 and page.evaluate(TAP)["mood"] == "neutral", o2)
        picks = set()
        page.evaluate("() => { settings.mentorLook = 'futuristic'; applyMentorLook(); }")
        for _ in range(4):
            page.click(".mentor-orbbox")
            f = page.evaluate(TAP)
            picks.add(f["picked"])
            page.wait_for_function("() => !document.querySelector('.mentor-orbbox svg.ml-tap')", timeout=3000)
        check("Futuristic tap: four of its six bolts flash at once (0.3 to 0.4 s), picked at random each time",
              f["bolts"] >= 6 and f["picked"].count("ml-bolt") == 4 and f["names"] == ["ml-tap-zap"] * 4 and all(300 <= d <= 400 for d in f["durs"]) and len(picks) >= 2, (f, picks))
        page.evaluate("() => { settings.mentorLook = 'grounded'; applyMentorLook(); }")
        page.click(".mentor-orbbox")
        g = page.evaluate(TAP)
        check("Grounded tap: six paint drops fly out from the pool and fade (0.5 to 0.7 s)", g["names"] == ["ml-tap-drop"] * 6 and all(500 <= d <= 700 for d in g["durs"]), g)
        page.wait_for_function("() => !document.querySelector('.mentor-orbbox svg.ml-tap')", timeout=3000)
        check("the round button has no tap move", page.evaluate("() => !document.querySelector('#mentor-button .ml-tap, #mentor-button .ml-picked')"))
        page.keyboard.press("Escape")
        check("no page errors", not errors, errors[:3])
        ctx.close()

        print("\n--- 6. Reduced motion, and the moods at 50 px in greyscale ---")
        rm = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        rp = rm.new_page()
        t.load(rp, paints=[], settings={"examplesChecked": True, "mentorLook": "magical"}, launch=False)
        open_window(rp)
        check("reduced motion: nothing in the window orb moves (Magical's ring and fragments included)",
              rp.evaluate("() => document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).length") == 0)
        rp.click(".mentor-orbbox")
        check("reduced motion: a tap on the orb plays nothing and leaves nothing behind", rp.evaluate(
            "() => document.querySelector('.mentor-orbbox').getAnimations({ subtree: true }).length === 0 && !document.querySelector('.mentor-orbbox .ml-tap, .mentor-orbbox .ml-picked') && !!document.querySelector('.mentor-window')"))
        rp.keyboard.press("Escape")
        rp.evaluate("""() => { const box = document.createElement('div'); box.id = 'u7-sheet';
            box.style.cssText = 'position:fixed;left:0;top:0;z-index:999;display:flex;flex-wrap:wrap;width:300px;gap:4px;background:var(--background)';
            for (const l of ['futuristic', 'magical', 'grounded']) for (const s of ['neutral', 'thinking', 'pleased', 'unsure', 'finished']) {
              const cell = document.createElement('div'); cell.dataset.k = l + '-' + s; cell.style.cssText = 'width:50px;height:50px';
              const svg = minifolioLook.svg(l, s); svg.style.width = svg.style.height = '50px'; cell.appendChild(svg); box.appendChild(cell); }
            document.body.appendChild(box); }""")
        for look in LOOKS:
            imgs = {s: Image.open(io.BytesIO(rp.locator(f'#u7-sheet [data-k="{look}-{s}"]').screenshot())).convert("L") for s in STATES}
            worst = min((sum(1 for v in ImageChops.difference(imgs[a], imgs[b]).tobytes() if v > 10) / 2500, f"{a}-{b}") for a, b in itertools.combinations(STATES, 2))
            check(f"{look}: every pair of moods differs in at least 6% of pixels at 50 px, greyscale, motion off", worst[0] >= 0.06, worst)
        rm.close()
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
