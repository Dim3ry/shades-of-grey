"""v21.4 tests for Minifolio: the app's code moved out of index.html into app.js and early.js,
so the Content Security Policy no longer allows code written inside the page ('unsafe-inline'
is gone from script-src).

Checks:
1. Version numbers (plain numbers), sw.js matches, the Updates entry, kept things (CNAME, the ocr
   folder, LICENSE-paint-list.txt, the ZAP workflow), storage names and the data version (still 1).
2. The files: app.js and early.js exist and load; index.html has exactly two <script> tags (v28: three, with colour.js; v31: four, with schemes.js; v32: five, with detail-recipes.js; v33: six, with basing-tips.js), both
   pointing at those files with "?v=" + the version, and no code written inside the page; early.js
   sits in <head> before the styles; app.js is last, just before </body>; the app's code (APP_VERSION,
   EXTRA_PAINT_TABLE…) is in app.js, not index.html. sw.js lists both files for offline use.
3. The policy: script-src is exactly 'self' 'wasm-unsafe-eval'; style-src keeps 'unsafe-inline';
   everything else is exactly as in v21.2. An inline script and an inline onclick are REALLY refused
   (tried on a page opened as "index.html?csp-probe", so the suite's watcher ignores those tries).
4. Every tab opens with no CSP errors and no page errors.
5. Light/dark before drawing: with app.js held back, early.js alone has already marked the page
   light (light setting, or "Match my phone" on a light phone) and the page background is light;
   a dark setting stays dark.
6. The pot-label reader still reads a test picture.
7. Offline: the saved copy has app.js and early.js; the app reloads and works with the internet off;
   an installed copy that's missing the new files (like an older version's) picks them up when
   online and then works offline; a missing file offline fails instead of being handed the page.
8. Help → Privacy wording; nothing scrolls sideways at 360 px; no page errors anywhere.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from dialog_watch import DialogAnswers

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}/"
URL = BASE + "index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

# v62: the 7th default stage was renamed from "Painted with issues" to "Needs touch-ups", so this list uses the new name.
STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Needs touch-ups", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 1, "count": 10,
     "log": [["2026-09-01", 1]]},
]
TABS = ["dashboard", "units", "recipes", "help", "updates", "settings"]

# The whole policy at v21.4: v21.2's, minus 'unsafe-inline' in script-src.
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
LIGHT_PAGE = "rgb(233, 239, 246)"   # #e9eff6, the light page colour (v20)

def seed(page, units=UNITS, settings=None, url=URL):
    page.goto(url)
    page.evaluate("""([u, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings])
    page.reload()
    page.wait_for_timeout(300)

def full_settings(**extra):
    s = {"palette": "ice", "tab": "dashboard", "stages": STAGES, "doneFrom": 5}
    s.update(extra)
    return s

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(120)

def shot(page, name, full=False):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)

def no_sideways(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

def watch(page, errors, csp):
    def on_console(m):
        where = page.url   # the deliberate inline tries run on "index.html?csp-probe"
        if "Content Security Policy" in m.text and "csp-probe" not in m.text and "csp-probe" not in where:
            csp.append(m.text)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", on_console)
    DialogAnswers(page)

def before_drawing(browser, appearance, scheme="dark"):
    """Open the app with app.js held back, and report what early.js alone has done."""
    context = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme=scheme,
                                  service_workers="block")
    page = context.new_page()
    page.goto(BASE + "manifest.json")   # same website, so the setting can be saved first
    page.evaluate("s => { localStorage.clear(); localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }",
                  full_settings(appearance=appearance))
    held = []
    page.route("**/app.js*", lambda route: held.append(route))
    page.goto(URL, wait_until="commit")
    page.wait_for_selector("#toast", state="attached", timeout=10000)   # the last thing before app.js
    for _ in range(200):   # v32: the page asks for app.js only after the scripts before it have loaded (now five of them), so wait until it is held
        if held:
            break
        page.wait_for_timeout(50)
    state = page.evaluate("""() => ({ app: typeof APP_VERSION, mark: document.documentElement.dataset.appearance || '',
        page: getComputedStyle(document.body).backgroundColor })""")
    for route in held:
        route.continue_()
    page.wait_for_function("() => typeof APP_VERSION === 'string'", timeout=10000)
    context.close()
    return state

