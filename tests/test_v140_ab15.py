"""AB15 tests for Minifolio (Grim Forge's own structure). New behaviour only:
1. In Grim Forge, tags (chips and status tags) are square with one 4 px chamfer, and the keyboard ring on a chip sits inside the box.
2. In Grim Forge, the stage pips are square lamps (as wide as they are tall, no rounding), and the stage is still said in words.
3. In Grim Forge, the toast is a riveted plate: heavy border, square corners, rivets drawn, Undo still 44 px tall and clear of the rivets.
4. The other three looks keep their old computed styles for the same things (pill-less tags, bar pips, the plain snackbar).
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import wait_settled, _FINISH_BAR

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

def units():
    return [{"id": i, "name": f"Squad {i}", "hobby": "Skirmish", "stage": 2 + i, "count": 3, "added": "2026-10-01", "log": [["2026-10-01", 2 + i]]} for i in (1, 2, 3)]

def load(page, theme, mode):
    t.load(page, units=units(), recipes=t.RECIPES, settings={"tab": "units", "theme": theme, "appearance": mode})
    page.evaluate(_FINISH_BAR)
    wait_settled(page)

# What each thing computes to, in one go (a tag is made up in the page so the check does not depend on paint data).
PROBE = """() => {
  const host = document.querySelector('#unit-list');
  const mk = (tag, cls) => { const e = document.createElement(tag); e.className = cls; e.textContent = 'x'; host.after(e); return e; };
  const pill = mk('span', 'status-pill s-owned'), chip = document.querySelector('.chip') || mk('button', 'chip');
  const row = mk('div', 'review-row'), rtag = document.createElement('span'); rtag.className = 'tag'; rtag.textContent = 'x'; row.append(rtag);
  const pip = document.querySelector('.unit-sum .pip'), r = pip.getBoundingClientRect();
  const cs = (e) => getComputedStyle(e);
  const out = { chip: cs(chip).clipPath, pill: cs(pill).clipPath, rtag: cs(rtag).clipPath,
    pipW: r.width, pipH: r.height, pipRadius: cs(pip).borderTopLeftRadius, pipAspect: cs(pip).aspectRatio,
    stageWords: document.querySelector('.unit-sum .stage').textContent.trim().length > 0 };
  pill.remove(); row.remove();
  showToast('Squad 1 removed', () => {}, 'Undo', 30);
  const toast = document.getElementById('toast'), undo = document.getElementById('toast-undo') || toast.querySelector('button');
  const tc = cs(toast), tr = toast.getBoundingClientRect(), ur = undo.getBoundingClientRect();
  out.toast = { border: tc.borderTopWidth, radius: tc.borderTopLeftRadius, padLeft: tc.paddingLeft, layers: tc.backgroundImage.split('radial-gradient').length - 1,
    undoH: ur.height, undoGap: tr.right - ur.right, shadow: tc.boxShadow !== 'none' };
  return out;
}"""

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        for mode in ("dark", "light"):
            print(f"\n--- Grim Forge, {mode} ---")
            load(page, "forge", mode)
            r = page.evaluate(PROBE)
            check(f"{mode}: a chip has the 4 px chamfer", "calc(100% - 4px)" in r["chip"] and "100% 4px" in r["chip"], r["chip"])
            check(f"{mode}: a status tag and an import tag have it too", r["pill"] == r["chip"] != "none" and r["rtag"] == r["chip"], (r["pill"], r["rtag"]))
            check(f"{mode}: pips are square lamps with no rounding", abs(r["pipW"] - r["pipH"]) < 0.6 and r["pipH"] >= 5 and r["pipRadius"] == "0px", r)
            check(f"{mode}: the stage is still said in words", r["stageWords"])
            tt = r["toast"]
            check(f"{mode}: the toast is a plate (2 px border, square, four rivets, a hard shadow)", tt["border"] == "2px" and tt["radius"] == "0px" and tt["layers"] >= 4 and tt["shadow"], tt)
            check(f"{mode}: Undo is 44 px and stays clear of the rivets", tt["undoH"] >= 44 and tt["undoGap"] >= 16, tt)
            page.evaluate("() => hideToast()")
        page.keyboard.press("Shift")
        off = page.evaluate("""() => { const c = document.createElement('button'); c.className = 'chip'; c.textContent = 'x'; document.querySelector('#unit-list').after(c); c.focus(); return getComputedStyle(c).outlineOffset + ' ' + c.matches(':focus-visible'); }""")
        check("the keyboard ring on a chip sits inside the chamfered box", off.startswith("-4px") and off.endswith("true"), off)

        for theme in ("classic", "parchment", "bench"):
            print(f"\n--- {theme} is unchanged ---")
            load(page, theme, "dark")
            r = page.evaluate(PROBE)
            tt = r["toast"]
            check(f"{theme}: tags are not chamfered", r["chip"] == r["pill"] == r["rtag"] == "none", (r["chip"], r["pill"], r["rtag"]))
            check(f"{theme}: pips are still the thin bars", r["pipH"] <= 4.01 and r["pipW"] > 2 * r["pipH"] and r["pipAspect"] == "auto", r)
            check(f"{theme}: the toast is still the plain snackbar (no border, 14 px side padding, no rivets)", tt["border"] == "0px" and tt["padLeft"] == "14px" and tt["layers"] == 0, tt)
        check("no page errors", not errors, errors)
        browser.close()
    ok = all(results)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
