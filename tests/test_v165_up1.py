"""UP1 test for Minifolio (finding c2: no "new version ready" message). New behaviour only, in a real browser with two real service worker versions.
1. First install: no message. A new version taking over while the page is open: one "New version ready" bar with Reload and Dismiss.
2. The page is not reloaded by itself; Dismiss removes the bar; a second new version does not bring it back; a fresh open has none.
3. The bar is clear of sideways scroll and its buttons are 44 px or more, at 390 and 360 px wide, dark and light.
4. The label reader worker is asked for and saved with a version tag on its address, like the scripts.
The test serves a temporary copy of the app folder and edits that copy's helper script between steps, so the second version is real.
(It does not check the app's own version number: the plumbing test does that.)
Run all tests with `python3 tests/run_all.py`, or run this file on its own."""
import os, re, shutil, sys, tempfile, threading, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:300]}"))

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.split("?")[0] == "/privacy": self.path = "/privacy.html"   # the host serves the privacy page at its clean address
        super().do_GET()
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

HELPER = "sw" + os.extsep + "js"   # the offline helper script (the copy of it is the only file the test changes)

def make_copy():
    d = tempfile.mkdtemp(prefix="up1-")
    for name in os.listdir(ROOT):
        if name in (".git", "tests", "node_modules"): continue
        src = os.path.join(ROOT, name)
        if name == HELPER: shutil.copy(src, os.path.join(d, name))
        else: os.symlink(src, os.path.join(d, name))
    return d

def set_sw_version(d, tag):
    p = os.path.join(d, HELPER)
    s = open(p, encoding="utf-8").read()
    s = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "{tag}";', s, count=1)
    open(p, "w", encoding="utf-8").write(s)

BAR = ".up1-bar"
def push_update(page, wait_for_bar=True):
    """Ask the browser to look for the new helper script (retrying: a still-settling older helper can make one ask miss it)."""
    for _ in range(12):
        page.evaluate("navigator.serviceWorker.getRegistration().then(r => r.update())")
        if not wait_for_bar or count(page): return
        page.wait_for_timeout(1000)
def count(page): return page.locator(BAR).count()
def main():
    d = make_copy()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=d))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, scheme in ((390, 844, "dark"), (360, 640, "light")):
            print(f"\n--- {w}px, {scheme} ---")
            set_sw_version(d, "v164")
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            page.goto(url)
            page.wait_for_function("() => navigator.serviceWorker.ready.then(() => true)", timeout=15000)
            page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)
            page.wait_for_timeout(500)
            check("first install shows no message", count(page) == 0, count(page))
            keys = page.evaluate("caches.keys().then(async ks => { const out = []; for (const k of ks) { const c = await caches.open(k); out.push(...(await c.keys()).map(r => r.url)); } return out; })")
            check("the label reader worker is saved with a version tag", any(re.search(r"/ocr/ocr-worker\.js[?]v=\d+$", u) for u in keys), [u for u in keys if "worker" in u])
            src_js = "() => fetch(document.querySelector('script[src^=app]').src).then(r => r.text()).then(t => t.includes('ocrWorkerUrl') && /ocr-worker[.]js[?]v=/.test(t))"
            check("the page asks for the worker with a version tag", page.evaluate(src_js))
            page.evaluate("window.__still = 1")
            # a second, real version of the helper script
            set_sw_version(d, "v164-up1")
            push_update(page)
            page.wait_for_selector(BAR, timeout=3000)
            check("a new version taking over shows one bar", count(page) == 1, count(page))
            check("it says New version ready and has Reload", page.locator(BAR).inner_text().startswith("New version ready") and page.locator("#up1-reload").inner_text() == "Reload", page.locator(BAR).inner_text())
            check("the page was not reloaded by itself", page.evaluate("window.__still") == 1)
            box = page.locator(BAR).bounding_box()
            check("no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            check("the bar sits inside the screen", box and box["x"] >= 0 and box["x"] + box["width"] <= w, box)
            small = [b for b in ("#up1-reload", "#up1-dismiss") if (lambda r: r["width"] < 44 or r["height"] < 44)(page.locator(b).bounding_box())]
            check("both buttons are 44 px or more", not small, small)
            page.click("#up1-dismiss")
            check("Dismiss removes the bar", count(page) == 0)
            set_sw_version(d, "v164-up2")
            push_update(page, wait_for_bar=False)
            page.wait_for_timeout(2500)
            check("a later version does not bring it back on the same open", count(page) == 0, count(page))
            page.reload(); page.wait_for_function("() => navigator.serviceWorker.ready.then(() => !!navigator.serviceWorker.controller)"); page.wait_for_timeout(1500)
            check("opening the app again shows no bar", count(page) == 0, count(page))
            # Reload button really reloads
            set_sw_version(d, "v164-up3")
            push_update(page)
            page.wait_for_selector(BAR, timeout=3000)
            page.evaluate("window.__still = 1")
            with page.expect_navigation(): page.click("#up1-reload")
            check("Reload reloads the page and the bar is gone", page.evaluate("window.__still") is None and count(page) == 0)
            ctx.close()
        browser.close()
    srv.shutdown(); shutil.rmtree(d, ignore_errors=True)
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
