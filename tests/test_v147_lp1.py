"""LP1 tests for Minifolio (the privacy page and the rights line). New behaviour only:
1. privacy.html: title, headings, the 12 months line, no leftover {DATE} or {FEEDBACK_PATH}, no script, nothing loaded from another site.
2. The rights line is in About, in How it works > About (where the fan-made notice was) and in the page footer; "their own licences" opens Credits.
3. The links to the page from About, How it works > Privacy, Credits and Settings.
4. The page itself at 320, 360, 390 and 1280 px, dark and light: no sideways scroll, 16 px text, contrast 4.5, no requests but its own.
5. The service worker never answers the privacy page with the app's page, and the page opens offline after one visit.
(Left to tests/test_version_plumbing.py: the version, the service worker's file list and the Updates entry.)
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import open_settings, wait_settled

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

PAGE = open(os.path.join(ROOT, "privacy.html"), encoding="utf-8").read()
HTML = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

class CleanUrls(SimpleHTTPRequestHandler):
    """Serves the repo like the host does: /privacy gives privacy.html."""
    def translate_path(self, path):
        if path.split("?")[0] == "/privacy":
            path = "/privacy.html"
        return super().translate_path(path)
    def log_message(self, *a):
        pass

def start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(CleanUrls, directory=ROOT))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"

# Contrast of the body text, a link and the footer text against the page colour, and the layout, in one go.
MEASURE = """() => {
    const lum = (c) => { const [r, g, b] = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    const bg = getComputedStyle(document.body).backgroundColor;
    const col = (s) => getComputedStyle(document.querySelector(s)).color;
    const back = document.querySelector('.back').getBoundingClientRect();
    return { sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth,
             font: parseFloat(getComputedStyle(document.body).fontSize), minFont: Math.min(...[...document.querySelectorAll('main *, footer *')].map(e => parseFloat(getComputedStyle(e).fontSize))),
             body: ratio(col('main p'), bg), link: ratio(col('main a:not(.back)'), bg), foot: ratio(col('#rights-line'), bg), updated: ratio(col('.updated'), bg),
             backH: back.height, backW: back.width, scripts: document.scripts.length };
}"""

def main():
    errors = []
    low = PAGE.lower()
    # ---- 1. the file ----
    check("the page is titled Minifolio privacy", "<title>Minifolio privacy</title>" in PAGE)
    heads = ["What Minifolio does receive, and why", "Who runs it.", "The short version.", "What stays on your device.", "Who else gets data.",
             "Your rights.", "Complaints.", "Children.", "Changes.", "Visit counts (GoatCounter).", "Feedback (Tally).", "Hosting (Cloudflare)."]
    check("every heading of the signed-off text is there", all(h in PAGE for h in heads), [h for h in heads if h not in PAGE])
    check("the 12 months line is there", "They are deleted after 12 months, or sooner if you ask." in PAGE)
    check("no {DATE} or {FEEDBACK_PATH} token is left, and both were filled",
          "{DATE}" not in PAGE and "{FEEDBACK_PATH}" not in PAGE and re.search(r"Last updated: \d{1,2} [A-Z][a-z]+ 2026", PAGE) and "(Tools and Settings, then Updates)" in PAGE)
    check("no script tag, no event handler, no em dash", "<script" not in low and not re.search(r"\son[a-z]+=", low) and "—" not in PAGE)
    loads = re.findall(r"<(?:script|link|img|iframe|source|embed|object|video|audio)\b[^>]*", low)
    check("nothing is loaded from another site (no tag that loads anything, no url() or @import)", not loads and "url(" not in low and "@import" not in low, loads)
    check("the page's own security policy lets in no script and no other site",
          "default-src 'none'" in PAGE and "script-src" not in PAGE and "connect-src" not in PAGE)
    check("no tracking script or counter is named on the page", "goatcounter.com" not in low and "gtag" not in low)

    # ---- 2 and 3. the app side ----
    rights_start = "Minifolio is an independent app made in the UK by George Atter-Dimery."
    server, base = start_server()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        # the run_all test server has no /privacy; give it the page the way the host does, and count what it is asked for
        ctx.route("**/privacy", lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE))
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.goto(t.URL)
        wait_settled(page)
        open_settings(page)
        page.click('#more-seg button[data-page="about"]')
        page.wait_for_timeout(150)
        about = page.inner_text("#view-about")
        foot = re.sub(r"\s+", " ", re.search(r'<p id="rights-line">(.*?)</p>', PAGE, re.S).group(1))
        foot = re.sub(r"<[^>]+>", "", foot).strip()
        check("About carries the rights line, word for word as in the page footer", re.sub(r"\s+", " ", page.inner_text("#about-rights")).strip() == foot, page.inner_text("#about-rights")[:120])
        check("About keeps its About and Mission text", about.count("Mission") >= 1 and "To give every painter a mentor in their pocket" in about)
        page.click("#about-rights-credits")
        # FB3: Credits is a section of About now, so the link scrolls to it and About stays open
        check("'their own licences' in About scrolls to the Credits section", page.is_visible("#view-credits") and page.is_visible("#view-about"))
        page.click('#more-seg button[data-page="help"]')
        page.evaluate("document.getElementById('about').open = true")
        help_about = re.sub(r"\s+", " ", page.inner_text("#about"))
        check("How it works > About has the rights line where the fan-made notice was",
              rights_start in help_about and "Unofficial fan-made app, not affiliated" not in help_about and "No Games Workshop artwork, rules, points or stats" in help_about)
        page.click("#help-rights-credits")
        check("'their own licences' in How it works opens About at the Credits section", page.is_visible("#view-credits") and page.is_visible("#view-about"))   # FB3
        check("the page footer's 'their own licences' link goes to the app's Credits page",
              'id="rights-credits-link" href="./#credits"' in PAGE and re.search(r"under <a [^>]*>their own licences</a>\.", PAGE) is not None)

        # links
        def opens(selector, where):
            """Taps a link and checks that it opens the privacy page in a new tab, and that the app is still where it was."""
            with ctx.expect_page() as popup:
                page.click(selector)
            tab = popup.value
            ok = tab.url.endswith("/privacy") and tab.title() == "Minifolio privacy"
            tab.close()
            return ok
        page.click('#more-seg button[data-page="about"]')
        h = page.evaluate("() => document.getElementById('about-privacy-link').getBoundingClientRect().height")
        check("About: one plain link opens the page in a new tab, 44 px tall, and About stays open", h >= 44 and opens("#about-privacy-link", "about") and page.is_visible("#view-about"))
        # FB3: the Credits section has no privacy link of its own any more (About's sits directly above it, on the same page)
        page.click('#more-seg button[data-page="settings"]')
        page.evaluate("() => { const b = document.getElementById('card-fold-your-data-button'); if (b.getAttribute('aria-expanded') !== 'true') b.click(); }")   # FB3: Counting visits is a part of Your data, which is a fold
        check("Settings: the link by Counting visits opens the page and Settings stays open", opens("#settings-privacy-link", "settings") and page.is_visible("#view-settings"))
        page.click('#more-seg button[data-page="help"]')
        page.evaluate("document.getElementById('privacy').open = true")
        check("How it works > Privacy: one line links to the full page, the rest of the topic is kept",
              opens("#help-privacy-link", "help") and page.locator("#privacy li").count() >= 10 and "Counting visits" in page.inner_text("#privacy"))
        check("all three links point at /privacy and open in a new tab without handing over the app",
              page.evaluate("() => ['about-privacy-link','settings-privacy-link','help-privacy-link'].every(id => { const a = document.getElementById(id); return a.getAttribute('href') === 'privacy' && a.target === '_blank' && a.rel.includes('noopener'); })"))

        # ---- 4. the page itself ----
        for scheme in ("dark", "light"):
            for w, hgt in ((320, 568), (360, 640), (390, 844), (1280, 800)):
                c = browser.new_context(viewport={"width": w, "height": hgt}, color_scheme=scheme, service_workers="block")
                q = c.new_page()
                asked = []
                q.on("request", lambda r: asked.append(r.url))
                q.on("pageerror", lambda x: errors.append(str(x)))
                q.goto(base + "privacy")
                m = q.evaluate(MEASURE)
                own = all(u.startswith(base) for u in asked)
                check(f"{w} px {scheme}: no sideways scroll, text 16 px or more, contrast 4.5 or more, no script, only its own files asked for",
                      not m["sideways"] and m["minFont"] >= 14.9 and m["font"] >= 16 and min(m["body"], m["link"], m["foot"], m["updated"]) >= 4.5 and m["scripts"] == 0 and own and len(asked) == 1,
                      [m, asked])
                if w == 320 and scheme == "dark":
                    check("the way back is a 44 px tap and goes to the app", m["backH"] >= 44 and q.get_attribute(".back", "href") == "./")
                    q.click("#rights-credits-link")
                    q.wait_for_selector("#view-credits:not(.hidden)", timeout=15000)
                    check("the footer's 'their own licences' link opens the app on its Credits page", q.url.endswith("#credits") and q.is_visible("#view-credits"), q.url)
                c.close()

        # ---- 5. the service worker and offline ----
        sc = browser.new_context(viewport={"width": 390, "height": 844})
        sp = sc.new_page()
        sp.goto(base + "index.html")
        sp.evaluate("() => navigator.serviceWorker.ready.then(() => true)")
        sp.reload()
        sp.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=10000)
        sp.goto(base + "privacy")
        sp.wait_for_timeout(600)
        sc.set_offline(True)
        sp.goto(base + "privacy")
        check("offline after one visit, /privacy opens the privacy page and not the app",
              sp.title() == "Minifolio privacy" and sp.locator("#view-dashboard").count() == 0 and "Last updated" in sp.inner_text("main"), sp.title())
        sc.close()

        check("no page errors", not errors, errors)
        browser.close()
    server.shutdown()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
