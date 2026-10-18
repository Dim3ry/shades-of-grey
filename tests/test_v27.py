"""v27 tests for Minifolio: anonymous, cookie-free visit counting (GoatCounter, the image way) and the Privacy update.

Each time the app starts from minifolio.app it asks GoatCounter for ONE tiny picture. That is all that is sent.
No cookies, nothing saved on the device, nothing from the collection. A tick box in Settings -> Counting visits
switches it off. The security policy allows that one picture address and nothing else.

How the tests reach "minifolio.app": the real address is used inside the browser, but every request to it is answered
by the test straight from the repo folder (the ".app" ending is on browsers' secure-only list, so a local copy can't
be reached any other way). Every request to GoatCounter is caught by the test and answered with a 1x1 picture, so
nothing really leaves this machine.

Checks:
1. Versions, kept things, the Updates entry, the CSP (exactly one new address, in img-src only), sw.js leaves the picture alone.
2. Real start-up from minifolio.app: exactly one picture request, the exact address, an image, no referrer, no cookies,
   nothing else leaves; once per start; tab changes and redraws don't count; local copies (localhost) never count.
3. The switch: on by default, off is saved and honoured after a reload, on again, odd saved values mean on,
   another window follows, the choice is not in backups, nothing else in the saved settings changes.
4. No internet / a failing counter: the app works exactly as before, no messages, no errors.
5. The security policy really allows only that picture (other paths, other names, scripts and fetches are refused).
6. The Settings card: dark and light at 390 and 360 px, 44 px row, readable, no sideways scroll, after Appearance.
7. Help -> Privacy, Updates and README wording; no new network code besides the one picture.
8. Nothing else broke (tabs, switch, Back), no real pop-ups, no page errors, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import base64, json, mimetypes, os, re, sys, urllib.parse
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
SITE_BASE = "https://minifolio.app/"
SITE = SITE_BASE + "index.html"
COUNTER = "https://dim3ry.goatcounter.com/count"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, ".."))
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

V27_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
           "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
           "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
UNITS = [{"id": 1, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 10},
         {"id": 2, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10}]

counter = {"mode": "ok", "hits": []}
outside = []

def serve_site(route):
    """Answer a request to https://minifolio.app/... from the repo folder."""
    path = urllib.parse.unquote(urllib.parse.urlparse(route.request.url).path).lstrip("/") or "index.html"
    full = os.path.realpath(os.path.join(ROOT, path))
    if full.startswith(ROOT + os.sep) and os.path.isfile(full):
        route.fulfill(status=200, body=open(full, "rb").read(), content_type=mimetypes.guess_type(full)[0] or "application/octet-stream")
    else:
        route.fulfill(status=404, body="not found", content_type="text/plain")

def counter_route(route):
    req = route.request
    counter["hits"].append({"url": req.url, "type": req.resource_type, "referer": req.headers.get("referer")})
    if counter["mode"] == "abort":
        route.abort("internetdisconnected")
    elif counter["mode"] == "500":
        route.fulfill(status=500, body="no", content_type="text/plain")
    else:
        route.fulfill(status=200, body=GIF, content_type="image/gif")

def noted_request(request):
    u = request.url
    if u.startswith((SITE_BASE, BASE, "data:", "blob:", "about:")) or u.startswith(COUNTER):
        return
    outside.append(u)

def clear_photos(page):
    page.evaluate("""async () => { await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
        r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""")

def settle(page):
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(500)

