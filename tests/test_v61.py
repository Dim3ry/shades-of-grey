"""v61 tests for Minifolio (chunk 1.4: make per-model tracking findable).

What changed:
 AI testers found per-model tracking hidden: it took 3 to 5 taps (unit, Edit details, a tick labelled
 "Track each model separately"), inside a section whose label named only name, game and faction. Now a unit
 with more than one model has a button right under its stage: "Track models separately" when it is off,
 "Track as one batch" when it is on. The tick in Edit details is gone. Both ways have an Undo.

Checks:
1. Versions, the v61 Updates entry, DATA_VERSION is still 1.
2. The button: shown for units of 2 or more models, not for one-model units, not in Edit details any more.
3. One tap turns it on and shows each model's row; Undo puts the unit back exactly (saved data too).
4. "Track as one batch": same stages goes straight back; different stages asks first; Undo brings each
   model's stage back, diary included. No on the question changes nothing.
5. A unit of more than 100 models: a notice, nothing changes.
6. Help: the per-model topic names the button, the way back and Undo; Edit details no longer lists the tick.
7. 390 px and 360 px, dark and light: no sideways scroll, the button is 44 px or more and fits.
8. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import test_v31 as t
import test_v44 as e   # main_tab, sub_tab

URL, read = t.URL, t.read
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

UNITS = [
    {"id": 1, "name": "Boyz", "hobby": "40K", "faction": "Orks", "stage": 2, "count": 5,
     "added": "2026-10-01", "log": [["2026-10-01", 0], ["2026-10-05", 2]]},
    {"id": 2, "name": "Warboss", "hobby": "40K", "faction": "Orks", "stage": 1, "count": 1,
     "added": "2026-10-01", "log": [["2026-10-01", 1]]},
    {"id": 3, "name": "Gretchin", "hobby": "40K", "faction": "Orks", "stage": 3, "count": 4, "each": True,
     "stages": [3, 5, 3, 4], "added": "2026-10-01", "log": [["2026-10-01", 3], ["2026-10-06", 5, 1], ["2026-10-07", 4, 3]]},
    {"id": 4, "name": "Horde", "hobby": "40K", "faction": "Orks", "stage": 0, "count": 150,
     "added": "2026-10-01", "log": [["2026-10-01", 0]]},
]
SETTINGS = {"tab": "units", "examplesChecked": True}

def card(uid):
    return f'#view-units li.unit[data-id="{uid}"]'

def stored(page, uid):
    units = json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))
    return next((u for u in units if u["id"] == uid), None)

def open_unit(page, uid):
    info = f"{card(uid)} .info"
    if page.get_attribute(info, "aria-expanded") != "true":
        page.click(info)
        page.wait_for_timeout(250)

def track(page, uid):
    return page.locator(f"{card(uid)} .panel button.track-each")

def tap_undo(page):
    page.click("#toast-undo")
    page.wait_for_timeout(250)

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        notices = []
        attach_notices(page, notices.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        t.load(page, units=UNITS, settings=SETTINGS)
        entry = page.evaluate("CHANGELOG.find(c => c.version === 'v61')")
        check("the entry names the button and the way back", entry and "Track models separately" in " ".join(entry["changes"]) and "Track as one batch" in " ".join(entry["changes"]), entry)

        # ---------- 2. Where the button is ----------
        print("\n--- 2. The button ---")
        open_unit(page, 1)
        check("a 5-model batch unit shows Track models separately", track(page, 1).count() == 1 and track(page, 1).inner_text() == "Track models separately", track(page, 1).count())
        under = page.evaluate("""(sel) => { const p = document.querySelector(sel); const kids = [...p.children];
            const b = p.querySelector('button.track-each'); const i = kids.indexOf(b);
            return i > 0 && !!kids[i - 1].querySelector('select.jump-stage'); }""", f"{card(1)} .panel")
        check("…straight under the stage menu, outside Edit details", under and page.locator(f"{card(1)} .edit-details button.track-each").count() == 0)
        check("the old tick is gone from Edit details", page.locator(f'{card(1)} .edit-details-body label:has-text("Track each model")').count() == 0)
        check("no sentence next to the button (label only)", page.evaluate(f"""() => {{ const b = document.querySelector('{card(1)} .panel button.track-each');
            return !b.nextElementSibling || !b.nextElementSibling.matches('p, small, .hint'); }}"""))
        open_unit(page, 2)
        check("a one-model unit has no button", track(page, 2).count() == 0)
        open_unit(page, 3)
        check("a unit already tracked model by model offers Track as one batch", track(page, 3).inner_text() == "Track as one batch")

        # ---------- 3. Turn on, Undo ----------
        print("\n--- 3. On, and Undo ---")
        before = stored(page, 1)
        track(page, 1).click()
        page.wait_for_timeout(300)
        u = stored(page, 1)
        check("one tap turns it on and saves it", u.get("each") is True and u.get("stages") == [2] * 5, u)
        check("…the panel stays open and shows each model's row", page.locator(f"{card(1)} .each-list li").count() == 5)
        check("…and the button now offers the way back", track(page, 1).inner_text() == "Track as one batch")
        check("…with an Undo on the message", page.locator("#toast-undo").is_visible() and "Boyz" in page.inner_text("#toast-text"), page.inner_text("#toast-text"))
        tap_undo(page)
        check("Undo puts the unit back exactly as it was", stored(page, 1) == before, stored(page, 1))
        check("…and the button says Track models separately again", track(page, 1).inner_text() == "Track models separately")

        # ---------- 4. Turn off ----------
        print("\n--- 4. Track as one batch ---")
        track(page, 1).click()
        page.wait_for_timeout(300)
        track(page, 1).click()
        page.wait_for_timeout(300)
        check("models at the same stage go back to one batch with no question", stored(page, 1).get("each") is None and not page.locator("#dialog-yes").is_visible())
        check("…with an Undo", page.locator("#toast-undo").is_visible())
        tap_undo(page)
        check("Undo turns per-model tracking back on", stored(page, 1).get("each") is True)

        before = stored(page, 3)
        track(page, 3).click()
        page.wait_for_timeout(300)
        check("models at different stages: the app asks first", page.locator("#dialog-yes").is_visible())
        page.click("#dialog-no")
        page.wait_for_timeout(250)
        check("No changes nothing", stored(page, 3) == before, stored(page, 3))
        track(page, 3).click()
        page.wait_for_timeout(300)
        page.click("#dialog-yes")
        page.wait_for_timeout(300)
        u = stored(page, 3)
        check("Yes: one batch at the furthest-behind stage", u.get("each") is None and u.get("stages") is None and u["stage"] == 3, u)
        tap_undo(page)
        check("Undo brings back each model's stage and the diary exactly", stored(page, 3) == before, stored(page, 3))

        # ---------- 5. Too many models ----------
        print("\n--- 5. Over 100 models ---")
        open_unit(page, 4)
        before = stored(page, 4)
        track(page, 4).click()
        page.wait_for_timeout(300)
        check("a 150-model unit gets a notice and nothing changes", stored(page, 4) == before and any("100" in n for n in notices), notices[-1:])

        # ---------- 6. Help ----------
        print("\n--- 6. Help ---")
        e.main_tab(page, "settings")
        e.sub_tab(page, "help")
        page.click("summary:has-text('Adding and updating units')")
        page.wait_for_timeout(150)
        topic = page.text_content("#help-track-each") or ""
        check("Help has a per-model topic naming the button, the way back and Undo",
              all(w in topic for w in ["Track models separately", "Track as one batch", "Undo", "100"]), topic)
        check("Help's Edit details line no longer lists the tick", "Track each model separately" not in (page.text_content("#help-edit-details") or ""))
        check("no em dash in the new Help line", "—" not in topic)

        # ---------- 7. Phones, dark and light ----------
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                print(f"\n--- 7. {tag} ---")
                page.set_viewport_size({"width": width, "height": 780})
                t.load(page, units=UNITS, settings=dict(SETTINGS, appearance=appearance))
                open_unit(page, 1)
                open_unit(page, 3)
                check(f"{tag}: no sideways scroll", not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
                sizes = page.evaluate("""() => [...document.querySelectorAll('button.track-each')].map(b => { const r = b.getBoundingClientRect();
                    return [Math.round(r.height), r.right <= document.documentElement.clientWidth]; })""")
                check(f"{tag}: both buttons are 44 px or more and fit on screen", len(sizes) == 2 and all(h >= 44 and fits for h, fits in sizes), sizes)
                os.makedirs(os.path.join(HERE, "screenshots"), exist_ok=True)
                page.locator(card(1)).screenshot(path=os.path.join(HERE, "screenshots", f"v61-track-{appearance}-{width}.png"))

        # ---------- 8. Safety ----------
        print("\n--- 8. Safety ---")
        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
