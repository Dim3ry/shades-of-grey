"""Chunk DS1 tests for Minifolio, part 2: the offline helper (the service worker) serves one version of the app at a time.
1. A newer page whose code files can't be fetched is not run with the older code: the saved page (and its code) is used.
2. A newer page whose code files can be fetched is used, with its own code.
3. An error from the host (500) gets the saved copy of the page; a redirect is followed.
4. Offline after that, the page and its code are still one version.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys, time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import app_ready

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = re.compile(r'src="[^"]+\.js.v=(\d+)"')

def is_page(url):
    return urlparse(url).path in ("/", "/index.html")

def tags(page):
    """The version numbers on every code file the page in the browser names (one number = one version)."""
    return sorted(set(TAG.findall(page.content())))

def main():
    errors = []
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    now = TAG.findall(html)[0]
    newer = re.sub(r'(src="[^"]+\.js.)v=\d+', r"\g<1>v=9999", html)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(t.URL)
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
        page.wait_for_function("() => caches.keys().then(n => n.length > 0)", timeout=15000)
        page.wait_for_timeout(500)

        # 1. A newer page, but its code files fail.
        ctx.route(is_page, lambda route: route.fulfill(status=200, content_type="text/html", body=newer))
        newer_code = re.compile(r"\.js.v=9999")
        ctx.route(newer_code, lambda route: route.abort("internetdisconnected"))
        page.reload(); app_ready(page)
        check("newer page with code files that fail: the saved page is used, all one version", tags(page) == [now], tags(page))
        check("…and the app runs", page.evaluate("typeof models") == "object")

        # 2. A newer page whose code files arrive.
        ctx.unroute(newer_code)
        # T6: the offline helper waits at most 4 s (its PAGE_WAIT_MS) for the new page and all its code files; after that it shows
        # the saved page on purpose (a slow connection) and keeps fetching, so the next load is the new one. On a busy machine the
        # fetching alone took longer than 4 s and this check saw the old version. So: the newer page on this load, or, only when this
        # load really waited the 4 s, on the next one. A helper that never uses the newer page still fails.
        started = time.time()
        page.reload(); app_ready(page)
        waited = time.time() - started
        first = tags(page)
        if first != ["9999"] and waited >= 4:
            print(f"   (the newer page took longer than the helper's 4 s wait here: this load took {waited:.1f} s; loading again)")
            page.wait_for_timeout(1000)
            page.reload(); app_ready(page)
        check("newer page with code files that arrive: the newer page is used", tags(page) == ["9999"], (first, tags(page), round(waited, 1)))
        check("…with its own code", page.evaluate("[...document.scripts].every(s => !s.src || s.src.endsWith('v=9999') || !/\\.js/.test(s.src))")
              and page.evaluate("typeof models") == "object")

        # 3. The host answers with an error.
        ctx.unroute(is_page)
        ctx.route(is_page, lambda route: route.fulfill(status=500, content_type="text/html", body="Server error"))
        page.reload(); app_ready(page)
        check("a 500 from the host: the saved copy of the page opens", page.title() == "Minifolio" and page.evaluate("typeof models") == "object",
              page.title())

        # 3b. A redirect from the host is followed, not treated as an error.
        ctx.unroute(is_page)
        ctx.route(is_page, lambda route: route.fulfill(status=302, headers={"Location": "/index.html"}) if "go=1" in route.request.url
                  else route.continue_())
        page.goto(t.BASE + "?go=1"); app_ready(page)
        check("a redirect from the host is followed", page.url.endswith("/index.html") and page.evaluate("typeof models") == "object", page.url)

        # 4. Offline afterwards.
        ctx.unroute(is_page)
        ctx.set_offline(True)
        page.reload(); app_ready(page)
        check("offline afterwards: the page and its code are one version", len(tags(page)) == 1 and page.evaluate("typeof models") == "object",
              tags(page))
        ctx.set_offline(False)

        check("no page errors", not errors, errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
