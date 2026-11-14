"""WL1 test for Minifolio (Models | Wish list: the switch, the list, add, edit, delete with Undo, saving and backups). New behaviour only."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

UNITS = [{"id": 1, "name": "Squad A", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}]
def wish(i, name, game="", faction="", count=1, really=False, note=""):
    return {"id": i, "name": name, "count": count, "game": game, "faction": faction, "really": really, "note": note, "added": "2026-10-01"}
WISHES = [wish(1, "The Zed Riders", "Skirmish", "Bright Host", 5), wish(2, "Archers", "Skirmish", "Bright Host", 2, True),
          wish(3, "Moss Knights", "Fantasy", "Moss Court", 4), wish(4, "Loose Model"), wish(5, "Gloom Scouts", "Skirmish", "", 1)]

def fresh(page, wishes=None, **settings):
    s = {"examplesChecked": True, **settings}
    if wishes is not None: s["modelWishes"] = wishes
    t.load(page, units=UNITS, settings=s)
    page.click('nav button[data-tab="units"]'); t.quiet(page)
def to_wishes(page):
    page.click('#models-seg button[data-mview="wishes"]'); page.wait_for_selector("#wish-view:not(.hidden)")
def heads(page): return page.evaluate("[...document.querySelectorAll('#wish-list .unit-head')].map(h => h.textContent.trim())")
def names(page): return page.evaluate("[...document.querySelectorAll('#wish-list .wish-name')].map(n => n.textContent)")
def vis(page, sel): return page.evaluate("s => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0; }", sel)
def stored(page): return json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings')")).get("modelWishes")
def add_wish(page, name, count="1", game="", faction="", really=False, note=""):
    page.click("#wish-add")
    page.fill(".wish-form .w-name", name); page.fill(".wish-form .w-count", count)
    page.fill(".wish-form .w-game", game); page.fill(".wish-form .w-faction", faction); page.fill(".wish-form .w-note", note)
    if really: page.check(".wish-form .w-really")
    page.click(".wish-form button[type=submit]")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        fresh(page, WISHES)

        print("\n--- 1. The switch ---")
        check("the page opens on Models with the switch above Add unit",
              page.get_attribute('#models-seg button[data-mview="models"]', "aria-selected") == "true" and vis(page, "#toggle-add") and not vis(page, "#wish-view")
              and page.evaluate("document.getElementById('models-seg').getBoundingClientRect().bottom <= document.getElementById('toggle-add').getBoundingClientRect().top"))
        to_wishes(page)
        check("Wish list hides the Add unit, Select, Filters and Sort controls and the unit list",
              not any(vis(page, s) for s in ("#toggle-add", "#toggle-select", "#toggle-filters", "#toggle-sort", "#unit-list")))
        check("the switch says which option is chosen", page.get_attribute('#models-seg button[data-mview="wishes"]', "aria-selected") == "true")
        check("the switch options are 44 px or more high",
              page.evaluate("[...document.querySelectorAll('#models-seg button')].every(b => b.getBoundingClientRect().height >= 43.5)"))
        page.click('#models-seg button[data-mview="models"]')
        check("back on Models the controls are back and the wish list is gone", vis(page, "#toggle-add") and not vis(page, "#wish-view"))

        print("\n--- 2. The list: order, groups, count ---")
        to_wishes(page)
        check("the count line", page.text_content("#wish-count").strip() == "5 wishes, 13 models", page.text_content("#wish-count"))
        check("games A to Z, then factions, with No game and No faction last",
              heads(page) == ["Fantasy", "Moss Court1 wish", "Skirmish", "Bright Host2 wishes", "No faction1 wish", "No game", "No faction1 wish"], heads(page))
        check("A to Z inside a faction ignores a leading The", names(page) == ["Moss Knights", "Archers", "The Zed Riders", "Gloom Scouts", "Loose Model"], names(page))
        subs = page.evaluate("[...document.querySelectorAll('#wish-list .wish-sub')].map(n => n.textContent)")
        check("each row reads models, game, faction", subs[1].startswith("2 models · Skirmish · Bright Host"), subs)
        check("Really want shows only on the wish marked so", [("Really want" in s) for s in subs] == [False, True, False, False, False], subs)
        check("Got it is hidden until WL2", not page.evaluate("[...document.querySelectorAll('.wish-got')].some(b => b.getClientRects().length > 0)"))

        print("\n--- 3. Wishes stay out of everything else ---")
        page.click('#models-seg button[data-mview="models"]')
        check("the Models summary line counts only units", page.text_content("#filter-note").strip() == "1 unit, 3 models", page.text_content("#filter-note"))
        check("Select mode lists only units", page.evaluate("document.querySelectorAll('#unit-list li.unit').length") == 1)
        page.click('nav button[data-tab="dashboard"]'); t.quiet(page)
        with_wishes = page.evaluate("document.getElementById('view-dashboard').innerText")
        fresh(page, []); page.click('nav button[data-tab="dashboard"]'); t.quiet(page)
        check("the Nexus reads the same with five wishes as with none", with_wishes == page.evaluate("document.getElementById('view-dashboard').innerText"))
        fresh(page, WISHES)
        page.click('nav button[data-tab="units"]'); t.quiet(page)

        print("\n--- 4. Add ---")
        to_wishes(page)
        add_wish(page, "<b>x</b> Bold", "3", "Skirmish", "Bright Host", True, "note <i>q</i>")
        check("the form shuts and the wish is in its group with its count", page.locator(".wish-form").count() == 0 and "<b>x</b> Bold" in names(page))
        check("the count line follows", page.text_content("#wish-count").strip() == "6 wishes, 16 models", page.text_content("#wish-count"))
        check("typed tags show as plain text", page.locator("#wish-list b, #wish-list i").count() == 0)
        check("the message says Added, as plain text", page.text_content("#toast-text").strip() == "Added <b>x</b> Bold" and page.locator("#toast-text b").count() == 0, page.text_content("#toast-text"))
        saved = stored(page)
        w = [x for x in saved if x["name"] == "<b>x</b> Bold"][0]
        check("saved with id, count, game, faction, flag, note and date",
              w["count"] == 3 and w["game"] == "Skirmish" and w["faction"] == "Bright Host" and w["really"] is True and w["note"] == "note <i>q</i>" and w["added"] and isinstance(w["id"], int), w)
        page.click("#wish-add")
        check("the form has Name, number, Game, Faction, Really want and Note, and the number starts at 1",
              page.input_value(".w-count") == "1" and not page.is_checked(".w-really") and page.locator(".wish-form .w-note").count() == 1)
        page.fill(".w-name", "   "); page.click(".wish-form button[type=submit]")
        check("a name of spaces is not saved", len(stored(page)) == 6)
        page.click(".w-cancel")
        check("Cancel shuts the form", page.locator(".wish-form").count() == 0)

        print("\n--- 5. Edit and delete ---")
        page.click('#wish-list li[data-wish-id="4"] .wish-info')
        check("tapping a row opens the form filled in, with Delete", page.input_value(".w-name") == "Loose Model" and page.locator(".w-delete").count() == 1)
        page.fill(".w-name", "Loose Model Two"); page.fill(".w-game", "Fantasy"); page.fill(".w-faction", "Moss Court"); page.click(".wish-form button[type=submit]")
        check("the edit moves it into its new group", "Loose Model Two" in names(page) and "No game" not in heads(page), heads(page))
        page.click('#wish-list li[data-wish-id="4"] .wish-info'); page.click(".w-delete")
        check("Delete removes it at once and says so with Undo", "Loose Model Two" not in names(page) and page.text_content("#toast-undo").strip() == "Undo" and len(stored(page)) == 5)
        page.click("#toast-undo")
        check("Undo puts it back exactly as it was", len([x for x in stored(page) if x["id"] == 4]) == 1 and [x for x in stored(page) if x["id"] == 4][0]["game"] == "Fantasy"
              and "Loose Model Two" in names(page))

        print("\n--- 6. Saving, old saves and backups ---")
        page.reload(); t.app_ready(page) if hasattr(t, "app_ready") else None
        page.click('nav button[data-tab="units"]'); t.quiet(page)
        check("the wish list is still on Models after a restart (and the page opens on Models)", vis(page, "#toggle-add"))
        to_wishes(page)
        check("wishes survive a restart", len(names(page)) == 6, names(page))
        fresh(page); to_wishes(page)
        check("a save with no wish field loads as an empty list with one short line", names(page) == [] and page.text_content("#wish-list").strip() == "No wishes yet.")
        add_wish(page, "Kept")
        backup = page.evaluate("JSON.parse(JSON.stringify(backupData()))")
        check("a backup carries the wishes", [w["name"] for w in backup["modelWishes"]] == ["Kept"], backup.get("modelWishes"))
        def restore(data):
            page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
            page.wait_for_selector("#dialog-yes", state="visible"); page.click("#dialog-yes"); page.wait_for_timeout(500)
        old = {k: v for k, v in backup.items() if k != "modelWishes"}
        restore(old)
        check("restoring an old backup does not error and keeps the wishes", [w["name"] for w in stored(page)] == ["Kept"] and not errors, (stored(page), errors))
        new = dict(backup, modelWishes=[wish(7, "From backup", "Fantasy", "Moss Court", 2), {"junk": 1}])
        restore(new)
        check("restoring a new backup brings its wishes back (damaged entries dropped)", [w["name"] for w in stored(page)] == ["From backup"], stored(page))

        print("\n--- 7. Phone sizes, light and dark, two looks ---")
        for w, h, mode, theme in ((390, 844, "dark", "classic"), (360, 640, "light", "classic"), (320, 568, "dark", "bench")):
            page.set_viewport_size({"width": w, "height": h})
            long = [wish(1, "A very long wish name " * 6, "Skirmish", "Bright Host", 2, True)]
            fresh(page, long, theme=theme, appearance=mode); to_wishes(page)
            m = page.evaluate("""() => { const r = document.querySelector('.wish-row').getBoundingClientRect(), i = document.querySelector('.wish-info').getBoundingClientRect();
                return { side: document.documentElement.scrollWidth <= innerWidth + 1, inside: r.right <= innerWidth + 1, tall: i.height >= 43.5,
                         add: document.getElementById('wish-add').getBoundingClientRect().height >= 43.5 }; }""")
            check(f"{w}x{h} {mode} {theme}: long name wraps, no sideways scroll, 44 px taps", all(m.values()), m)
        check("no page errors", not [e for e in errors if "woff2" not in e], errors)
        browser.close()
    bad = results.count(False)
    print(f"\n{len(results) - bad} passed, {bad} failed")
    sys.exit(1 if bad else 0)

main()
