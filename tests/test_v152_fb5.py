"""FB5 tests for Minifolio (the version button is on the start circle too). New behaviour only: the text, the place (same as on the other
screens), one tap to Updates and Back to the circle, and no overlap or sideways scroll at three phone sizes, dark and light, Classic and Forge,
with and without the loading ring."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import launch_helpers as lh
import version_helpers as vh

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

SIZES = [(390, 844), (360, 640), (320, 568)]
# the basket is shown with a wide count (worst case), then every box that must stay clear of the number is measured
GEOM = """() => { const b = document.getElementById('basket-button'); b.classList.remove('hidden'); b.textContent = '88';
  const box = e => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom }; };
  const v = document.getElementById('version-tag'), vr = box(v), cx = (vr.l + vr.r) / 2, cy = (vr.t + vr.b) / 2;
  const tap = { l: cx - 22, r: cx + 22, t: cy - 22, b: cy + 22 };   // the ::after hit area is 44 x 44 around the text
  const others = [...document.querySelectorAll('.arc [data-tab], #mentor-button, .mo-load, .mo-ring')].filter(e => e.getClientRects().length).map(box);
  return { text: v.textContent, shown: getComputedStyle(v).display !== 'none', v: vr, tap, home: box(document.getElementById('home-button')), basket: box(b), others,
    sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth }; }"""

def hit(a, b):
    return a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]

def clear_of_everything(g):
    return (not hit(g["v"], g["home"]) and not hit(g["v"], g["basket"]) and g["v"]["r"] <= g["basket"]["l"] - 4
            and not any(hit(g["tap"], o) for o in g["others"]) and not g["sideways"])

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        print("\n--- 1. Text, place, no overlap: three sizes, dark and light, Classic and Forge ---")
        for (w, h) in SIZES:
            for scheme, look in [("dark", "classic"), ("light", "classic")] + ([("dark", "forge")] if w != 360 else []):
                ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block", color_scheme=scheme)
                page = ctx.new_page()
                page.on("pageerror", lambda x: errors.append(str(x)))
                t.load(page, units=[], launch=True, settings={"theme": look, "examplesChecked": True} if look != "classic" else None)
                tag = f"{w}x{h} {scheme} {look}"
                g = page.evaluate(GEOM)
                check(f"{tag}: shown, says the app's version, clear of wedges, Mentor, basket and title, no sideways scroll",
                      g["shown"] and g["text"] == vh.current() and clear_of_everything(g), g)
                if look == "classic" and scheme == "dark":
                    page.evaluate("() => document.querySelector('.tabs button[data-tab=\"dashboard\"]').click()")
                    lh.wait_settled(page)
                    page.evaluate("async () => { await document.fonts.ready; }")
                    d = page.evaluate(GEOM)
                    same = all(abs(g["v"][k] - d["v"][k]) <= 2 for k in ("l", "r", "t", "b"))
                    check(f"{tag}: same top and left/right as on the Dashboard (within 2 px)", same, (g["v"], d["v"]))
                ctx.close()

        print("\n--- 2. While the loading ring shows ---")
        for (w, h) in [SIZES[0], SIZES[2]]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page()
            t.load(page, units=[], launch=True)
            page.reload()
            try:
                page.wait_for_function("() => document.querySelector('.mo-load') && document.getElementById('version-tag').textContent", timeout=8000)
                g = page.evaluate(GEOM)
                check(f"{w}x{h}: with the ring drawn, the number is clear of it and of the Mentor button", g["shown"] and any(True for _ in g["others"]) and clear_of_everything(g), g)
            except Exception as e:
                check(f"{w}x{h}: the ring was caught on screen", False, str(e)[:120])
            ctx.close()

        print("\n--- 3. One tap opens Updates; Back returns to the start circle ---")
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, units=[], launch=True)
        check("the circle is showing", lh.is_launching(page))
        page.click("#version-tag")
        page.wait_for_function("() => settings.tab === 'updates' && !document.body.classList.contains('launching')")
        lh.wait_settled(page)
        on = page.evaluate("() => ({ updates: !document.getElementById('view-updates').classList.contains('hidden'), seg: document.querySelector('#more-seg [aria-selected=true]').dataset.page })")
        check("one tap opens Updates inside Tools", on["updates"] and on["seg"] == "updates", on)
        page.evaluate("() => history.back()")
        page.wait_for_function("() => document.body.classList.contains('launching')")
        check("Back returns to the start circle", lh.is_launching(page))
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)} / {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
