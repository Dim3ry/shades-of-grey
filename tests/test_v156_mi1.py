"""MI1 test for Minifolio (the four menu icons: bars, hex base, palette, book). New behaviour only."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import _FINISH_BAR

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

SHAPES = {
    "dashboard": ('<rect x="4" y="12.5" width="4" height="7.5" rx="1"/><rect x="10" y="8" width="4" height="12" rx="1"/>'
                  '<rect x="16" y="4" width="4" height="16" rx="1"/>'),
    "units": '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><circle cx="12" cy="12" r="3"/>',
    "recipes": "M12 3.5a8.5 8.5 0 1 0 0 17",
    "guides": '<path d="M3 5.5c3-1 6-.8 9 1 3-1.8 6-2 9-1V19c-3-1-6-.8-9 1-3-1.8-6-2-9-1z"/><path d="M12 6.5V20"/>',
}
NAMES = {"dashboard": "Dashboard", "units": "Models", "recipes": "Painting", "guides": "Tools"}
INFO = """() => Object.fromEntries([...document.querySelectorAll('.arc > [data-tab]')].map(b => {
    const s = b.querySelector('.icon svg'), r = s.getBoundingClientRect(), br = b.getBoundingClientRect(), cs = getComputedStyle(s);
    return [b.dataset.tab, { html: s.innerHTML.replace(/><\/(rect|path|circle)>/g, '/>'), name: b.getAttribute('aria-label') || b.textContent.trim(), hidden: s.getAttribute('aria-hidden'),
        fill: cs.fill, stroke: cs.stroke, sw: cs.strokeWidth, cap: cs.strokeLinecap, w: r.width, h: r.height, color: getComputedStyle(b.querySelector('.icon')).color,
        inside: r.left >= br.left - 0.5 && r.right <= br.right + 0.5 && r.top >= br.top - 0.5 && r.bottom <= br.bottom + 0.5 }];
  }))"""

def main():
    errors = []
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"), encoding="utf-8").read()
    check("each drawing is in the page once (one shared place)", all(src.count(v) == 1 for v in SHAPES.values()))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, launch=True)
        info = page.evaluate(INFO)
        check("each segment draws its new shape", all(SHAPES[s] in info[s]["html"] for s in NAMES), {s: info[s]["html"][:60] for s in NAMES})
        check("names are kept and the icon is hidden from screen readers",
              all(info[s]["name"] == NAMES[s] and info[s]["hidden"] == "true" for s in NAMES), info)
        check("no fill, stroke 1.6, round caps, square box, same size for all",
              all(info[s]["fill"] == "none" and info[s]["sw"] == "1.6px" and info[s]["cap"] == "round" and abs(info[s]["w"] - info["units"]["w"]) < 0.5 and abs(info[s]["h"] - info[s]["w"]) < 0.5 for s in NAMES), info)
        check("icons sit whole in the start circle", all(info[s]["inside"] for s in NAMES), info)

        print("\n--- bar, selected state, copies ---")
        for w, h, mode in ((390, 844, "dark"), (360, 640, "light")):
            page.set_viewport_size({"width": w, "height": h})
            t.load(page, settings={"appearance": mode}, launch=True)
            page.evaluate("() => document.querySelector('.tabs button[data-tab=recipes]').click()")
            page.evaluate(_FINISH_BAR)
            b = page.evaluate(INFO)
            sel = page.evaluate("() => getComputedStyle(document.querySelector('.arc [data-tab][aria-current=page] .icon svg')).strokeWidth")
            check(f"{w}x{h} {mode}: whole in the bar, the lit one is heavier, colour follows text",
                  all(b[s]["inside"] and SHAPES[s] in b[s]["html"] and b[s]["stroke"] != "none" for s in NAMES) and sel == "2.4px", (b, sel))
        page.set_viewport_size({"width": 390, "height": 844})
        t.load(page, launch=True)
        page.evaluate("() => document.querySelector('.tabs button[data-tab=units]').click()")
        page.wait_for_selector(".mo-tr svg", state="attached", timeout=5000)
        copies = page.evaluate("() => [...document.querySelectorAll('.mo-tr svg')].map(s => s.innerHTML.replace(/><\\/(rect|path|circle)>/g, '/>'))")
        check("travelling copies use the same four drawings", len(copies) == 4 and all(any(SHAPES[s] in c for c in copies) for s in NAMES), copies)
        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
