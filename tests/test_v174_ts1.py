"""TS1 tests for Minifolio: tap areas of the small controls the AR4 re-review measured too small. New behaviour only.
A tap area is measured the real way: scroll the control into view, then ask the browser what is under the corners and the middle of the
44 x 44 px square around the control (elementFromPoint). Every point must land on the control, or on the label or button that switches it.
That counts an enlarged ::after hit area (the Shopping pill, the version button) and a row's label (the tick boxes) as the tap area.
1. Header: the Shopping pill and the version button.
2. Shopping screen: Show shop links, the My shops ticks, the Bought tick and Remove on a row.
3. Import review (the same list the recipe paste uses): every tick box.
4. No sideways scroll on any of these screens, and neighbouring tap areas do not overlap.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from test_v83_shopping import P, WISH

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# For each control matching the selector: scroll it into view, then hit-test the middle and the four corners of the square
# (at least 44 x 44, or the control's own size when that is bigger) centred on it, pulled in 6 px from the edge (the corners of a button are rounded).
# Returns the points that landed on something else, and the owner's size.
HIT = """(sel) => {
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    if (!el.getClientRects().length) continue;
    el.scrollIntoView({block: "center"});
    const r = el.getBoundingClientRect();
    const owner = el.closest("label, button") || el;
    const w = Math.max(r.width, 44) / 2 - 6, h = Math.max(r.height, 44) / 2 - 6;
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const bad = [];
    for (const [dx, dy] of [[0, 0], [-w, -h], [w, -h], [-w, h], [w, h]]) {
      const hit = document.elementFromPoint(cx + dx, cy + dy);
      if (!hit || !(el.contains(hit) || owner.contains(hit))) bad.push([Math.round(dx), Math.round(dy), hit ? hit.tagName + "." + hit.className : "none"]);
    }
    out.push({text: (owner.textContent || el.id || "").trim().slice(0, 24), bad});
  }
  return out;
}"""
SIDEWAYS = "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
# the tap areas of two neighbours must not share a point: for each control, the owner rectangles of all the matching controls are pairwise apart
OVERLAP = """(sel) => { const rs = [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length).map(e => (e.closest("label, button") || e).getBoundingClientRect());
  let n = 0; for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) { const a = rs[i], b = rs[j];
    if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) n++; } return n; }"""

PAINTS = [P(1, "Alpha Blue", **WISH), P(2, "Beta Red", **WISH), P(3, "Zeta With A Rather Long Paint Name Indeed", **WISH)]
ARMY = "My list (500 points)\n\nOrks\n\nBoyz (85 points)\n  • 10x Boy\n\nGretchin (40 points)\n  • 10x Gretchin\n"

def short(found):
    return [f"{x['text']}: {x['bad']}" for x in found if x["bad"]][:3]

def run_look(page, tag):
    """Everything on one page load: header, Shopping screen, import review."""
    head = page.evaluate(HIT, "#basket-button") + page.evaluate(HIT, "#version-tag")
    check(f"{tag}: the Shopping pill and the version button have a 44 px tap area", len(head) == 2 and not short(head), short(head) or head)
    page.evaluate("() => openShopping()")
    page.wait_for_timeout(250)
    page.wait_for_selector("#shop-panel .shop-tick")
    ticks = page.evaluate(HIT, "#shop-links-switch, .my-shop input")
    check(f"{tag}: Show shop links and the My shops ticks (5 boxes) have a 44 px tap area", len(ticks) == 5 and not short(ticks), short(ticks) or len(ticks))
    rows = page.evaluate(HIT, "#shop-panel .shop-tick, #shop-panel .shop-remove")
    check(f"{tag}: the Bought tick and Remove on every row have a 44 px tap area", len(rows) >= 6 and not short(rows), short(rows) or len(rows))
    check(f"{tag}: no two shopping tap areas overlap", page.evaluate(OVERLAP, ".my-shop input, #shop-links-switch") == 0 and page.evaluate(OVERLAP, "#shop-panel .shop-tick, #shop-panel .shop-remove") == 0)
    check(f"{tag}: no sideways scroll on Shopping", not page.evaluate(SIDEWAYS))
    # the army-list import review (Models > Add > army list); its ticks are the "import" ticks
    page.evaluate("() => { const d = document.activeElement; if (d && d.blur) d.blur(); }")
    page.click('nav button[data-tab="units"]')
    page.wait_for_timeout(300)
    page.click("#toggle-add")
    page.click("#add-wh")
    page.fill("#wh-text", ARMY)
    page.click("#wh-read")
    page.wait_for_selector("#review:not(.hidden)")
    page.wait_for_timeout(300)
    imp = page.evaluate(HIT, "#review-list .review-row input[type=checkbox]")
    check(f"{tag}: the import review ticks have a 44 px tap area", len(imp) >= 2 and not short(imp), short(imp) or len(imp))
    check(f"{tag}: import review ticks do not overlap, no sideways scroll", page.evaluate(OVERLAP, "#review-list .review-row input[type=checkbox]") == 0 and not page.evaluate(SIDEWAYS))

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # four looks at 390 dark; then 360 and 320 on Classic; then light at 390 and 360
        plan = [("390", "dark", th) for th in ("classic", "parchment", "forge", "bench")] + [("360", "dark", "classic"), ("320", "dark", "classic"), ("390", "light", "classic"), ("360", "light", "parchment")]
        for width, scheme, theme in plan:
            ctx = browser.new_context(viewport={"width": int(width), "height": 800}, service_workers="block", color_scheme=scheme, reduced_motion="reduce")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, paints=PAINTS, recipes=[t.rec(1, "Blue", "Armour", [1, 2])], settings={"examplesChecked": True, "theme": theme})
            print(f"\n--- {width} px, {scheme}, {theme} ---")
            run_look(page, f"{width} {scheme} {theme}")
            ctx.close()
        check("no page errors", not errors, errors)
        browser.close()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
