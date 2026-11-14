"""FX4 test for Minifolio (what the second AI re-test still found wrong). New behaviour only, with real taps.
1. An old message goes when a screen row is tapped (Models/Wanted, Painting rows, bottom menu); a fresh one stays; one message at a time.
2. The paste result line says Owned only when the paints are Owned.
3. Keep them leaves every paint with no status (and its message no longer says "as your own").
4. The restore question names current wanted models when the backup carries a wanted list.
5. The empty Shopping list says what fills it; a Wishlist paint of the person's own does.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready, leave_launch

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

STAGES = ["Boxed", "Built", "Primed", "Painted"]
UNIT = {"id": 1, "name": "Squad", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}
WISH = {"id": 1, "name": "Zed Riders", "count": 2, "game": "Skirmish", "faction": "Bright Host", "really": False, "note": "", "added": "2026-10-01"}

def toast(page): return page.evaluate("({hidden: document.getElementById('toast').classList.contains('hidden'), text: document.getElementById('toast-text').textContent})")
def fresh_install(page):
    page.goto(t.URL); page.evaluate("localStorage.clear()"); page.reload()
    app_ready(page); leave_launch(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, scheme in ((390, 844, "dark"), (360, 640, "light")):
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.on("dialog", lambda d: d.dismiss())
            print(f"\n--- 1. Messages and screen rows ({w}px, {scheme}) ---")
            t.load(page, units=[UNIT], settings={"examplesChecked": True, "stages": STAGES, "modelWishes": [WISH]})
            page.click('nav button[data-tab="units"]'); t.quiet(page)
            page.click('#models-seg button[data-mview="wishes"]'); t.quiet(page)
            page.click("#wish-list >> text=Zed Riders"); t.quiet(page)
            page.click(".w-delete"); t.quiet(page)
            check("the Removed message is up with Undo", toast(page)["text"] == "Removed Zed Riders" and page.is_visible("#toast-undo"), toast(page))
            page.click('#models-seg button[data-mview="models"]'); t.quiet(page)
            check("a message under 2 seconds old survives a tap on a screen row", toast(page)["text"] == "Removed Zed Riders", toast(page))
            page.wait_for_timeout(2300)
            page.click('#models-seg button[data-mview="wishes"]'); t.quiet(page)
            check("an older message goes with a tap on the Models/Wanted row", toast(page) == {"hidden": True, "text": ""}, toast(page))
            page.evaluate("showToast('Added Old', () => {}, 'Undo', UNDO_SECONDS)"); page.wait_for_timeout(2300)
            page.click('nav button[data-tab="recipes"]'); t.quiet(page)
            page.evaluate("showToast('Deleted Older', () => {}, 'Undo', UNDO_SECONDS)"); page.wait_for_timeout(2300)
            page.click('#recipe-seg button:has-text("Your Palette")'); t.quiet(page)
            check("an older message goes with a tap on a Painting row", toast(page)["hidden"] and "Deleted Older" not in page.evaluate("document.body.textContent"), toast(page))
            page.evaluate("showToast('Added Open', () => {}, 'Undo', UNDO_SECONDS)"); page.wait_for_timeout(2300)
            page.click('#recipe-seg button:has-text("Your Palette")'); t.quiet(page)
            check("a tap on the row already open is not a move: the message stays", toast(page)["text"] == "Added Open", toast(page))
            page.evaluate("showToast('Deleted One', () => { showToast('One is back') }, 'Undo', UNDO_SECONDS)")
            page.click("#toast-undo"); page.wait_for_timeout(30)
            check("after Undo only the new message is on the page (no fading copy of the old one)",
                  page.evaluate("document.body.textContent").count("Deleted One") == 0 and page.evaluate("document.querySelectorAll('.toast').length") == 1, page.evaluate("document.querySelectorAll('.toast').length"))
            check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: d.dismiss())

        print("\n--- 2. Paste result line, and 3. Keep them (fresh install, real taps) ---")
        fresh_install(page)
        page.click('nav button[data-tab="recipes"]'); t.quiet(page)
        page.locator('button:visible:has-text("Paste recipes from your notes")').first.click(); t.quiet(page)
        page.fill("#import-text", "Dark\n\nArmour:\nZorblax Goo\nNuln Oil")
        page.click("text=Read notes"); page.wait_for_selector("#import-save")
        page.click("#import-save"); page.wait_for_function("() => !importDraft"); t.quiet(page)
        review = page.evaluate("(document.getElementById('import-review') || {}).textContent || ''")
        check("unticked: the result line does not say Owned", "added" in review and "Owned" not in review, review)
        fresh_install(page)
        page.click('nav button[data-tab="recipes"]'); t.quiet(page)
        page.locator('button:visible:has-text("Paste recipes from your notes")').first.click(); t.quiet(page)
        page.fill("#import-text", "Dark\n\nArmour:\nZorblax Goo\nNuln Oil")
        page.click("text=Read notes"); page.wait_for_selector("#import-save")
        page.click("#import-owned"); page.click("#import-save"); page.wait_for_function("() => !importDraft"); t.quiet(page)
        review = page.evaluate("(document.getElementById('import-review') || {}).textContent || ''")
        check("ticked: the result line says Owned", "added as Owned" in review, review)

        fresh_install(page)
        before = page.evaluate("book.paints.filter(p => p.example).length")
        page.click('nav button[data-tab="units"]'); t.quiet(page)
        page.click("#examples-card .keep-examples"); page.wait_for_timeout(300)
        check("Keep them: the message no longer says as your own", "as your own" not in toast(page)["text"] and toast(page)["text"].startswith("Kept "), toast(page))
        check("Keep them: no example paint becomes Owned", before > 0 and page.evaluate("book.paints.every(p => !paintStatus(p))"), before)

        print("\n--- 4. Restore names current wanted models ---")
        t.load(page, units=[UNIT], settings={"examplesChecked": True, "stages": STAGES, "modelWishes": [WISH]})
        page.click('nav button[data-tab="units"]'); t.quiet(page)
        from launch_helpers import tap_tab
        tap_tab(page, "settings"); t.quiet(page)
        def ask(data):
            page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
            page.wait_for_selector("#dialog-backdrop:not(.hidden)")
            q = page.text_content("#dialog-message"); page.click("#dialog-no"); page.wait_for_timeout(300); return q
        q = ask({"app": "Minifolio", "dataVersion": 2, "models": [UNIT], "modelWishes": []})
        check("an empty wanted list in the backup still names your 1 wanted model", q.startswith("Replace your current 1 unit and 1 wanted model with 1 from the backup?"), q)
        q = ask({"app": "Minifolio", "dataVersion": 2, "models": [UNIT]})
        check("a backup with no wanted list: your wanted models stay, so they are not named", "wanted" not in q, q)

        print("\n--- 5. Shopping empty state ---")
        fresh_install(page)
        page.click('nav button[data-tab="recipes"]'); t.quiet(page)
        page.click('#recipe-seg button:has-text("Shopping")'); t.quiet(page)
        txt = page.inner_text("#shop-panel")
        check("the empty list says what fills it", "Nothing to buy." in txt and "Wishlist" in txt, txt[:200])
        page.evaluate("applyPaintStatus(findOrAddPaint('Citadel', 'Mournfang Brown', '#5a3a1a'), 'wishlist'); render()")
        t.quiet(page)
        check("a Wishlist paint of the person's own goes on the list", "Mournfang Brown" in page.inner_text("#shop-panel") and "Nothing to buy" not in page.inner_text("#shop-panel"), page.inner_text("#shop-panel")[:200])
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
