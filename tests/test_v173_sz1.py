"""SZ1 tests for Minifolio: the Updates list (the Updates list) moved out of app.js into its own file, changelog.js. New behaviour only.
1. The list lives in changelog.js (once), no longer in app.js, and the page asks for changelog.js before app.js.
2. The list still works as a plain top-level name: the newest entry is first, older ones follow in order, nothing was dropped.
3. The Updates screen still draws exactly the newest UPDATES_SHOWN entries, newest first, and the page shows no error.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import version_helpers as vh
from launch_helpers import leave_launch

ROOT = t.ROOT
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def main():
    errors, requested = [], []
    print("\n--- 1. Where the list lives ---")
    log = vh.changelog_source()
    app = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
    check("changelog.js holds the list once", len(re.findall(r"^    const [A-Z]+ = \[$", log, re.M)) == 1 and "{ version: \"v100\"" in log)
    check("app.js no longer holds the list", "{ version: \"v100\"" not in app and "{ version: \"v45\"" not in app)
    check("the file is big (the whole history moved, not a stub)", len(log) > 50000, len(log))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("request", lambda r: requested.append(r.url.split("?")[0].rsplit("/", 1)[-1]))
        t.load(page, settings={"tab": "updates", "examplesChecked": True})
        leave_launch(page)

        check("the page asked for changelog.js before app.js",
              "changelog.js" in requested and "app.js" in requested and requested.index("changelog.js") < requested.index("app.js"), requested)

        print("\n--- 2. The list as a name the app and tests read ---")
        entries = vh.changelog_entries(page)
        names = [e["version"] for e in entries]
        check("the list is there with its whole history", len(entries) >= 100, len(entries))
        check("newest first, older after it (the newest two are consecutive versions)",
              vh.parse(names[0]) > vh.parse(names[1]) and names[0] == vh.current(), names[:3])
        check("every entry has a version, a date and at least one line",
              all(e.get("version") and e.get("date") and e.get("changes") for e in entries))
        check("version_helpers still finds the entries through the page", vh.has_entry(page, vh.current()) and vh.has_entry(page, "v45"))

        print("\n--- 3. The Updates screen ---")
        page.evaluate("renderUpdates()")
        shown = page.evaluate("UPDATES_SHOWN")
        check("the Updates screen is open", page.evaluate("settings.tab") == "updates", page.evaluate("settings.tab"))
        drawn = page.evaluate("() => [...document.querySelectorAll('#changelog .release h3')].map(h => h.firstChild.textContent)")
        check("it draws the newest UPDATES_SHOWN entries, newest first, and no more", drawn == names[:shown] and len(drawn) == shown, (shown, drawn))
        check("no page error", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
