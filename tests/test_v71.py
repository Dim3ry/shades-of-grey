"""v71 tests for Minifolio (chunk 4.2a: Ask the Mentor, first half).

What changed:
 The Compendium gets a new folding part, Ask the Mentor (first of the parts, under the Pro preview heading). You choose a Base colour, a
 Second colour (optional) and a Part (Armour, Eyes, Weapon or Base). Under each chosen colour you get up to three paint picks for that part,
 each row with its tag and reason, your own paints first and a poor match you own labelled Yours, poor fit. It reuses the Colour ideas rules.
 The tips and the similar-paint alternatives are the second half (4.2b).

Checks:
1. The part is there, first, shut to start, and the Compendium still carries the Pro preview label.
2. Empty state: one short line. The two pickers and the four part buttons (Armour pressed to start).
3. A base colour gives up to three rows under "With <paint>", each with a tag and a reason; your own paints are tagged and none is claimed when you own nothing.
4. A second colour adds a second list; the same paint twice gives one; the part changes the picks.
5. The picks are kept when you leave the Compendium and come back, and clearing the base colour brings back the empty line.
6. 390 px and 360 px, dark and light: no sideways scroll, the pickers and part buttons are 44 px or more.
7. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PANEL = "#cmp-fold-mentor-panel"

def open_mentor(page):
    t.blur(page)   # the bottom bar hides while a box has the focus
    page.click('nav button[data-tab="compendium"]')
    page.wait_for_selector("#cmp-fold-mentor-button")
    if page.get_attribute("#cmp-fold-mentor-button", "aria-expanded") != "true":
        page.click("#cmp-fold-mentor-button")
    page.wait_for_timeout(150)

def pick(page, box, text):
    page.click(f"#cmp-mentor-{box}")
    page.fill(f"#cmp-mentor-{box}", text)
    page.wait_for_timeout(150)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(250)

def part(page, key):
    page.click(f'{PANEL} [data-mentor-part="{key}"]')
    page.wait_for_timeout(200)

def rows(page):
    return page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-mentor-panel .idea-list > li')].map(li => ({
        name: (li.querySelector('.idea-name') || {}).childNodes ? li.querySelector('.idea-name').childNodes[0].textContent : '',
        tag: [...li.querySelectorAll('.idea-tag')].map(x => x.textContent), text: li.textContent.length }))""")

def labels(page):
    return page.evaluate("() => [...document.querySelectorAll('#cmp-fold-mentor-panel > .idea-label')].map(x => x.textContent)")

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. The part ---")
        load(page)
        page.click('nav button[data-tab="compendium"]')
        page.wait_for_selector("#cmp-fold-mentor-button")
        first = page.evaluate("() => document.querySelector('#compendium-body .fold-button').id")
        check("Ask the Mentor is the first folding part and starts shut", first == "cmp-fold-mentor-button" and page.get_attribute("#cmp-fold-mentor-button", "aria-expanded") == "false")
        check("the Compendium still carries the Pro preview label", "Pro preview" in page.inner_text("#view-compendium .card-head"))

        print("\n--- 2. Empty state and the buttons ---")
        open_mentor(page)
        check("one short line says what to do", page.inner_text("#cmp-mentor-none") == "Choose a colour above.")
        check("a Base colour box and a Second colour box", page.inner_text("#cmp-mentor-base-combo label") == "Base colour" and page.inner_text("#cmp-mentor-second-combo label") == "Second colour")
        parts = page.evaluate("() => [...document.querySelectorAll('#cmp-fold-mentor-panel [data-mentor-part]')].map(b => [b.textContent, b.getAttribute('aria-pressed')])")
        check("four part buttons, Armour pressed to start", parts == [["Armour", "true"], ["Eyes", "false"], ["Weapon", "false"], ["Base", "false"]], parts)

        print("\n--- 3. Picks for a base colour ---")
        pick(page, "base", "Macragge")
        r = rows(page)
        check("up to three rows under 'With Macragge Blue'", labels(page) == ["Part", "With Macragge Blue"] and 1 <= len(r) <= 3, (labels(page), len(r)))
        check("each row has a name, an ownership tag and a reason behind it", all(x["name"] and x["tag"] and x["text"] > 20 for x in r), r[:2])
        check("a paint of yours is tagged You own this, and a poor one Yours, poor fit",
              any("You own this" in x["tag"] for x in r) or any("Yours, poor fit" in x["tag"] for x in r), r)
        load(page, paints=[])
        open_mentor(page)
        pick(page, "base", "Macragge")
        r = rows(page)
        check("with no paints of yours, no row claims you own it", r and not any(("You own this" in x["tag"]) or ("Yours, poor fit" in x["tag"]) for x in r), r)

        print("\n--- 4. Second colour and part ---")
        load(page)
        open_mentor(page)
        pick(page, "base", "Macragge")
        armour = [x["name"] for x in rows(page)]
        part(page, "eyes")
        eyes = [x["name"] for x in rows(page)]
        check("the part changes the picks", armour and eyes and armour != eyes, (armour, eyes))
        check("the chosen part button is the one pressed", page.get_attribute(f'{PANEL} [data-mentor-part="eyes"]', "aria-pressed") == "true" and page.get_attribute(f'{PANEL} [data-mentor-part="armour"]', "aria-pressed") == "false")
        pick(page, "second", "Troll Slayer")
        check("a second colour adds a second list", labels(page) == ["Part", "With Macragge Blue", "With Troll Slayer Orange"], labels(page))
        pick(page, "second", "Macragge")
        check("the same paint twice gives one list", labels(page) == ["Part", "With Macragge Blue"], labels(page))

        print("\n--- 5. Kept while the app is open ---")
        pick(page, "second", "Troll Slayer")
        t.blur(page)
        page.click('nav button[data-tab="units"]')
        page.wait_for_timeout(150)
        open_mentor(page)
        check("the picks are still there after leaving the Compendium", labels(page) == ["Part", "With Macragge Blue", "With Troll Slayer Orange"]
              and page.get_attribute(f'{PANEL} [data-mentor-part="eyes"]', "aria-pressed") == "true", labels(page))
        for box in ("base", "second"):   # scroll each Clear to the middle first: the bottom bar would sit over it near the bottom edge
            page.evaluate("id => document.getElementById(id).scrollIntoView({ block: 'center' })", f"cmp-mentor-{box}-clear")
            page.click(f"#cmp-mentor-{box}-clear")
            page.wait_for_timeout(300)
        check("clearing both colours brings back the empty line", page.locator("#cmp-mentor-none").count() == 1 and not rows(page), (labels(page), page.locator("#cmp-mentor-none").count(), len(rows(page))))

        print("\n--- 6. Phones, dark and light ---")
        for width in (390, 360):
            for scheme in ("dark", "light"):
                page.set_viewport_size({"width": width, "height": 844})
                load(page, settings={"appearance": scheme})
                open_mentor(page)
                pick(page, "base", "Macragge")
                pick(page, "second", "Troll Slayer")
                small = page.evaluate("""() => [...document.querySelectorAll('#cmp-fold-mentor-panel .combo-input, #cmp-fold-mentor-panel [data-mentor-part]')]
                    .filter(b => b.getBoundingClientRect().height < 43.5).map(b => b.id || b.textContent)""")
                check(f"{width} px {scheme}: no sideways scroll", no_sideways(page))
                check(f"{width} px {scheme}: the boxes and part buttons are 44 px or more", not small, small)

        print("\n--- 7. Errors ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
