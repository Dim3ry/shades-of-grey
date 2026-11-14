"""FX3 test for Minifolio (honesty fixes: Last backup after a restore, stale messages, the wish note on its card, the restore question). New behaviour only."""
import json, os, sys, datetime
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

STAGES = ["Boxed", "Built", "Primed", "Painted"]
UNITS = [{"id": i, "name": f"Squad {i}", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]} for i in range(1, 4)]
LONG = "Buy this one in the autumn sale when the shop has the new box, then check the old plastic kit as well"
WISHES = [{"id": 1, "name": "Zed Riders", "count": 2, "game": "Skirmish", "faction": "Bright Host", "really": False, "note": LONG, "added": "2026-10-01"},
          {"id": 2, "name": "Archers", "count": 1, "game": "Skirmish", "faction": "Bright Host", "really": False, "note": "", "added": "2026-10-02"}]

def fresh(page, wishes=None, **settings):
    s = {"examplesChecked": True, "stages": STAGES, **settings}
    if wishes is not None: s["modelWishes"] = wishes
    t.load(page, units=UNITS, settings=s)
    page.click('nav button[data-tab="units"]'); t.quiet(page)
def tab(page, name):
    from launch_helpers import tap_tab
    tap_tab(page, name); t.quiet(page)
def restore(page, data, yes=True):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
    page.wait_for_selector("#dialog-backdrop:not(.hidden)")
    q = page.text_content("#dialog-message")
    page.click("#dialog-yes" if yes else "#dialog-no")
    page.wait_for_timeout(500)
    return q
def page_text(page): return page.evaluate("document.body.textContent")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            fresh(page)
            tab(page, "settings")

            print(f"\n--- 1. Restore counts as a backup ({w}px) ---")
            check("before: Last backup says Never", "Never" in page.inner_text("#backup-age"), page.inner_text("#backup-age"))
            backup = {"app": "Minifolio", "dataVersion": 2, "models": UNITS[:1], "modelWishes": WISHES}
            q = restore(page, backup)
            today = datetime.date.today().isoformat()
            check("after: Last backup is today, not Never", "Never" not in page.inner_text("#backup-age") and "today" in page.inner_text("#backup-age"), page.inner_text("#backup-age"))
            st = json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings')"))
            check("saved date is today, and the backup file gained no new field", st.get("lastBackup") == today and "savedOn" not in backup, st.get("lastBackup"))

            print("\n--- 2. The restore question names wanted models only when there are some ---")
            check("with wanted models (and none yet): named in the same short line", q == "Replace your current 3 units with 1 unit and 2 wanted models from the backup? (Your recipes stay as they are.)", q)
            fresh(page); tab(page, "settings")
            q2 = restore(page, {"app": "Minifolio", "dataVersion": 2, "models": UNITS[:1]}, yes=False)
            check("without wishes: the old wording", q2 == "Replace your current 3 units with 1 from the backup? (Your recipes stay as they are.)", q2)
            ctx.close()

        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))

        print("\n--- 3. Messages: gone on use, replaced by a newer one, gone after leaving the screen ---")
        fresh(page)
        page.evaluate("showToast('Removed Old Thing', () => {}, 'Undo', UNDO_SECONDS)")
        page.click("#toast-undo"); page.wait_for_timeout(700)   # (the fading copy of the message is gone by then)
        check("Undo used: the old words are gone from the page", "Removed Old Thing" not in page_text(page) and page.evaluate("document.getElementById('toast').classList.contains('hidden')"))
        page.evaluate("showToast('Removed First', () => {}, 'Undo', UNDO_SECONDS); showToast('Added Second')")
        check("a newer message replaces the older one", page.text_content("#toast-text") == "Added Second" and "Removed First" not in page_text(page))
        page.wait_for_timeout(400)
        page.evaluate("showToast('Removed Third', () => {}, 'Undo', UNDO_SECONDS)")
        page.wait_for_timeout(2300)   # older than the two-second grace
        tab(page, "settings")
        check("leaving the screen removes it (text and Undo)", "Removed Third" not in page_text(page) and page.evaluate("document.getElementById('toast').classList.contains('hidden')"))
        page.evaluate("showToast('Removed Fourth', () => { window.ranStale = true }, 'Undo', UNDO_SECONDS); showTab('units')")
        check("a message made in the same moment as the move stays", page.text_content("#toast-text") == "Removed Fourth")

        print("\n--- 4. The wish note on its card ---")
        fresh(page, WISHES)
        page.click('#models-seg button[data-mview="wishes"]'); page.wait_for_selector("#wish-view:not(.hidden)")
        notes = page.evaluate("[...document.querySelectorAll('#wish-list .wish-note')].map(n => n.textContent)")
        check("one note line, on the wish that has a note only", len(notes) == 1, notes)
        check("cut at about 60 characters with an ellipsis", notes and notes[0].endswith("…") and 55 <= len(notes[0]) <= 62, notes)
        check("the note is one line (no wrapping)", page.evaluate("getComputedStyle(document.querySelector('.wish-note')).whiteSpace") == "nowrap")
        check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
