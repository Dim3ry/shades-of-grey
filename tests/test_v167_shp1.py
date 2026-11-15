"""SHP1 test for Minifolio: one word, Wishlist, for the Models list; the "Really want" tick is gone. New behaviour only.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_v31 as t
from launch_helpers import tap_tab

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

ROOT = os.path.dirname(HERE)
STAGES = ["Boxed", "Built", "Primed", "Painted"]
UNIT = {"id": 1, "name": "Squad", "hobby": "Skirmish", "faction": "Bright Host", "stage": 1, "count": 3, "added": "2026-09-01", "log": [["2026-09-01", 1]]}
OLD = {"id": 4, "name": "Old Guard", "count": 2, "game": "Skirmish", "faction": "Bright Host", "really": True, "note": "n", "added": "2026-10-01"}
PLAIN = {"id": 5, "name": "Scouts", "count": 1, "game": "", "faction": "", "really": False, "note": "", "added": "2026-10-02"}

def main():
    errors = []
    print("\n--- 1. No UI string still says Wanted ---")
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    app = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
    # old Updates entries are history: they are whole-line quoted strings in a list, so those lines are skipped
    app_ui = "\n".join(l for l in app.split("\n") if not re.match(r'^\s+"[^"]*",?\s*$', l))
    shown = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
    check("index.html text has no Wanted or Really want", not re.search(r"\bWanted\b|Really want", re.sub(r"<[^>]+>", " ", shown)), "")
    left = [m for m in re.findall(r"[\"'`][^\"'`\n]*(?:\bWanted\b|\bwanted (?:model|yet)|Really want|Wish list)[^\"'`\n]*[\"'`]", app_ui)
            if "named(blend.target" not in m and "Wanted\"" not in m]
    check("app.js strings (outside the Updates list) have no wanted model, Really want or Wish list", not left, left[:3])
    check("the switch and the Help topic say Wishlist",
          'data-mview="wishes" aria-selected="false">Wishlist<' in html and "<strong>Wishlist</strong> switch" in html)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640), (320, 640)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page(); page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, units=[UNIT], settings={"examplesChecked": True, "stages": STAGES, "modelWishes": [OLD, PLAIN]})
            page.click('nav button[data-tab="units"]'); t.quiet(page)
            page.click('#models-seg button[data-mview="wishes"]'); page.wait_for_selector("#wish-view:not(.hidden)")
            if w == 390:
                print("\n--- 2. The screen reads Wishlist, nothing shows Really want ---")
                check("the switch reads Models | Wishlist", page.evaluate("[...document.querySelectorAll('#models-seg button')].map(b => b.textContent.trim())") == ["Models", "Wishlist"])
                check("the count line", page.inner_text("#wish-count").strip() == "3 Wishlist models", page.inner_text("#wish-count"))
                check("a group heading reads N on Wishlist", "on Wishlist" in page.inner_text("#wish-list") and "wanted" not in page.inner_text("#wish-list").lower())
                check("an item with the old really flag shows no label", "Really" not in page.inner_text("#wish-list"))
                page.click("#wish-add")
                check("the form has no Really want tick", page.locator(".wish-form .w-really").count() == 0 and "Really" not in page.inner_text(".wish-form"))
                page.click(".w-cancel")
                page.locator(".wish-info", has_text="Old Guard").click()
                page.fill(".wish-form .w-note", "edited"); page.click(".wish-form button[type=submit]")
                saved = json.loads(page.evaluate("localStorage.getItem('shades-of-grey-settings')"))["modelWishes"]
                check("editing keeps the stored really flag", [x for x in saved if x["id"] == 4][0]["really"] is True and [x for x in saved if x["id"] == 4][0]["note"] == "edited", saved)
                print("\n--- 3. Got it and Undo still work ---")
                page.locator("li.wish-row", has_text="Scouts").locator(".wish-got").click()
                check("Got it moves it to Models", page.evaluate("models.some(m => m.name === 'Scouts')") and page.evaluate("wishes().length") == 1)
                page.click("#toast button") if page.locator("#toast button").count() else None
                page.wait_for_timeout(300)
                check("Undo puts it back on the Wishlist", page.evaluate("wishes().length") == 2 and not page.evaluate("models.some(m => m.name === 'Scouts')"))
                print("\n--- 4. Backup and restore ---")
                t.load(page, units=[UNIT], settings={"examplesChecked": True, "stages": STAGES, "modelWishes": [PLAIN]})
                tap_tab(page, "settings"); t.quiet(page)
                data = {"app": "Minifolio", "dataVersion": 2, "models": [UNIT], "modelWishes": [OLD]}
                page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(data).encode()}])
                page.wait_for_selector("#dialog-backdrop:not(.hidden)")
                q = page.text_content("#dialog-message")
                check("the restore question says Wishlist model", "Wishlist model" in q and "wanted" not in q.lower(), q)
                page.click("#dialog-yes"); page.wait_for_timeout(700)
                back = page.evaluate("wishes().map(w => [w.name, w.really])")
                check("the old really item restored without error and keeps its flag", back == [["Old Guard", True]], back)
                check("no page error", not errors, errors)
            else:
                check(f"{w} wide: no sideways scroll on the Wishlist", page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            ctx.close()
        browser.close()
    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) and not errors else 1)

if __name__ == "__main__":
    main()
