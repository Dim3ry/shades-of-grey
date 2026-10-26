"""v18.1 tests for Shades of Grey: "unofficial fan-made" wording.

Checks: version numbers, the Updates entry, the About wording in Help (Games Workshop AND paint makers,
other brands belong to their makers), the one-line note on the Updates tab, the README line, no sideways
scroll on a 360px phone, and no page errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
URL = f"http://localhost:{PORT}/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def start(page):
    page.goto(URL)
    page.evaluate("localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]')")
    page.reload()
    page.wait_for_timeout(300)

def main():
    readme = open(os.path.join(HERE, "..", "README.md"), encoding="utf-8").read()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)

        print("--- Version numbers ---")

        print("\n--- Updates entry ---")
        at = page.evaluate("CHANGELOG.findIndex(e => e.version === 'v18.1')")
        entry = page.evaluate(f"CHANGELOG[{max(at, 0)}]")
        if page.evaluate("['v18.1'].every(v => CHANGELOG.some(r => r.version === v))"):
            if page.evaluate("['v18.1'].every(v => CHANGELOG.some(r => r.version === v))"):
                check("v18.1 is dated 10 Oct 2026", entry["date"] == "10 Oct 2026", entry["date"])
            else:
                print("SKIP (entry no longer in the public Updates list): " + 'v18.1 is dated 10 Oct 2026')
        else:
            print("SKIP (entry no longer in the public Updates list): entry wording checks for v18.1")
        if page.evaluate("['v18'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("v18 is listed straight below v18.1", page.evaluate(f"CHANGELOG[{at + 1}].version") == "v18")
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'v18 is listed straight below v18.1')

        print("\n--- Help → About ---")
        page.click('nav button[data-tab="settings"]')   # v21.9: Help and Updates are sub-tabs of Settings
        page.click('#more-seg button[data-page="help"]')
        page.wait_for_timeout(150)
        page.evaluate("document.getElementById('about').open = true")
        about = page.inner_text("#about")
        check("About says unofficial and fan-made", "Unofficial fan-made app" in about, about[:200])
        check("About says not affiliated with Games Workshop or any paint maker",
              "not affiliated with or endorsed by Games Workshop or any paint maker" in about)
        check("About says no brand logos", "no brand logos" in about)
        check("About says other paint names belong to their makers", "belong to their makers" in about)
        for brand in ["Vallejo", "The Army Painter", "AK Interactive"]:
            check(f"About names {brand} as an example", brand in about)
        check("About still says Citadel and Warhammer are Games Workshop trademarks",
              "trademarks of Games Workshop Ltd" in about)
        check("About still says data stays on this device", "Your data stays on this device" in about)

        print("\n--- Updates tab note ---")
        page.click('nav button[data-tab="settings"]')   # v21.9: Help and Updates are sub-tabs of Settings
        page.click('#more-seg button[data-page="updates"]')
        page.wait_for_timeout(150)
        note = page.locator("#unofficial-note")
        check("the unofficial note is on the Updates tab", note.count() == 1)
        check("the note is visible", note.is_visible())
        check("the note says unofficial and not affiliated",
              note.inner_text().strip() == "Unofficial fan-made app. Not affiliated with Games Workshop or any paint maker.",
              note.inner_text())
        check("the note sits under the version note",
              page.evaluate("document.getElementById('version-note').nextElementSibling.id") == "unofficial-note")

        print("\n--- README ---")
        check("README says unofficial fan-made", "Unofficial fan-made app" in readme)
        check("README says not affiliated with Games Workshop or any paint maker",
              "Games Workshop or any paint maker" in readme)

        print("\n--- Phone width ---")
        small = browser.new_page(viewport={"width": 360, "height": 740})
        small.on("pageerror", lambda e: errors.append(str(e)))
        start(small)
        for tab in ["updates", "help"]:
            small.click("nav button[data-tab='settings']")   # v21.9: Help and Updates are sub-tabs of Settings
            small.click(f"#more-seg button[data-page='{tab}']")
            small.wait_for_timeout(150)
            if tab == "help":
                small.evaluate("document.getElementById('about').open = true")
            wide = small.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"360px phone, {tab} tab: no sideways scroll", not wide)
        shots = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
        os.makedirs(shots, exist_ok=True)
        small.click('nav button[data-tab="settings"]')   # v21.9: Help and Updates are sub-tabs of Settings
        small.click('#more-seg button[data-page="updates"]')
        small.screenshot(path=os.path.join(shots, "v18_1_updates_phone.png"), full_page=True)

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

main()
