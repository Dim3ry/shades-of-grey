"""Chunk DR1 tests for Minifolio: kept drafts and the storage quota. New behaviour only.
1. A draft keeps at most 50,000 characters per piece (was 500,000), and a recipe step's note at most 2,000.
2. When a normal save fails because storage is full, the kept drafts are dropped first and the save is tried again.
   If that is not enough, the red banner still shows.
3. Remove safety copies: when drafts exist it says how much room they use (one line) and offers to throw them away;
   with no drafts there is no such line. With drafts only, the banner button still appears.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready, leave_launch, quiet

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Fake "storage full": with window.__quota set, setItem throws once the total would pass it (as in test_v126_ds2).
QUOTA = """(() => {
  const realSet = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (window.__quota != null) {
      let total = 0;
      for (let i = 0; i < this.length; i++) { const key = this.key(i); if (key !== k) total += key.length + this.getItem(key).length; }
      if (total + k.length + String(v).length > window.__quota) throw new DOMException("full", "QuotaExceededError");
    }
    return realSet.call(this, k, v);
  };
})();"""

SETTINGS = {"examplesChecked": True, "recipeExamplesChecked": True, "tab": "dashboard"}
BOOK = {"v15": True, "paints": [], "recipes": [], "schemes": []}
UNITS = [{"id": 1, "name": "Squad 1", "hobby": "40K", "faction": "Iron Wolves", "stage": 1, "count": 5,
          "added": "2026-10-01", "log": [["2026-10-01", 1]]}]
DRAFTS = json.dumps({"paste": {"text": "recipe notes " * 12000}})   # about 150 KB
COPY = json.dumps({"date": "2026-11-01", "stages": None, "models": UNITS * 3})

def start(page, extra):
    page.goto(t.URL)
    page.evaluate("""([u, b, s, extra]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        for (const [k, v] of Object.entries(extra || {})) localStorage.setItem(k, v); }""", [UNITS, BOOK, SETTINGS, extra])
    page.reload()
    app_ready(page)
    leave_launch(page)

def stored(page, key):
    return page.evaluate("k => localStorage.getItem(k)", key)

def set_quota(page, spare):
    """Storage is full except for `spare` characters beyond what is used now."""
    page.evaluate("""(spare) => { let used = 0; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); used += k.length + localStorage.getItem(k).length; } window.__quota = used + spare; }""", spare)

def bigger_note(page):
    page.evaluate("() => { models[0].note = 'a longer note '.repeat(30); commit('Saved'); }")
    quiet(page)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, scheme in [(390, 844, "dark"), (360, 640, "light")]:
            print(f"\n=== {width}x{height} {scheme} ===")
            ctx = browser.new_context(viewport={"width": width, "height": height}, service_workers="block", color_scheme=scheme)
            ctx.add_init_script(QUOTA)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))

            start(page, {})
            limit = page.evaluate("DRAFT_TEXT_LIMIT")
            cut = page.evaluate("draftText('x'.repeat(200000)).length")
            note = page.evaluate("draftText('x'.repeat(200000), DRAFT_STEP_NOTE_LIMIT).length")
            check("a draft piece is cut at 50,000 characters or fewer", limit <= 50000 and cut == limit, (limit, cut))
            check("a step note is cut at 2,000", note == 2000, note)

            start(page, {"shades-of-grey-drafts": DRAFTS})
            before = len(stored(page, "shades-of-grey-drafts") or "")
            set_quota(page, 50)
            bigger_note(page)
            saved = json.loads(stored(page, "mini-tracker-models") or "[]")
            check("a full-storage save drops the kept drafts and then works", stored(page, "shades-of-grey-drafts") is None
                  and saved and saved[0].get("note", "").startswith("a longer note"), before)
            check("…so no banner shows", not page.is_visible("#save-banner"))
            page.evaluate("window.__quota = null")

            start(page, {"shades-of-grey-drafts": DRAFTS})
            page.evaluate("""() => { let used = 0; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (k !== 'shades-of-grey-drafts') used += k.length + localStorage.getItem(k).length; } window.__quota = used + 20; }""")
            bigger_note(page)
            check("if dropping drafts is not enough, the banner still shows", page.is_visible("#save-banner"))
            page.evaluate("window.__quota = null")

            # Remove safety copies, with a copy and drafts.
            start(page, {"shades-of-grey-drafts": DRAFTS, "mini-tracker-models-before-restore": COPY})
            set_quota(page, 0)
            page.evaluate("() => { notifyFull(); }")
            check("with drafts and a copy, the full message offers Remove safety copies", page.is_visible("#toast") and "Remove safety copies" in page.text_content("#toast"))
            page.evaluate("offerRemoveSafetyCopies()")
            page.wait_for_selector("#dialog-yes", state="visible")
            msg = page.text_content("#dialog-message")
            check("it says how much room drafts use, in one line", "Unsaved drafts use about" in msg and " KB" in msg, msg)
            page.click("#dialog-yes")
            page.wait_for_selector("#dialog-yes", state="visible")
            check("then offers to throw the drafts away, asking first", "Throw them away" in page.text_content("#dialog-message")
                  and stored(page, "shades-of-grey-drafts") is not None)
            page.click("#dialog-no")
            check("Keep leaves the drafts", stored(page, "shades-of-grey-drafts") is not None)
            check("…and the safety copy was removed", stored(page, "mini-tracker-models-before-restore") is None)

            # Drafts only.
            start(page, {"shades-of-grey-drafts": DRAFTS})
            page.evaluate("showSaveProblem()")
            check("with only drafts, the banner button is still offered", page.is_visible("#banner-copies"))
            page.click("#banner-copies")
            page.wait_for_selector("#dialog-yes", state="visible")
            check("it goes straight to the drafts question", "Unsaved drafts use about" in page.text_content("#dialog-message"))
            page.click("#dialog-yes")
            quiet(page)
            check("Throw away removes the drafts and saves", stored(page, "shades-of-grey-drafts") is None and not page.is_visible("#save-banner"))

            # No drafts: no draft line.
            start(page, {"mini-tracker-models-before-restore": COPY})
            page.evaluate("offerRemoveSafetyCopies()")
            page.wait_for_selector("#dialog-yes", state="visible")
            check("no drafts: no draft line", "draft" not in page.text_content("#dialog-message").lower(), page.text_content("#dialog-message"))
            page.click("#dialog-no")

            # Tap targets of the dialog buttons.
            page.evaluate("offerRemoveSafetyCopies()")
            page.wait_for_selector("#dialog-yes", state="visible")
            boxes = [page.locator(s).bounding_box() for s in ("#dialog-yes", "#dialog-no")]
            check("dialog buttons are 44 px tall or more", all(b and b["height"] >= 44 for b in boxes), boxes)
            check("…and the dialog fits the screen", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            ctx.close()
        check("no page errors", not errors, errors)
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} passed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
