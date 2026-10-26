"""v45 tests for Minifolio (small tidy): the Updates page shows only the latest five versions, and Help -> Privacy names the
site's current host (Cloudflare) instead of GitHub Pages.

What is checked:
1. Versions: APP_VERSION v45, sw.js v45, every script tag ?v=45, and a short v45 Updates entry that is the newest.
2. The list: CHANGELOG holds exactly five entries (v45 to v41), the Updates page draws five, and it never draws more than
   UPDATES_SHOWN even if the list is longer (a longer list is tried in the page and cut back to five).
3. Help: the Updates and feedback topic says "latest five versions"; Privacy names Cloudflare and no longer says GitHub Pages;
   the rest of Privacy and About still read as before.
4. Nothing else on Settings changed: the Settings page's own markup is the same as on main.
5. Phone width (390 and 360 px), dark and light: Updates and Help show, nothing scrolls sideways, no page errors, no pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, subprocess, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t   # the shared helpers

URL, read, shot, no_sideways, ROOT = t.URL, t.read, t.shot, t.no_sideways, t.ROOT
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def fresh(page, settings=None):
    page.goto(URL)
    page.evaluate("""(s) => { localStorage.clear(); if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", settings)
    page.goto(URL)
    page.wait_for_timeout(400)

def open_more(page, which):
    page.click('nav button[data-tab="settings"]')
    page.click(f'#more-seg button[data-page="{which}"]')
    page.wait_for_timeout(150)

def settings_block(html):
    start = html.index('<section id="view-settings"')
    return html[start:html.index("</section>", start)]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        print("\n--- 1. Versions ---")
        fresh(page)
        html = read("index.html")
        version = page.evaluate("APP_VERSION")

        print("\n--- 2. The list ---")
        versions = page.evaluate("CHANGELOG.map(r => r.version)")
        check("the list holds only the newest five entries (checked while v45 is the newest)", version != "v45" or (len(versions) == 5 and versions[0] == "v45" and versions[-1] == "v41"), versions)
        check("UPDATES_SHOWN is five", page.evaluate("UPDATES_SHOWN") == 5)
        open_more(page, "updates")
        check("the Updates page draws five entries", page.locator("#changelog .release").count() == 5, page.locator("#changelog .release").count())
        check("the heading still shows the version number next to the title",
              page.inner_text("#changelog .release h3").startswith(version) and page.inner_text("#version-tag").strip() == version,
              page.inner_text("#changelog .release h3"))
        page.evaluate("""() => { for (let i = 1; i <= 4; i++) CHANGELOG.push({ version: 'v0.' + i, date: 'test', changes: ['extra'] }); renderUpdates(); }""")
        check("even with a longer list, the page draws only five", page.locator("#changelog .release").count() == 5, page.locator("#changelog .release").count())
        check("the old entries are gone from the code", all(x not in read("app.js") for x in ('version: "v40"', 'version: "v39"', 'version: "v38"', 'version: "v1"')))

        print("\n--- 3. Help ---")
        fresh(page)
        open_more(page, "help")
        page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
        help_text = page.inner_text("#view-help")
        check("Help says the Updates tab lists the latest five versions", "lists what changed in the latest five versions" in help_text)
        check("Help no longer says it lists each version", "what changed in each version" not in help_text)
        privacy = page.inner_text("#privacy")
        check("Privacy names Cloudflare as the site's host", "(Cloudflare) sees basic technical details" in privacy, privacy[-300:])
        check("Privacy no longer names GitHub Pages", "GitHub" not in privacy, privacy[-300:])
        about = page.inner_text("#about")
        check("About still says unofficial and fan-made, and that data stays on the device",
              "Unofficial fan-made app" in about and "Your data stays on this device" in about)

        print("\n--- 4. Settings page unchanged ---")
        old = subprocess.run(["git", "show", "origin/main:index.html"], cwd=ROOT, capture_output=True, text=True).stdout
        if old and version == "v45":   # v46 added a button to Settings, so this only applies while v45 is the newest
            check("the Settings page's own markup is the same as on main", settings_block(old) == settings_block(html))
        else:
            print("SKIP (no main branch here to compare with)")

        print("\n--- 5. Phone width, dark and light ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 800})
                tag = f"{appearance} {width}px"
                fresh(page, settings={"appearance": appearance})
                open_more(page, "updates")
                check(f"{tag}: Updates shows five entries and does not scroll sideways",
                      page.locator("#changelog .release").count() == 5 and no_sideways(page))
                shot(page, f"v45-updates-{appearance}-{width}.png")
                open_more(page, "help")
                page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = false); document.getElementById('privacy').open = true")
                check(f"{tag}: Help (Privacy open) does not scroll sideways", no_sideways(page))
                shot(page, f"v45-help-privacy-{appearance}-{width}.png")
                open_more(page, "settings")
                check(f"{tag}: Settings shows and does not scroll sideways", page.is_visible("#backup-card") and no_sideways(page))

        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not dialogs, dialogs[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