def site_load(page, settings=None, units=None, url=SITE):
    """Open the app as minifolio.app with the given saved settings and units, counting only the real start-up."""
    page.goto(url)
    page.evaluate("""([u, s]) => { localStorage.clear();
        if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings])
    clear_photos(page)
    counter["hits"].clear()
    page.reload()
    settle(page)

def reload(page):
    page.reload()
    settle(page)

def blur(page):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.wait_for_timeout(150)

def main_tab(page, name):
    blur(page)
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def sub_tab(page, name):
    page.click(f'#more-seg button[data-page="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def saved_settings(page):
    t = page.evaluate("() => localStorage.getItem('shades-of-grey-settings')")
    return json.loads(t) if t else {}

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

def query_of(url):
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query, keep_blank_values=True)

def main():
    errors, csp, popups, notices = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        context.route(SITE_BASE + "**", serve_site)
        context.route("https://dim3ry.goatcounter.com/**", counter_route)
        context.on("request", noted_request)
        page = context.new_page()
        attach_notices(page, notices.append)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions and kept things ----------
        print("\n--- 1. Versions and kept things ---")
        site_load(page)
        html, app, sw = read("index.html"), read("app.js"), read("sw.js")
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v27 or later", float(version[1:]) >= 27, version)
        check("version is a plain number", re.fullmatch(r"v\d+(\.\d+)?", version) is not None, version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="(early|app)\.js\?v=([\d.]+)"', html)
        check("both script tags carry ?v= matching APP_VERSION", sorted(tags) == [("app", version[1:]), ("early", version[1:])], tags)
        check("the comment above the script tag names the same number", f'The "?v={version[1:]}" makes' in html)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v27')")
        check("Updates has a v27 entry with two lines", entry and len(entry["changes"]) >= 2, entry)
        check("the newest Updates entry is the current version", page.evaluate("CHANGELOG[0].version") == version)
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder and the paint-list licence kept",
              os.path.isdir(os.path.join(ROOT, "ocr")) and os.path.exists(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        wf = read(".github/workflows/zap-scan.yml")
        check("the ZAP workflow is still the passive baseline scan", "zaproxy/action-baseline" in wf and "full-scan" not in wf)
        csp_meta = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html, re.S)
        policy = " ".join(csp_meta.group(1).split()) if csp_meta else ""
        check("the CSP is exactly v21.4's plus the one counter picture address in img-src", policy == V27_CSP, policy)
        rules = {}
        for part in policy.split(";"):
            words = part.split()
            if words:
                rules[words[0]] = words[1:]
        check("script-src is untouched (only our own files and WebAssembly)", rules.get("script-src") == ["'self'", "'wasm-unsafe-eval'"], rules.get("script-src"))
        check("connect-src is untouched (only minifolio.app)", rules.get("connect-src") == ["'self'"], rules.get("connect-src"))
        outside_words = [w for v in rules.values() for w in v if w.startswith("http") or "*" in w]
        check("the only outside address in the whole policy is the counter's picture", outside_words == [COUNTER], outside_words)
        check("the policy comment in index.html explains the new address", "dim3ry.goatcounter.com/count" in html.split("-->")[0] or "ONE address" in html)
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        check("the three storage names are unchanged",
              all(k in app for k in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"',
                                     'RECIPES_KEY = "shades-of-grey-recipes"']))
        check("no code was put inside index.html", len(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", html)) == 0)
        skip = sw.find('.goatcounter.com")')
        check("sw.js leaves the counter's picture alone (before it handles anything)", 0 < skip < sw.find("respondWith"), skip)

        # ---------- 2. Real start-up from minifolio.app ----------
        print("\n--- 2. Real start-up from minifolio.app ---")
        outside.clear()
        site_load(page, units=UNITS)
        check("the page really is at minifolio.app", page.evaluate("location.hostname") == "minifolio.app")
        hits = counter["hits"]
        check("one start-up asks GoatCounter exactly once", len(hits) == 1, hits)
        hit = hits[0] if hits else {"url": "", "type": "", "referer": "x"}
        q = query_of(hit["url"])
        check("the address is exactly the counter's /count picture", hit["url"].startswith(COUNTER + "?"), hit["url"])
        check("only two things are in the address: the page name \"/\" and a random cache-buster", sorted(q) == ["p", "rnd"] and q["p"] == ["/"] and len(q["rnd"][0]) >= 4, q)
        check("it is asked for as a picture (not a script or a fetch)", hit["type"] == "image", hit["type"])
        check("no referrer is sent (GoatCounter isn't told which page it came from)", not hit["referer"], hit["referer"])
        check("no cookies are set or stored", context.cookies() == [] and page.evaluate("document.cookie") == "", context.cookies())
        check("nothing else leaves the app", outside == [], outside)
        check("a brand-new start saves no counting setting (the default is on)", "countVisits" not in saved_settings(page), saved_settings(page))
        check("countThisVisit() a second time asks for nothing more", page.evaluate("countThisVisit()") is False and len(counter["hits"]) == 1, counter["hits"])
        for tab in ["units", "recipes", "settings", "dashboard"]:
            main_tab(page, tab)
        page.evaluate("render()")
        page.wait_for_timeout(300)
        check("moving between tabs and redrawing never counts again", len(counter["hits"]) == 1, counter["hits"])
        counter["hits"].clear()
        reload(page)
        check("a new start counts once more", len(counter["hits"]) == 1, counter["hits"])
        saved = json.loads(page.evaluate("() => localStorage.getItem('mini-tracker-models')"))
        check("the units are the same as before (counting touches nothing)",
              [(u["id"], u["name"], u["count"], u["stage"]) for u in saved] == [(u["id"], u["name"], u["count"], u["stage"]) for u in UNITS], saved)

        counter["hits"].clear()
        local = context.new_page()
        local.on("pageerror", lambda e: errors.append(str(e)))
        local.goto(URL)
        local.evaluate("() => localStorage.clear()")
        local.reload()
        settle(local)
        check("a local copy (localhost) never counts", counter["hits"] == [] and local.evaluate("countingHere()") is False, counter["hits"])
        check("and the same for an app opened from any other address", local.evaluate("COUNTED_HOSTS") == ["minifolio.app"], local.evaluate("COUNTED_HOSTS"))
        local.close()

        # ---------- 3. The switch ----------
        print("\n--- 3. The switch in Settings ---")
        site_load(page, units=UNITS)
        main_tab(page, "settings")
        box = page.locator("#count-visits")
        check("the tick box is ticked by default", box.is_checked())
        note_on = page.inner_text("#counting-note")
        check("the note says it is on and what is sent", note_on.startswith("On.") and "one tiny picture" in note_on and "nothing from your collection" in note_on, note_on)
        counter["hits"].clear()
        page.click("#counting-card .count-label")
        page.wait_for_timeout(300)
        check("tapping the words unticks the box", not box.is_checked())
        check("the choice is saved (false)", saved_settings(page).get("countVisits") is False, saved_settings(page))
        check("the note says it is off", page.inner_text("#counting-note").startswith("Off."), page.inner_text("#counting-note"))
        check("switching it off sends nothing", counter["hits"] == [], counter["hits"])
        reload(page)
        check("after a reload it stays off and asks GoatCounter for nothing", counter["hits"] == [] and not page.locator("#count-visits").is_checked(), counter["hits"])
        main_tab(page, "settings")
        page.focus("#count-visits")
        page.keyboard.press("Space")
        page.wait_for_timeout(300)
        check("the Space key ticks it again (works from the keyboard)", page.locator("#count-visits").is_checked() and saved_settings(page).get("countVisits") is True, saved_settings(page))
        check("ticking it again mid-visit doesn't count straight away (takes effect next start)", counter["hits"] == [], counter["hits"])
        reload(page)
        check("the next start counts once", len(counter["hits"]) == 1, counter["hits"])
        # unknown settings survive a change
        page.evaluate("""() => { settings.someFutureThing = { a: 1 }; saveSettings(); }""")
        main_tab(page, "settings")
        page.click("#counting-card .count-label")
        page.wait_for_timeout(300)
        check("other saved settings are kept when the switch changes", saved_settings(page).get("someFutureThing") == {"a": 1}, saved_settings(page))
        check("DATA_VERSION stays 1 and the saved data version is unchanged", page.evaluate("DATA_VERSION") == 1 and saved_settings(page).get("dataVersion") == 1, saved_settings(page))
        check("a backup does not carry the choice (like the feedback card's dates)",
              "countVisits" not in page.evaluate("() => JSON.stringify(backupData())"))
        # odd saved values count as on and are removed
        for label, value in [("a word", "no"), ("zero", 0), ("null", None), ("the word false", "false"), ("a list", [False])]:
            site_load(page, settings={"countVisits": value}, units=UNITS)
            check(f"a saved value that is {label} is treated as ON (only a real false is off)",
                  len(counter["hits"]) == 1 and page.evaluate("countingIsOn()") is True and "countVisits" not in saved_settings(page),
                  (counter["hits"], saved_settings(page)))
        site_load(page, settings={"countVisits": False}, units=UNITS)
        check("a saved false is honoured at start-up (nothing asked for)", counter["hits"] == [] and page.evaluate("countingIsOn()") is False, counter["hits"])
        site_load(page, settings={"countVisits": True}, units=UNITS)
        check("a saved true counts", len(counter["hits"]) == 1, counter["hits"])
        # a second window follows the choice
        site_load(page, units=UNITS)
        other = context.new_page()
        other.on("pageerror", lambda e: errors.append(str(e)))
        other.goto(SITE)
        settle(other)
        main_tab(other, "settings")
        other.click("#counting-card .count-label")
        other.wait_for_timeout(300)
        page.wait_for_timeout(900)
        check("another window's change shows here too (the box follows)", page.evaluate("countingBox.checked") is False and page.evaluate("countingIsOn()") is False,
              page.evaluate("countingIsOn()"))
        other.close()

        # ---------- 4. No internet or a failing counter ----------
        print("\n--- 4. No internet, or a counter that fails ---")
        for mode in ["abort", "500"]:
            counter["mode"] = mode
            notices.clear()
            errors.clear()
            site_load(page, units=UNITS)
            main_tab(page, "units")
            check(f"[{mode}] the app still asked once and carried on", len(counter["hits"]) == 1, counter["hits"])
            check(f"[{mode}] the Units list still shows both units", page.locator("#view-units li.unit").count() == 2, page.locator("#view-units li.unit").count())
            check(f"[{mode}] no message is shown to the person", notices == [] and not page.locator("#toast").is_visible(), notices)
            check(f"[{mode}] no page errors", errors == [], errors[:3])
            check(f"[{mode}] no save problem banner", page.evaluate("() => { const b = document.getElementById('save-problem'); return !b || b.hidden || getComputedStyle(b).display === 'none'; }"))
        counter["mode"] = "ok"

        # ---------- 5. The security policy really allows only that picture ----------
        print("\n--- 5. The policy allows only that one picture ---")
        probe = context.new_page()
        probe.on("pageerror", lambda e: errors.append(str(e)))
        probe.goto(SITE + "?csp-probe")
        probe.wait_for_function("() => typeof APP_VERSION === 'string'")
        counter["hits"].clear()
        result = probe.evaluate("""async () => {
            const blocked = [];
            document.addEventListener('securitypolicyviolation', e => blocked.push([e.violatedDirective.split(' ')[0], e.blockedURI]));
            const tryImg = (src) => new Promise(done => { const i = new Image(); i.onload = i.onerror = () => done(); i.src = src; });
            await tryImg('https://dim3ry.goatcounter.com/count?p=%2Fcsp-probe');
            const allowedBlocked = blocked.length;
            await tryImg('https://dim3ry.goatcounter.com/other?csp-probe');
            await tryImg('https://dim3ry.goatcounter.com/count/more?csp-probe');
            await tryImg('https://evil.goatcounter.com/count?csp-probe');
            await tryImg('https://example.com/csp-probe.png');
            const s = document.createElement('script'); s.src = 'https://gc.zgo.at/count.js?csp-probe'; document.head.appendChild(s);
            const s2 = document.createElement('script'); s2.src = 'https://dim3ry.goatcounter.com/count.js?csp-probe'; document.head.appendChild(s2);
            let fetched = 'sent';
            try { await fetch('https://dim3ry.goatcounter.com/count?csp-probe'); } catch (e) { fetched = 'refused'; }
            await new Promise(r => setTimeout(r, 500));
            return { allowedBlocked, blocked, fetched };
        }""")
        check("the counter's own /count picture is allowed (no violation)", result["allowedBlocked"] == 0, result)
        directives = [b[0] for b in result["blocked"]]
        check("another path on the same site is refused", any("/other" in b[1] for b in result["blocked"]), result["blocked"])
        check("a longer path under /count is refused", any("/count/more" in b[1] for b in result["blocked"]), result["blocked"])
        check("another GoatCounter name is refused", any("evil.goatcounter" in b[1] for b in result["blocked"]), result["blocked"])
        check("a picture from any other website is refused", any("example.com" in b[1] for b in result["blocked"]), result["blocked"])
        check("a script from GoatCounter's script address is refused (script-src is untouched)", any(b[0] == "script-src-elem" and "gc.zgo.at" in b[1] for b in result["blocked"]), result["blocked"])
        check("a script from the counter's own site is refused", any(b[0] == "script-src-elem" and "count.js" in b[1] and "dim3ry" in b[1] for b in result["blocked"]), result["blocked"])
        check("fetching from the counter's address is refused (connect-src is untouched)", result["fetched"] == "refused", result)
        check("only the allowed picture ever reached the network", [h["url"].split("?")[0] for h in counter["hits"]] == [COUNTER], counter["hits"])
        probe.close()

        # ---------- 6. The Settings card ----------
        print("\n--- 6. The Settings card, dark and light ---")
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                tag = f"{appearance} {width}px"
                page.set_viewport_size({"width": width, "height": 844})
                site_load(page, settings={"appearance": appearance}, units=UNITS)
                main_tab(page, "settings")
                page.locator("#counting-card").scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                geo = page.evaluate("""() => { const c = document.getElementById('counting-card').getBoundingClientRect();
                    const row = document.querySelector('#counting-card .count-label').getBoundingClientRect();
                    const box = document.getElementById('count-visits').getBoundingClientRect();
                    const ap = document.getElementById('appearance-card').getBoundingClientRect();
                    return { cl: c.left, cr: c.right, w: window.innerWidth, rowH: row.height, rowW: row.width, boxW: box.width, boxH: box.height,
                             apBottom: ap.bottom, cTop: c.top }; }""")
                check(f"{tag}: the card is inside the screen", geo["cl"] >= 0 and geo["cr"] <= geo["w"] + 0.5, geo)
                check(f"{tag}: the tick row is at least 44 px tall and the box at least 20 px", geo["rowH"] >= 44 and geo["boxW"] >= 20 and geo["boxH"] >= 20, geo)
                check(f"{tag}: the card sits straight after Appearance", 0 <= geo["cTop"] - geo["apBottom"] <= 40, geo)
                check(f"{tag}: no sideways scroll", no_sideways(page))
                col = page.evaluate("""() => { const bg = (el) => { let e = el; while (e) { const v = getComputedStyle(e).backgroundColor;
                        if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'transparent') return v; e = e.parentElement; } return 'rgb(0,0,0)'; };
                    const card = document.getElementById('counting-card');
                    return { label: getComputedStyle(card.querySelector('.count-label')).color, note: getComputedStyle(document.getElementById('counting-note')).color,
                             bg: bg(card) }; }""")
                check(f"{tag}: the words and the note are readable (contrast at least 4.5)",
                      contrast(rgb(col["label"]), rgb(col["bg"])) >= 4.5 and contrast(rgb(col["note"]), rgb(col["bg"])) >= 4.5, col)
                if width == 390:
                    shot(page, f"v27-counting-card-{appearance}-390.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Wording and code ----------
        print("\n--- 7. Help, Privacy, Updates, README and the code ---")
        site_load(page, units=UNITS)
        main_tab(page, "settings")
        sub_tab(page, "help")
        counting = page.evaluate("() => document.getElementById('privacy-counting').textContent")
        check("Privacy says what is counted and who gets it (GoatCounter, Ireland, Finland and Germany)",
              all(w in counting for w in ["GoatCounter", "Ireland", "Finland and Germany", "one tiny, empty picture"]), counting)
        check("Privacy says what is NOT sent (cookies, device storage, account, units, recipes, photos, settings, referrer)",
              all(w in counting for w in ["no cookies", "nothing is saved on your device", "no account or ID", "units, recipes, photos or settings", "which page you came from"]), counting)
        check("Privacy is honest that the request carries the internet address and browser type, and that GoatCounter says it doesn't keep the address",
              "internet address and browser type" in counting and "doesn't keep the address" in counting, counting)
        check("Privacy says where it counts, that offline does nothing and where the switch is",
              "only counts when the app is opened from minifolio.app" in counting and "with no internet it does nothing" in counting and "Settings → Counting visits" in counting, counting)
        priv_all = page.evaluate("() => document.getElementById('privacy').textContent")
        check("the old promise of \"no analytics\" is gone", "no analytics" not in priv_all.lower(), priv_all)
        check("the new line says no tracking of you, nothing about your collection, nothing sold, and points at the switch",
              "No tracking of you" in priv_all and "nothing about your collection is ever sent" in priv_all and "nothing is sold" in priv_all and "switch off" in priv_all, priv_all)
        check("the Locked down line names the one allowed picture",
              "the only other address it is allowed to load anything from is the visit counter's tiny picture" in priv_all, priv_all)
        check("What goes out points forward to the visit count", "The one thing the app does send on its own is the visit count" in priv_all, priv_all)
        check("the old Privacy lines are still there (stays on your phone, scanning, feedback card, unfinished work, shop links)",
              all(w in priv_all for w in ["Stays on your phone", "Scanning a paint pot", "The feedback card", "Unfinished work", "Shop links"]), priv_all)
        sub_tab(page, "updates")
        updates = page.inner_text("#view-updates")
        check("the Updates page has the v27 entry in plain words",
              "v27" in updates and "GoatCounter" in updates and "no cookies" in updates.lower() and "Counting visits" in updates and "nothing from your collection" in updates, updates[:700])
        check("\"Tell us what you think\" is still there", "Tell us what you think" in updates)
        readme = read("README.md")
        check("README explains the counter, no cookies, the one address, and the switch",
              all(w in readme for w in ["GoatCounter", "no cookies", "one address", "Settings → Counting visits", "Help → Privacy"]), readme[:900])
        check("README still has the unofficial and copyright lines", "Unofficial fan-made app" in readme and "All rights reserved" in readme)
        start = app.find("v27: COUNTING VISITS")
        end = app.find("const CHANGELOG = [")
        mine = app[start:end]
        check("the new code was found", 0 < start < end and len(mine) > 500, (start, end))
        code_only = "\n".join(l for l in mine.splitlines() if not l.strip().startswith("//"))
        check("the new code has no fetch, XMLHttpRequest, sendBeacon, WebSocket, eval or inline handlers",
              not re.search(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|\beval\s*\(|new Function|\bon[a-z]+\s*=\s*\"", code_only.replace("pixel.onload", "").replace("pixel.onerror", "")), code_only)
        check("the new code makes exactly one picture and asks for it without a referrer",
              code_only.count("new Image(") == 1 and 'referrerPolicy = "no-referrer"' in code_only, code_only)
        check("the new code sends only the page name \"/\" and a random number", 'encodeURIComponent("/")' in code_only and "&rnd=" in code_only and "&t=" not in code_only and "&r=" not in code_only and "&s=" not in code_only)
        check("nothing from units, recipes, photos or settings is read by the new code", not re.search(r"\bmodels\b|\bbook\b|photo", code_only.replace("countingBox", "")), code_only)

        # ---------- 8. Nothing else broke ----------
        print("\n--- 8. Nothing else broke ---")
        site_load(page, units=UNITS)
        check("five tabs along the bottom", page.locator("nav.tabs button[data-tab]").count() == 5)
        main_tab(page, "settings")
        for name in ["help", "updates", "settings"]:
            sub_tab(page, name)
            check(f"the {name} page opens from the switch", page.evaluate("settings.tab") == name, page.evaluate("settings.tab"))
        check("the Appearance and Colours cards are still on Settings", page.locator("#appearance-card").count() == 1 and page.locator("#palette-select").count() == 1)
        check("the Backups card is still first on Settings", page.evaluate("() => document.querySelector('#view-settings .card').id") == "backup-card")
        outside.clear()
        reload(page)
        check("a start-up from minifolio.app sends only the one picture (nothing else left the app)", outside == [] and len(counter["hits"]) >= 1, outside)

        check("no real browser pop-ups at any point", not popups, popups)
        check("no page errors", not errors, errors[:3])
        check("no CSP errors on the real pages", not csp, csp[:3])
        context.close()
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
