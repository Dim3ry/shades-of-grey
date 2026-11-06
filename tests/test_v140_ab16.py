"""AB16 tests for Minifolio (Paint Bench's own structure). New behaviour only:
1. In Bench the status tags and the chips are strips of masking tape (tape background, ink text, clear contrast).
2. In Bench the stage pips are pencil ticks (slanted strokes, a filled one longer and thicker than an empty one).
3. In Bench the headline card has a tape label stuck over its top edge, clear of the text.
4. In Bench the toast is a strip of tape, and Undo is still 44 px tall.
5. The other three looks are unchanged in computed styles (no clip-path, no tape label).
6. Nothing sideways at 390, 360 and 320 px wide, dark and light.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def lum(c):
    r, g, b = [int(x) for x in re.findall(r"\d+", c)[:3]]
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def open_look(page, theme, appearance):
    t.load(page, units=t.UNITS, recipes=t.RECIPES, settings={"theme": theme, "appearance": appearance})

def probe(page):
    """Reads the Dashboard (headline card) first, then Models (chips, pips): the two live on different pages."""
    page.click('nav button[data-tab="dashboard"]')
    page.wait_for_selector("#headline-card", state="visible")
    a = page.evaluate(PROBE)
    page.click('nav button[data-tab="units"]')
    page.wait_for_selector(".pip", state="attached")
    b = page.evaluate(PROBE)
    a.update({k: v for k, v in b.items() if k.startswith(("chip", "pip"))})
    return a

def sw(v, what="polygon"):
    return isinstance(v, str) and v.startswith(what)

PROBE = """() => {
  const q = s => document.querySelector(s);
  const cs = (e, p) => e ? getComputedStyle(e)[p] : null;
  const chip = q(".chip");
  const pips = [...document.querySelectorAll('.pip')];
  const pf = pips.find(p => p.classList.contains('filled')), pe = pips.find(p => !p.classList.contains('filled') && !p.classList.contains('part'));
  const head = q('#headline-card');
  const host = document.createElement('div'); host.className = 'review-row clash';
  host.innerHTML = '<label><span class="tag">possible match</span></label>'; document.body.append(host);
  const tag = host.querySelector('.tag');
  const out = { chipClip: cs(chip, 'clipPath'), chipBg: cs(chip, 'backgroundImage'), chipColour: cs(chip, 'color'),
    pipFilledClip: cs(pf, 'clipPath'), pipEmptyClip: cs(pe, 'clipPath'), pipH: cs(pf, 'height'),
    headBefore: head ? getComputedStyle(head, '::before').content : null, headBeforeW: head ? getComputedStyle(head, '::before').width : null,
    tagClip: cs(tag, 'clipPath'), tagColour: cs(tag, 'color'), tagBgImg: cs(tag, 'backgroundImage'),
    sideways: document.documentElement.scrollWidth > innerWidth + 1 };
  host.remove();
  return out;
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 1 to 3. Bench: tape tags and chips, pencil ticks, tape label ---")
        for appearance in ("dark", "light"):
            open_look(page, "bench", appearance)
            r = probe(page)
            check(f"Bench {appearance}: the tag is a tape strip (torn ends, tape texture)", sw(r["tagClip"]) and "gradient" in r["tagBgImg"], r)
            check(f"Bench {appearance}: tag text is ink on tape at 4.5 to 1 or more", ratio(r["tagColour"], "rgb(228, 217, 182)") >= 4.5, r["tagColour"])
            check(f"Bench {appearance}: the chips are tape (texture, ink text, 4.5 to 1)", "gradient" in r["chipBg"] and ratio(r["chipColour"], "rgb(205, 187, 124)") >= 4.5, r)
            check(f"Bench {appearance}: filled and empty pips are both slanted strokes", sw(r["pipFilledClip"]) and sw(r["pipEmptyClip"]), r)
            check(f"Bench {appearance}: a filled tick is a taller stroke than an empty one", r["pipFilledClip"] != r["pipEmptyClip"] and "36%" in r["pipEmptyClip"] and "36%" not in r["pipFilledClip"], r)
            check(f"Bench {appearance}: the headline card has a tape label (a box, not text)", r["headBefore"] not in (None, "none", "normal") and r["headBeforeW"] == "64px", r)
            check(f"Bench {appearance}: no sideways scroll", not r["sideways"], r)
        pressed = page.evaluate("() => { const c = [...document.querySelectorAll('.chip')].find(c => c.getAttribute('aria-pressed') === 'true'); return c ? [getComputedStyle(c).fontWeight, getComputedStyle(c).boxShadow] : null; }")
        check("Bench: a chosen chip shows by weight and a bar under it, not colour alone", pressed is None or (int(pressed[0]) >= 700 and pressed[1] != "none"), pressed)

        print("\n--- The tape label stays clear of the headline text ---")
        gap = page.evaluate("""() => { const h = document.querySelector('#headline-card'), b = h.querySelector('.headline'), r = h.getBoundingClientRect(), tr = b.getBoundingClientRect();
            return tr.top - (r.top + 8); }""")
        check("the label reaches 8 px into the card and the text starts below that", gap >= 0, gap)

        print("\n--- 4. Bench: the toast is a strip of tape; Undo is 44 px ---")
        for appearance in ("dark", "light"):
            open_look(page, "bench", appearance)
            page.evaluate("() => { const t = document.getElementById('toast'); document.getElementById('toast-text').textContent = 'Moved to Primed'; t.classList.remove('hidden'); }")
            page.wait_for_function("() => getComputedStyle(document.getElementById('toast')).opacity === '1'")
            r = page.evaluate("""() => { const t = document.getElementById('toast'), u = document.getElementById('toast-undo'), c = getComputedStyle(t);
                return { clip: c.clipPath, bg: c.backgroundImage, colour: c.color, undoH: u.getBoundingClientRect().height, undoColour: getComputedStyle(u).color, undoText: u.textContent }; }""")
            check(f"Bench {appearance}: the toast is tape (torn ends, texture, ink text)", r["clip"].startswith("polygon") and "gradient" in r["bg"] and ratio(r["colour"], "rgb(228, 217, 182)") >= 4.5, r)
            check(f"Bench {appearance}: Undo is at least 44 px tall and keeps its word", r["undoH"] >= 43.9 and r["undoText"] == "Undo", r)
            check(f"Bench {appearance}: Undo text is 4.5 to 1 on the tape", ratio(r["undoColour"], "rgb(228, 217, 182)") >= 4.5, r["undoColour"])

        print("\n--- 5. Classic is unchanged; Parchment and Forge do not carry Bench's features, and Bench carries none of theirs ---")
        # Bench's own values, read once, so the other looks can be compared against exactly what Bench draws.
        open_look(page, "bench", "dark")
        bench = probe(page)
        page.evaluate("() => document.getElementById('toast').classList.remove('hidden')")
        bt = page.evaluate("() => { const c = getComputedStyle(document.getElementById('toast')); return [c.clipPath, c.rotate, c.backgroundImage, c.borderTopWidth, document.getElementById('toast').className]; }")
        bpip = page.evaluate("() => { const c = getComputedStyle(document.querySelector('.pip')); return [c.borderTopWidth, c.aspectRatio]; }")
        check("Bench carries none of Forge's or Parchment's: no chamfer, no lamp pips, no paper-slip border, no rivet plate (the toast-slip class is on every look's toast; only its Parchment rules draw the slip)",
              "4px" not in bench["tagClip"] and bpip[0] == "0px" and "url" not in bt[2] and bt[3] == "0px" and bt[0].startswith("polygon") and "calc" not in bt[0], (bench["tagClip"], bpip, bt))
        for theme in ("classic", "parchment", "forge"):
            for appearance in ("dark", "light"):
                open_look(page, theme, appearance)
                r = probe(page)
                page.evaluate("() => document.getElementById('toast').classList.remove('hidden')")
                toast = page.evaluate("() => { const c = getComputedStyle(document.getElementById('toast')); return [c.clipPath, c.rotate, c.backgroundImage]; }")
                if theme == "classic":
                    # No chunk of AB14, AB15 or AB16 touches Classic: every computed style here stays strictly as before.
                    same = (r["chipClip"] == "none" and r["pipFilledClip"] == "none" and r["pipEmptyClip"] == "none" and r["tagClip"] == "none"
                            and r["headBefore"] in ("none", "normal") and toast[:2] == ["none", "none"])
                    check(f"classic {appearance}: no clip on chips, tags, pips, toast, and no label on the headline card", same, (r, toast))
                else:
                    # AB14 (Parchment) and AB15 (Forge) restyle their own chips, tags, pips and toast on purpose (Forge's 4 px chamfer clip, for one),
                    # so "no clip at all" no longer holds. What must hold: none of Bench's features appear here.
                    ok = (r["tagClip"] != bench["tagClip"] and r["pipFilledClip"] != bench["pipFilledClip"] and r["pipEmptyClip"] != bench["pipEmptyClip"]
                          and r["headBefore"] in ("none", "normal") and toast[0] != bt[0] and toast[1] == "none" and toast[2] != bt[2])
                    check(f"{theme} {appearance}: none of Bench's tape tags, ticks, tape label or tape toast (torn-end clips, tilt, tape texture)", ok, (r, toast, bt))

        print("\n--- 6. Small phones, dark and light ---")
        for w, h in ((360, 640), (320, 568)):
            ctx2 = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            pg = ctx2.new_page()
            for appearance in ("dark", "light"):
                open_look(pg, "bench", appearance)
                r = probe(pg)
                check(f"Bench {w} px {appearance}: no sideways scroll", not r["sideways"], r)
            ctx2.close()
        check("no script errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
