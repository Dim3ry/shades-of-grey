"""AB5 tests: corners follow the look, and Classic's corner marks sit on the headline card and the Mentor window only.
1. No listed rule keeps a literal pill or 12 to 22 px corner: chips, status tags, Mentor window and bubbles use the look's radius.
2. Forge's control radius is square and Parchment's is 2 px, on real chips, the Mentor input and Send.
3. In Classic only #headline-card and the open Mentor window draw corner marks; other cards are a plain 1 px line.
4. The Classic theme button in Settings still shows the marks."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import leave_launch, open_settings, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def fresh(page, theme, mode="dark"):
    page.goto(t.BASE + "manifest.json")
    page.evaluate("(s) => { localStorage.clear(); localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }", {"theme": theme, "appearance": mode})
    page.goto(t.URL)
    page.wait_for_function("() => typeof settings === 'object'")
    leave_launch(page)

def radius(page, sel):
    return page.evaluate("(s) => { const e = document.querySelector(s); return e ? getComputedStyle(e).borderTopLeftRadius : null; }", sel)

def main():
    errors = []
    html = t.read("index.html")
    print("\n--- 1. No literal pill corners in the listed rules ---")
    sels = [".chips > .chip", ".chips.chips-tall > .chip", ".chips.chips-wrap > .chip", ".chip", ".review-row .tag", ".recipe-chip", ".linked .recipe-chip", ".linked .unlink",
            ".status-pill", ".start-swatches > .start-swatch", ".mentor-window", ".mentor-chip", ".mentor-input", ".mentor-send", ".mentor-me p", ".mentor-source", ".mentor-close", ".mentor-back", ".mentor-suggest"]
    bad = []
    for s in sels:
        for m in re.finditer(r"(?m)^\s*" + re.escape(s) + r"\s*\{([^}]*)\}", html):
            body = m.group(1)
            for rad in re.findall(r"border-radius:\s*([^;]*);", body):
                if re.search(r"\b(999|22|18|14|12)px", rad): bad.append((s, rad))
    check("listed rules no longer carry 999, 22, 18, 14 or 12 px corners", not bad, bad)
    check("the Mentor window takes the card radius and its input and Send the control radius",
          re.search(r"\.mentor-window \{[^}]*border-radius: var\(--radius-card\)", html) and re.search(r"\.mentor-input \{[^}]*border-radius: var\(--radius-control\)", html)
          and re.search(r"\.mentor-send \{[^}]*border-radius: var\(--radius-control\)", html))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        print("\n--- 2. Forge is square, Parchment is 2 px ---")
        for theme, want in (("forge", "0px"), ("parchment", "2px")):
            fresh(page, theme)
            chip = page.evaluate("() => { const e = document.querySelector('.chip'); return e ? getComputedStyle(e).borderTopLeftRadius : null; }")
            check(f"{theme}: a chip's corners are {want}", chip == want, chip)
            page.click("#mentor-button")
            page.wait_for_selector(".mentor-window", state="visible")
            win, inp, send = radius(page, ".mentor-window"), radius(page, ".mentor-input"), radius(page, ".mentor-send")
            check(f"{theme}: the Mentor window, input and Send are {want}", win == inp == send == want, (win, inp, send))

        print("\n--- 3. Classic: marks on the headline card and the Mentor window only ---")
        for mode in ("dark", "light"):
            fresh(page, "classic", mode)
            marks = page.evaluate("""() => [...document.querySelectorAll('#view-dashboard .card')].map(e => [e.id, getComputedStyle(e).backgroundImage.split('linear-gradient').length - 1])""")
            head = [n for i, n in marks if i == "headline-card"]
            others = [n for i, n in marks if i != "headline-card"]
            check(f"classic {mode}: the headline card has eight corner strokes", head == [8], marks)
            check(f"classic {mode}: every other card on the page has none", others and all(n == 0 for n in others), marks)
            page.click("#mentor-button")
            page.wait_for_selector(".mentor-window", state="visible")
            n = page.evaluate("() => getComputedStyle(document.querySelector('.mentor-window')).backgroundImage.split('linear-gradient').length - 1")
            check(f"classic {mode}: the Mentor window has eight corner strokes", n == 8, n)

        print("\n--- 4. The Classic theme button still previews the marks ---")
        fresh(page, "forge")
        open_settings(page)
        n = page.evaluate("() => getComputedStyle(document.querySelector('.theme-swatch[data-t=classic] .ts-card')).backgroundImage.split('linear-gradient').length - 1")
        check("the Classic square in Settings still draws eight marks", n == 8, n)
        check("no page errors", not errors, errors)
        browser.close()
    ok = all(results)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