def main():
    html, app, early, sw = read("index.html"), read("app.js"), read("early.js"), read("sw.js")
    errors, csp = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        watch(page, errors, csp)
        got = {}
        page.on("response", lambda r: got.__setitem__(r.url.split("/")[-1], (r.status, r.headers.get("content-type", ""))))

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page, settings=full_settings())
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21.4 or later", float(version[1:]) >= 21.4, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.4')")
        if page.evaluate("['v21.4'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v21.4 entry", entry and len(entry["changes"]) >= 1, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v21.4 entry')
        if page.evaluate("['v21.4'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the v21.4 entry is about the safety change", entry and "Safety" in " ".join(entry["changes"]))
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the v21.4 entry is about the safety change')
        tab(page, "updates")
        heads = page.locator("#view-updates h3").all_inner_texts()
        if page.evaluate("['v21.4'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab shows v21.4", any(h.startswith("v21.4") for h in heads), heads[:3])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab shows v21.4')
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder is kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
              ["ocr-worker.js", "tesseract-core-simd-lstm.wasm", "tesseract-core-lstm.wasm", "eng.traineddata"]))
        check("LICENSE-paint-list.txt is kept", os.path.exists(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        zap = os.path.join(ROOT, ".github", "workflows", "zap-scan.yml")
        check("ZAP workflow is kept, still the passive baseline scan",
              os.path.exists(zap) and "action-baseline" in read(".github/workflows/zap-scan.yml")
              and "action-full-scan" not in read(".github/workflows/zap-scan.yml"))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") in (1, 2))  # v62 raised DATA_VERSION to 2 for the "Needs touch-ups" rename
        for key in ["mini-tracker-models", "shades-of-grey-settings", "shades-of-grey-recipes"]:
            check(f"storage key {key} still used", key in app)

        # ---------- 2. The files ----------
        print("\n--- 2. The new files ---")
        tag = "?v=" + version[1:]
        scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", html, re.S)
        check("index.html has exactly six <script> tags (v28: early.js, colour.js, app.js; v31: plus schemes.js; v32: plus detail-recipes.js; v33: plus basing-tips.js)", len(scripts) == 6, len(scripts))
        check("both load a file (src=…)", all('src="' in attrs for attrs, _ in scripts), [a for a, _ in scripts])
        check("no code written inside the page (both tags are empty)", all(not body.strip() for _, body in scripts))
        check("no inline onclick= style handlers", not re.search(r"<[^>]+\son[a-z]+\s*=", html))
        check("no javascript: links", "javascript:" not in html.lower())
        srcs = [re.search(r'src="([^"]+)"', a).group(1) for a, _ in scripts if 'src="' in a]
        check(f"they are early.js{tag}, colour.js{tag} (v28), schemes.js{tag} (v31), detail-recipes.js{tag} (v32), basing-tips.js{tag} (v33) then app.js{tag}", srcs == [f"early.js{tag}", f"colour.js{tag}", f"schemes.js{tag}", f"detail-recipes.js{tag}", f"basing-tips.js{tag}", f"app.js{tag}"], srcs)
        head = html[:html.find("</head>")]
        check("early.js loads in <head>, before the styles", f'src="early.js{tag}"' in head
              and head.find('src="early.js') < head.find("<style"))
        check("early.js loads plainly (not async/defer, so it runs before the page is drawn)",
              not re.search(r"<script[^>]*early\.js[^>]*\b(async|defer)\b", html))
        tail = html[html.rfind("<script"):]
        check("app.js is the last thing, just before </body>", "app.js" in tail
              and re.fullmatch(r'<script src="app\.js[^"]*"></script>\s*</body>\s*</html>\s*', tail), tail[:120])
        check("the app's code is in app.js", "const APP_VERSION" in app and "EXTRA_PAINT_TABLE" in app
              and "function backTarget" in app)
        check("…and not in index.html any more", "APP_VERSION" not in html and "EXTRA_PAINT_TABLE" not in html)
        check("early.js reads the saved appearance", "shades-of-grey-settings" in early and "appearance" in early)
        for name in ("early.js", "app.js"):
            status, kind = got.get(name + tag, (0, ""))
            check(f"{name} loaded from the server", status == 200, (status, sorted(got)[:8]))
            check(f"{name} came back as a script", "javascript" in kind, kind)
        check("sw.js saves app.js and early.js for offline use",
              '"./app.js" + CODE_TAG' in sw and '"./early.js" + CODE_TAG' in sw and 'VERSION.slice(1)' in sw)
        check("only page requests fall back to the app when offline", 'mode === "navigate"' in sw)

        # ---------- 3. The policy ----------
        print("\n--- 3. The policy ---")
        tags = re.findall(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"', html)
        check("exactly one CSP tag", len(tags) == 1, len(tags))
        check("the CSP is exactly v21.2's minus script 'unsafe-inline'", tags == [V21_4_CSP], tags)
        policy = tags[0] if tags else ""
        script_rule = re.search(r"script-src ([^;]+)", policy)
        check("script-src has no 'unsafe-inline'", script_rule and "'unsafe-inline'" not in script_rule.group(1))
        check("style-src keeps 'unsafe-inline'", "style-src 'self' 'unsafe-inline'" in policy)
        check("the CSP tag comes before both scripts", 0 < html.find("Content-Security-Policy\" content") < html.find("<script"))
        check("the plain-English note explains the change", "NO code written inside the page" in html)
        check("the browser sees the same policy",
              page.evaluate("document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]').content") == policy)

        probe = context.new_page()
        watch(probe, errors, csp)
        probe.goto(URL + "?csp-probe")
        probe.wait_for_function("() => typeof APP_VERSION === 'string'")
        outcome = probe.evaluate("""() => new Promise(resolve => {
            const seen = [];
            document.addEventListener('securitypolicyviolation', e => seen.push(e.effectiveDirective || e.violatedDirective));
            window.cspProbeRan = false; window.cspProbeClicked = false;
            const s = document.createElement('script');
            s.textContent = 'window.cspProbeRan = true;';
            document.body.append(s);
            const b = document.createElement('button');
            b.setAttribute('onclick', 'window.cspProbeClicked = true');
            document.body.append(b); b.click();
            setTimeout(() => { s.remove(); b.remove();
              resolve({ seen, ran: window.cspProbeRan, clicked: window.cspProbeClicked }); }, 600);
        })""")
        check("code written inside the page is refused (it didn't run)", outcome["ran"] is False, outcome)
        check("…and the browser reported it as a script-src refusal",
              any(d.startswith("script-src") for d in outcome["seen"]), outcome)
        check("an inline onclick= is refused too", outcome["clicked"] is False, outcome)
        check("the app still works on that page", probe.evaluate("typeof render") == "function")
        probe.close()

        # ---------- 4. Every tab ----------
        print("\n--- 4. Every tab ---")
        seed(page, settings=full_settings())
        for name in TABS:
            tab(page, name)
            if name == "help":
                page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
            check(f"{name} tab opens", page.is_visible(f"#view-{name}"))
            shot(page, f"v21-4-tab-{name}.png")
        tab(page, "units")
        check("the units are shown", page.locator("#view-units li.unit").count() == 2)
        page.click('#view-units li.unit[data-id="1"] .info')
        page.wait_for_timeout(200)
        check("a unit's details open (the app's code is running)", page.locator("#view-units .jump-stage").count() >= 1)
        check("no CSP errors on any tab", not csp, csp[:3])
        context.close()

        # ---------- 5. Light/dark before drawing ----------
        print("\n--- 5. Light or dark before the page is drawn ---")
        light = before_drawing(browser, "light")
        check("with app.js held back, the app hasn't started yet", light["app"] == "undefined", light)
        check("light setting: early.js has already marked the page light", light["mark"] == "light", light)
        check("…and the page is already the light colour (no dark flash)", light["page"] == LIGHT_PAGE, light)
        auto = before_drawing(browser, "auto", scheme="light")
        check("'Match my phone' on a light phone: marked light before drawing", auto["mark"] == "light", auto)
        dark = before_drawing(browser, "dark", scheme="light")
        check("dark setting: stays dark", dark["mark"] == "" and dark["page"] != LIGHT_PAGE, dark)
        check("no CSP errors while drawing", not csp, csp[:3])

        # ---------- 6. Label reader ----------
        print("\n--- 6. Label reader ---")
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        watch(page, errors, csp)
        seed(page, settings=full_settings())
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
        text = page.evaluate("""async () => {
          const c = document.createElement('canvas'); c.width = 700; c.height = 140;
          const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, 700, 140);
          g.fillStyle = '#000'; g.font = 'bold 64px Arial'; g.fillText('MACRAGGE BLUE', 30, 95);
          const w = await getOcrWorker(); const { data } = await w.recognize(c); return data.text; }""")
        check("the label reader still reads a test picture", "MACRAGGE" in text.upper(), text)
        check("no CSP errors from the label reader", not csp, csp[:3])

        context.close()

        # ---------- 7. Offline ----------
        # This part runs its own small server, so "offline" can be real: the server is switched off.
        # (The browser's own offline switch doesn't reach the offline helper's fetches.)
        print("\n--- 7. Offline ---")
        sock = socket.socket(); sock.bind(("127.0.0.1", 0)); own_port = sock.getsockname()[1]; sock.close()
        server = [None]
        def internet(on):
            if on and server[0] is None:
                server[0] = subprocess.Popen([sys.executable, "-m", "http.server", str(own_port), "--bind", "127.0.0.1"],
                                             cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(50):
                    try:
                        socket.create_connection(("127.0.0.1", own_port), timeout=0.2).close(); break
                    except OSError:
                        time.sleep(0.1)
            elif not on and server[0] is not None:
                server[0].terminate(); server[0].wait(); server[0] = None
        own_url = f"http://localhost:{own_port}/index.html"
        try:
            internet(True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            watch(page, errors, csp)
            seed(page, settings=full_settings(), url=own_url)
            page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=15000)
            page.wait_for_timeout(500)

            def reopen():
                # Close the tab and open the app again, like reopening it on a phone.
                fresh = context.new_page()
                watch(fresh, errors, csp)
                fresh.goto(own_url)
                fresh.wait_for_timeout(800)
                return fresh

            cache_name = "shades-of-grey-" + version
            saved = page.evaluate("""name => caches.open(name).then(c => c.keys()).then(k => k.map(r => r.url.split('/').pop()))""",
                                  cache_name)
            check("the offline copy has app.js", f"app.js{tag}" in saved, saved)
            check("the offline copy has early.js", f"early.js{tag}" in saved, saved)
            internet(False)
            page.close()
            page = reopen()
            check("with the server switched off, the app opens", page.evaluate("typeof APP_VERSION") == "string")
            check("…shows the Dashboard", page.is_visible("#view-dashboard"))
            tab(page, "units")
            check("…and the units are there", page.locator("#view-units li.unit").count() == 2)
            shot(page, "v21-4-offline.png")
            missing = page.evaluate("fetch('no-such-file.js').then(r => 'answered ' + r.status, () => 'failed')")
            check("offline, a missing file fails instead of being handed the page", missing == "failed", missing)

            # An installed copy without the new files (like an older version's): it picks them up.
            internet(True)
            page.evaluate("""() => caches.keys().then(names => Promise.all(names.map(n => caches.open(n).then(c =>
                c.keys().then(k => Promise.all(k.filter(r => /(app|early)\\.js/.test(r.url)).map(r => c.delete(r))))))))""")
            gone = page.evaluate("""name => caches.open(name).then(c => c.keys()).then(k => k.filter(r => /(app|early)\\.js/.test(r.url)).length)""",
                                 cache_name)
            check("(set-up) the saved copy no longer has the new files", gone == 0, gone)
            page.close()
            page = reopen()
            page.wait_for_function("() => typeof APP_VERSION === 'string'", timeout=10000)
            back = page.evaluate("""name => caches.open(name).then(c => c.keys()).then(k => k.map(r => r.url.split('/').pop()))""",
                                 cache_name)
            check("online, it fetches and saves app.js again", f"app.js{tag}" in back, back)
            check("…and early.js", f"early.js{tag}" in back, back)
            internet(False)
            page.close()
            page = reopen()
            state = page.evaluate("""name => caches.open(name).then(c => c.keys()).then(k =>
                ({ app: typeof APP_VERSION, title: document.title, saved: k.map(r => r.url.split('/').pop()) }))""", cache_name)
            check("…and then works offline", state["app"] == "string" and page.locator("#view-units li.unit").count() == 2, state)
        finally:
            internet(False)
        check("no CSP errors offline", not csp, csp[:3])
        context.close()

        # ---------- 8. Privacy, 360 px ----------
        print("\n--- 8. Privacy and 360 px ---")
        context = browser.new_context(viewport={"width": 360, "height": 740})
        page = context.new_page()
        watch(page, errors, csp)
        seed(page, settings=full_settings())
        tab(page, "help")
        privacy = page.text_content("#privacy")
        check("Privacy still mentions the Content Security Policy", "Content Security Policy" in privacy)
        check("Privacy says code slipped into the page is refused too", "slipped into the page" in privacy, privacy[:300])
        for name in TABS:
            tab(page, name)
            check(f"{name}: nothing scrolls sideways at 360 px", no_sideways(page),
                  page.evaluate("document.documentElement.scrollWidth"))
        context.close()

        check("no CSP errors anywhere", not csp, csp[:5])
        check("no page errors", not errors, errors[:5])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
