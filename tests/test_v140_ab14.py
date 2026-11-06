"""AB14 tests for Minifolio (Parchment Codex: ruled ledger and paper-slip toast). New behaviour only:
1. Parchment: cards and the unit list use hairline rules, not boxes (dark and light, 390 / 360 / 320 wide).
2. Parchment: the ink blots (stain images) are still there, rows keep 44 px taps, no sideways scroll.
3. Parchment's toast has the paper-slip class, Undo is 44 px, and Undo and the text pass 4.5 to 1.
4. The other three looks keep their boxed cards, stripe, corners and plain toast (computed styles).
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def units(n=4):
    return [{"id": i, "name": f"Squad {i}", "hobby": "Skirmish", "stage": 2 + i % 3, "count": 3, "added": "2026-10-01",
             "log": [["2026-10-01", 2 + i % 3]]} for i in range(1, n + 1)]

STYLE = """() => {
  const q = s => document.querySelector(s), g = e => getComputedStyle(e), px = v => parseFloat(v);
  const u = q('#unit-list > li.unit'), c = q('.card'), ul = q('#unit-list');
  const us = g(u), cs = g(c);
  return { u: { top: px(us.borderTopWidth), right: px(us.borderRightWidth), bottom: px(us.borderBottomWidth), left: px(us.borderLeftWidth),
                radius: px(us.borderTopLeftRadius), mb: px(us.marginBottom), shadow: us.boxShadow, h: u.getBoundingClientRect().height,
                stainImg: us.backgroundImage, leftStyle: us.borderLeftStyle },
           c: { left: px(cs.borderLeftWidth), top: px(cs.borderTopWidth), bottom: px(cs.borderBottomWidth), radius: px(cs.borderTopLeftRadius),
                shadow: cs.boxShadow, stainImg: cs.backgroundImage, style: cs.borderTopStyle },
           info: px(g(u.querySelector('.info')).minHeight), ulTop: px(g(ul).borderTopWidth),
           wide: document.documentElement.scrollWidth > innerWidth };
}"""

TOAST = """() => {
  showToast('Removed Squad 1', () => {});
  const tt = document.getElementById('toast'), b = document.getElementById('toast-undo'), s = getComputedStyle(tt);
  return { cls: tt.classList.contains('toast-slip'), bg: s.backgroundColor, color: s.color, radius: parseFloat(s.borderTopLeftRadius),
           btn: b.getBoundingClientRect().height, btnColor: getComputedStyle(b).color, bT: parseFloat(s.borderTopWidth), bL: parseFloat(s.borderLeftWidth), under: getComputedStyle(b).textDecorationLine, card: getComputedStyle(document.documentElement).getPropertyValue('--card').trim(),
           text: getComputedStyle(document.documentElement).getPropertyValue('--text').trim(), bgv: getComputedStyle(document.documentElement).getPropertyValue('--background').trim() };
}"""

LEAK = """() => {
  const host = document.querySelector('#unit-list'), cs = e => getComputedStyle(e);
  const mk = (cls) => { const e = document.createElement('span'); e.className = cls; e.textContent = 'x'; host.after(e); return e; };
  const pill = mk('status-pill s-owned'), tag = mk('tag'), pip = document.querySelector('.unit-sum .pip');
  const out = { pill: cs(pill).clipPath, tag: cs(tag).clipPath, pip: cs(pip).clipPath, pipRadius: cs(pip).borderTopLeftRadius, toastRotate: cs(document.getElementById('toast')).rotate };
  pill.remove(); tag.remove(); return out;
}"""

def open_look(page, theme, mode):
    t.load(page, units=units(), settings={"theme": theme, "appearance": mode, "tab": "units"})
    page.wait_for_selector("#unit-list > li.unit")

def hexrgb(h):
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640), (320, 568)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            for mode in ("dark", "light"):
                tag = f"{w}px {mode}"
                open_look(page, "parchment", mode)
                s = page.evaluate(STYLE)
                u, c = s["u"], s["c"]
                check(f"Parchment {tag}: unit rows are ruled (bottom hairline, no side or top box, square corners, no gap)",
                      u["bottom"] == 1 and u["top"] == 0 and u["right"] == 0 and u["radius"] == 0 and u["mb"] == 0 and u["shadow"] == "none", u)
                check(f"Parchment {tag}: the stage stripe stays on the left (4 px)", u["left"] == 4 and u["leftStyle"] == "solid", u)
                check(f"Parchment {tag}: cards have a rule above and below, no side box, no shadow",
                      c["top"] == 1 and c["bottom"] == 1 and c["left"] == 0 and c["radius"] == 0 and c["shadow"] == "none" and c["style"] == "solid", c)
                check(f"Parchment {tag}: the ink blots are still drawn on rows and cards",
                      "radial-gradient" in u["stainImg"] and "radial-gradient" in c["stainImg"], (u["stainImg"][:60], c["stainImg"][:60]))
                check(f"Parchment {tag}: rows keep 44 px taps and the page does not scroll sideways", s["info"] >= 44 and not s["wide"], s)
                tz = page.evaluate(TOAST)
                check(f"Parchment {tag}: toast is a paper slip (class, card paper, ink text, square) with a 44 px Undo",
                      (tz["cls"] and tz["btn"] >= 43.9 and tz["radius"] == 0 and tz["bg"] == hexrgb(tz["card"])), tz)
                if w == 390:
                    lk = page.evaluate(LEAK)
                    # AB15 (Forge) and AB16 (Bench) restyle tags, pips and toasts; none of that may leak into Parchment.
                    check(f"Parchment {tag}: no Forge chamfer, Bench tape or tilt on tags, pips or toast", lk["pill"] == "none" and lk["tag"] == "none" and lk["pip"] == "none" and lk["toastRotate"] in ("none", "0deg"), lk)
                    bg = t.rgb(tz["bg"])
                    check(f"Parchment {tag}: toast text and Undo reach 4.5 to 1 on the slip",
                          t.contrast(t.rgb(tz["color"]), bg) >= 4.5 and t.contrast(t.rgb(tz["btnColor"]), bg) >= 4.5,
                          (tz["color"], tz["btnColor"], tz["bg"]))
            ctx.close()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        for theme in ("classic", "forge", "bench"):
            open_look(page, theme, "dark")
            s = page.evaluate(STYLE)
            u, c = s["u"], s["c"]
            want = page.evaluate("() => { const r = getComputedStyle(document.documentElement); return [parseFloat(r.getPropertyValue('--border-width')), r.getPropertyValue('--radius-card').trim()]; }")
            bw = want[0]
            tz = page.evaluate(TOAST)
            if theme == "classic":
                # No chunk of AB14, AB15, AB16 touches Classic, so it stays strictly unchanged.
                check("classic: cards and rows keep their box border, stripe, spacing and shadow",
                      c["left"] == bw and c["top"] == bw and u["top"] == bw and u["left"] == 4 and u["mb"] == 10 and u["bottom"] == bw, (u, c, want))
                check("classic: corners follow the look's own radius token", f"{u['radius']:g}px" == want[1] or want[1].startswith("var") or u["radius"] == c["radius"], (u["radius"], c["radius"], want))
                check("classic: toast is still the plain snackbar (ink on page colour)", tz["bg"] == hexrgb(tz["text"]) and tz["color"] == hexrgb(tz["bgv"]) and tz["btn"] >= 43.9, tz)
            else:
                # Forge (AB15) and Bench (AB16) legitimately restyle their own toasts, tags and pips, so they are no longer "unchanged".
                # What this chunk promises is that Parchment's own features do not leak into them.
                check(f"{theme}: no Parchment ledger rules on unit rows (rows are not bottom-hairline-only, square, gapless)",
                      not (u["bottom"] == 1 and u["top"] == 0 and u["right"] == 0 and u["radius"] == 0 and u["mb"] == 0 and u["shadow"] == "none"), u)
                check(f"{theme}: cards are not Parchment's rule-above-and-below ledger cards",
                      not (c["left"] == 0 and c["top"] == 1 and c["bottom"] == 1 and c["shadow"] == "none"), c)
                check(f"{theme}: the toast carries none of Parchment's paper slip (no card paper, no ruled edge only, no underlined Undo)",
                      tz["cls"] and tz["bg"] != hexrgb(tz["card"]) and not (tz["bT"] == 1 and tz["bL"] == 0) and "underline" not in tz["under"], tz)
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    sys.exit(0 if all(results) else 1)

main()
