"""FX5 test for Minifolio (failure messages people can act on). New behaviour only, with real taps.
1. Storage that throws shows the Not saved banner with Save backup from the start-up; working storage never shows it.
2. A cut-off or empty backup says so and changes nothing; a complete file that is not a backup keeps the old words.
3. A file that can't be read (restore and CSV import) says so plainly and resets the file box.
4. If the app never finishes starting, "Minifolio could not start. Reload the page." shows; never when it started.
5. The label reader shows plain words, not engine messages; first use with no connection says about 11 MB and points to typing.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready, leave_launch

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

BLOCK = "Storage.prototype.setItem = function () { throw new DOMException('blocked', 'SecurityError'); };"
def toast(page): return page.evaluate("document.getElementById('toast-text').textContent")
def banner(page): return page.evaluate("({shown: !document.getElementById('save-banner').classList.contains('hidden'), text: document.getElementById('save-banner-text').textContent})")
def pick(page, sel, name, data):
    page.set_input_files(sel, files=[{"name": name, "mimeType": "application/json", "buffer": data}]); page.wait_for_timeout(400)
def no_sideways(page): return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, scheme in ((390, 844, "dark"), (360, 640, "light")):
            print(f"\n--- {w}px, {scheme} ---")
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page)
            check("working storage: no banner at start-up", not banner(page)["shown"], banner(page))
            check("the start-up message is not shown when start-up worked", page.evaluate("!document.getElementById('start-failed')"))
            page.wait_for_timeout(4500)
            check("still not shown after the wait", page.evaluate("!document.getElementById('start-failed')"))

            # 2. backups
            pick(page, "#restore-file", "cut.json", b'{"models":[{"name":"A')
            check("cut-off backup: says cut off and nothing changed", "cut off" in toast(page) and "nothing was changed" in toast(page), toast(page))
            pick(page, "#restore-file", "empty.json", b"")
            check("empty file: says cut off", "cut off" in toast(page), toast(page))
            pick(page, "#restore-file", "plain.json", b'"hello"')
            check("complete file that is not a backup keeps the old words", toast(page) == "That file doesn't look like a Minifolio backup.", toast(page))
            check("restore box is reset after each", page.evaluate("document.getElementById('restore-file').value") == "")

            # 3. read errors
            page.evaluate("() => { window.__read = FileReader.prototype.readAsText; FileReader.prototype.readAsText = function () { setTimeout(() => this.onerror && this.onerror(), 0); }; }")
            pick(page, "#restore-file", "gone.json", b"{}")
            check("restore read error: plain message", "couldn't be read" in toast(page) and "nothing was changed" in toast(page), toast(page))
            check("restore read error: input reset", page.evaluate("document.getElementById('restore-file').value") == "")
            page.set_input_files("#csv-file", files=[{"name": "gone.csv", "mimeType": "text/csv", "buffer": b"a,b"}]); page.wait_for_timeout(400)
            shown = page.evaluate("document.body.textContent")
            check("CSV read error: plain message", "couldn't be read, so nothing was imported" in shown)
            check("CSV read error: input reset", page.evaluate("document.getElementById('csv-file').value") == "")
            page.evaluate("() => { FileReader.prototype.readAsText = window.__read; }")

            # 5. label reader words (the function the scan panel uses)
            msgs = page.evaluate("""[new Error("Failed to execute 'importScripts' on 'WorkerGlobalScope'"), new Error("Aborted(RuntimeError: memory access out of bounds)"),
                new Error("Couldn't load the label reader's English data."), new Error("Couldn't read that picture.")].map(plainLabelError)""")
            check("engine messages become plain words", all("importScripts" not in m and "RuntimeError" not in m for m in msgs), msgs)
            check("a failed first load says it needs a connection, 11 MB, and points to typing",
                  "connection" in msgs[0] and "11 MB" in msgs[0] and "Type the name" in msgs[0], msgs[0])
            check("another failure points to typing too", "Type the name below" in msgs[1] and "connection" not in msgs[1], msgs[1])
            check("a plain own message is kept", msgs[3] == "Couldn't read that picture.", msgs[3])
            check("no sideways scroll", no_sideways(page))
            ctx.close()

            # 1. blocked storage
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.add_init_script(BLOCK)
            page.goto(t.URL); app_ready(page); leave_launch(page)
            b = banner(page)
            check("blocked storage: banner shows from start-up", b["shown"] and "can't be saved" in b["text"], b)
            check("the banner has Save backup, tappable at 44 px", page.evaluate("(() => { const r = document.getElementById('banner-backup').getBoundingClientRect(); return r.height >= 44 && r.width >= 44; })()"))
            page.click('nav button[data-tab="units"]'); page.wait_for_timeout(300)
            check("the banner stays after the app does a save", banner(page)["shown"])
            page.click("#banner-retry"); page.wait_for_timeout(300)
            check("Try again while still blocked says so and keeps the banner", "Still can't save" in toast(page) and banner(page)["shown"], toast(page))
            check("blocked: no sideways scroll", no_sideways(page))
            ctx.close()

            # 4. app fails to start (app.js blocked)
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, service_workers="block")
            page = ctx.new_page()
            page.route("**/app.js*", lambda r: r.abort())
            page.goto(t.URL); page.wait_for_timeout(5500)
            msg = page.evaluate("(() => { const e = document.getElementById('start-failed'); return e ? e.textContent : null; })()")
            check("failed start: plain message with Reload", msg is not None and "Minifolio could not start. Reload the page." in msg, msg)
            check("failed start: no sideways scroll", no_sideways(page))
            ctx.close()
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
