"""Coach 1 tests for Minifolio: the colour engine (colour.js). Nothing is visible to users yet.

colour.js is the offline colour maths for the coming "Colour ideas" panel: paint colour to hue / saturation /
lightness, harmonies (opposite, neighbours, split-opposite, triad, neutrals), and the nearest-paint finder
(paints you own first, with an honest "how sure" label). It is NOT yet loaded by index.html or saved by sw.js:
Coach 2 wires it in (and does the version bump and Updates entry then), so today's app is byte-for-byte unchanged.

Checks:
1. The maths, in Node (tests/colour_engine_check.js): known colour values, the published CIEDE2000 test table,
   the pairs everyone knows (blue <-> orange), harmony angles, nearest paint (owned first, skips materials and the
   untouched grey, duplicates, rough metallic/Contrast paints, poor matches flagged), the real built-in catalogue,
   and a scan that the file never touches the network, storage or the page.
2. The same file in a real browser (Chromium) gives the same answers and adds exactly one name to the page.
3. The running app is untouched: index.html still has only its two script tags, and sw.js does not list colour.js yet.
Run all tests with `python3 tests/run_all.py`, or run this file on its own."""
import os, re, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, ".."))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

def main():
    print("--- 1. The maths, in Node ---")
    run = subprocess.run(["node", os.path.join(HERE, "colour_engine_check.js")], capture_output=True, text=True, cwd=ROOT)
    print(run.stdout.strip())
    check("every Node check passed", run.returncode == 0, (run.stdout + run.stderr)[-600:])

    print("\n--- 2. The same file in Chromium ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("about:blank")
        before = page.evaluate("() => Object.keys(window).length")
        page.add_script_tag(path=os.path.join(ROOT, "colour.js"))
        after = page.evaluate("() => Object.keys(window).length")
        check("colour.js adds exactly one name to the page", after == before + 1 and page.evaluate("() => typeof MinifolioColour") == "object", (before, after))
        out = page.evaluate("""() => {
            const C = MinifolioColour;
            const paints = [
              { brand: "T", name: "Navy", colour: "#1e3a8a", status: "owned" },
              { brand: "T", name: "Sky", colour: "#58c1cd" },
              { brand: "T", name: "Fire Orange", colour: "#f4874e", owned: true },
              { brand: "T", name: "Untouched", colour: "#808080" },
            ];
            return {
              comp: C.harmonies("#0000ff").complementary,
              family: C.colourFamily(C.harmonies("#2255cc").complementary),
              dist: C.labDistance({ L: 50, a: 2.5, b: 0 }, { L: 73, a: 25, b: -18 }),
              best: C.nearestPaints("#58c1cd", paints).map(e => [e.paint.name, e.owned, e.quality]),
              any: C.closestAny("#58c1cd", paints).paint.name,
              hsl: C.hexToHsl("#00ff00"),
            };
        }""")
        check("blue's opposite is yellow, a mid blue's is orange", out["comp"] == "#ffff00" and out["family"] == "orange", out)
        check("published CIEDE2000 pair gives 27.1492", abs(out["dist"] - 27.1492) < 0.0002, out["dist"])
        check("nearest paint: owned first, then by closeness; the untouched grey is skipped",
              out["best"] == [["Fire Orange", True, "poor"], ["Navy", True, "poor"], ["Sky", False, "good"]], out["best"])
        check("closestAny finds the exact paint", out["any"] == "Sky", out["any"])
        check("green is hue 120 in the browser too", abs(out["hsl"]["h"] - 120) < 0.5, out["hsl"])
        check("no page errors", not errors, errors[:3])
        browser.close()

    print("\n--- 3. The running app is untouched ---")
    html, sw = read("index.html"), read("sw.js")
    check("index.html has only its two script tags (early.js, app.js)",
          re.findall(r'<script src="([a-z]+)\.js', html) == ["early", "app"], re.findall(r'<script[^>]*>', html))
    check("sw.js does not list colour.js yet (Coach 2 adds it)", "colour.js" not in sw)
    check("app.js does not use the engine yet", "MinifolioColour" not in read("app.js"))

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
