"""v72 tests for Minifolio (chunk 4.2b: Ask the Mentor, tips and alternatives).

What changed:
 Under the Ask the Mentor picks, the Mentor tips for the chosen part are shown (from mentor-tips.js through mentorTipsFor), each with its
 advice, its suggested colours (swatch and look) and its credit as a safe https link when it has one. A tip whose colour words name the
 family of a chosen colour comes first. No tip fits: nothing is shown. The similar-paint alternatives were already reachable from each pick
 (the Similar paints button from 3.5), so that part is only checked, not changed.

Checks:
1. A part with a tip shows it under the picks, with its colours; the sample tips say they are samples.
2. A part with no tip (Weapon) shows no tips and no empty line about tips.
3. A credit is a link with an https address that opens in a new tab with rel noopener noreferrer; a credit with an unsafe address is plain text.
4. Tip text that looks like HTML is shown as text, never turned into page elements.
5. A colour-matched tip comes first. Each pick still has its Similar paints button, and it opens the 3.5 pop-up.
6. 390 px and 360 px, dark and light: no sideways scroll, the credit link is 44 px or more.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_v71 as m

load, no_sideways = t.load, t.no_sideways
open_mentor, pick, part = m.open_mentor, m.pick, m.part
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

TIPS = "#cmp-mentor-tips"

def tips(page):
    return page.evaluate("""() => [...document.querySelectorAll('#cmp-mentor-tips .mentor-tip')].map(li => ({ key: li.dataset.tip,
        text: li.querySelector('.mentor-tip-advice').textContent, swatches: li.querySelectorAll('.mentor-tip-colours .swatch').length,
        looks: [...li.querySelectorAll('.mentor-tip-colours li')].map(x => x.textContent),
        link: li.querySelector('.mentor-tip-credit a') ? { href: li.querySelector('.mentor-tip-credit a').href,
              rel: li.querySelector('.mentor-tip-credit a').rel, target: li.querySelector('.mentor-tip-credit a').target } : null,
        credit: (li.querySelector('.mentor-tip-credit') || {}).textContent || '' }))""")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Tips for a part ---")
        load(page)
        open_mentor(page)
        check("no tips before a colour is chosen", page.locator(TIPS).count() == 0)
        pick(page, "base", "Macragge")
        tp = tips(page)
        check("Armour shows its tip under the picks", [x["key"] for x in tp] == ["sample-armour"], tp)
        below = page.evaluate("() => { const l = [...document.querySelectorAll('#cmp-fold-mentor-panel .idea-list')].pop(); const b = document.getElementById('cmp-mentor-tips'); return !!(l && b && (l.compareDocumentPosition(b) & 4)); }")
        check("the tips sit below the picks", below)
        check("the tip shows its colours as swatches with their looks", tp and tp[0]["swatches"] == 2 and tp[0]["looks"] == ["a deep blue", "a light blue"], tp)
        check("a sample tip says it is a sample", tp and "Sample tip" in tp[0]["text"], tp)
        part(page, "eyes")
        check("Eyes shows the eyes tip only", [x["key"] for x in tips(page)] == ["sample-eyes"], tips(page))

        print("\n--- 2. No tip fits ---")
        part(page, "weapon")
        panel = page.inner_text("#cmp-fold-mentor-panel")
        check("Weapon (no tips) shows no tips part", page.locator(TIPS).count() == 0)
        check("and no line about tips", "tip" not in panel.lower(), panel[-200:])
        check("the picks are still there", len(m.rows(page)) >= 1)

        print("\n--- 3. Credit links ---")
        part(page, "base")
        tp = tips(page)
        link = tp[0]["link"] if tp else None
        check("the credited tip has a link to its https address", link and link["href"] == "https://example.com/", tp)
        check("the link opens in a new tab with rel noopener noreferrer", link and link["target"] == "_blank" and set(link["rel"].split()) >= {"noopener", "noreferrer"}, link)
        page.evaluate("""() => MENTOR_TIPS.push(
            { key: "t-bad-url", part: "weapon", colour: "orange", technique: "Layer", advice: "Bad address.", colours: [],
              credit: { name: "Someone", url: "javascript:alert(1)" } },
            { key: "t-http", part: "weapon", colour: "grey", technique: "", advice: "Plain http.", colours: [{ look: "bad", hex: "red;x" }],
              credit: { name: "Other", url: "http://example.com/" } },
            { key: "t-html", part: "weapon", colour: "blue", technique: "<i>Wash</i>", advice: "<img src=x onerror=\\"window.__hit=1\\"><b>bold</b>",
              colours: [{ look: "<u>dark</u>", hex: "#123456" }], credit: { name: "<script>window.__hit=2</script>", url: "https://example.com/a" } })""")
        part(page, "weapon")
        tp = {x["key"]: x for x in tips(page)}
        check("a javascript: credit is plain text, not a link", "t-bad-url" in tp and tp["t-bad-url"]["link"] is None and tp["t-bad-url"]["credit"] == "Credit: Someone", tp.get("t-bad-url"))
        check("an http (not https) credit is plain text, not a link", "t-http" in tp and tp["t-http"]["link"] is None, tp.get("t-http"))
        check("a colour with a bad hex is left out", "t-http" in tp and tp["t-http"]["swatches"] == 0, tp.get("t-http"))

        print("\n--- 4. Text only ---")
        made = page.evaluate("() => document.querySelectorAll('#cmp-mentor-tips img, #cmp-mentor-tips b, #cmp-mentor-tips i, #cmp-mentor-tips u, #cmp-mentor-tips script').length")
        check("tip text that looks like HTML makes no page elements", made == 0, made)
        check("it is shown as the text it is", "t-html" in tp and "<img src=x" in tp["t-html"]["text"] and "<i>Wash</i>" in tp["t-html"]["text"]
              and tp["t-html"]["looks"] == ["<u>dark</u>"] and "<script>" in tp["t-html"]["credit"], tp.get("t-html"))
        check("nothing in it ran", page.evaluate("() => window.__hit === undefined"))

        print("\n--- 5. Order and alternatives ---")
        order = [x["key"] for x in tips(page)]
        check("with a blue chosen, the blue tip comes first", order and order[0] == "t-html", order)
        pick(page, "second", "Troll Slayer")
        order = [x["key"] for x in tips(page)]
        check("an orange second colour puts its tip up front too", order[:2] == ["t-bad-url", "t-html"] or order[:2] == ["t-html", "t-bad-url"], order)
        sim = page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-mentor-panel .idea-list > li')].map(li =>
            [...li.querySelectorAll('button')].some(b => b.textContent.trim() === 'Similar paints'))""")
        check("every pick has a Similar paints button", sim and all(sim), sim)
        btn = page.locator("#cmp-fold-mentor-panel .idea-list > li button", has_text="Similar paints").first
        btn.scroll_into_view_if_needed()
        btn.click()
        page.wait_for_timeout(250)
        check("it opens the Similar paints pop-up", page.evaluate("() => [...document.querySelectorAll('[role=dialog]')].some(d => d.offsetParent !== null && d.textContent.includes('Similar paints'))"))
        page.keyboard.press("Escape")

        print("\n--- 6. Phones, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, settings={"appearance": scheme})
                open_mentor(page)
                pick(page, "base", "Macragge")
                part(page, "base")
                h = page.evaluate("() => { const a = document.querySelector('#cmp-mentor-tips .mentor-tip-credit a'); return a ? a.getBoundingClientRect().height : 0; }")
                check(f"{width} px {scheme}: no sideways scroll", no_sideways(page))
                check(f"{width} px {scheme}: the credit link is 44 px or more", h >= 43.5, h)
                if width == 360 and scheme == "dark" and len(sys.argv) > 1:
                    page.locator(TIPS).screenshot(path=os.path.join(sys.argv[1], "v72_tips_360_dark.png"))

        print("\n--- 7. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
