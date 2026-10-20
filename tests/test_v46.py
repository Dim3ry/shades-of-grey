"""v46 tests for Minifolio (T1: link tag and tidy-ups).

What changed:
 (a) Link tag: a link such as minifolio.app/?from=dakka is counted under the tag "dakka". The app reads `from` once, accepts only
     1 to 20 lowercase letters, digits and dashes, and adds it to the existing GoatCounter counting picture as `q=campaign=<tag>`
     (the way GoatCounter's pixel documentation says campaigns are recorded). Only sent when Counting visits is on and the app
     runs from minifolio.app; never saved, never in backups, never written into the page. The security policy is unchanged.
 (b) Tidy-ups: the Dashboard headline line now also says how many models are "under way" (past the first stage, not done yet);
     the up-arrow is always the accent colour so a new unit's button no longer looks switched off; and Settings -> Backups has a
     new "Send full backup with photos to..." button that matches "Send backup to...".

Checks:
1. Versions, the v46 Updates entry, the security policy exactly as before, Help, Privacy and README wording.
2. The tag: accepted and refused values, exact picture address, one request only, no referrer, nothing else leaves, switch off and
   local copies send nothing, the tag is not saved, not in backups, not in the page, and markup in the tag does nothing.
3. Dashboard: empty, brand-new, built and primed, finished, model-by-model units, each against an independent count.
4. The up-arrow: accent colour at every stage in dark and light, readable, the finished tick still looks off, stripe and name keep
   the stage colour.
5. Send full backup with photos to...: where it sits, a working share menu, closing the menu, no share menu, a failing one,
   a too-late tap (ready, tap again), a second failure, the dates, the toasts, missing photos, Save full backup unchanged.
6. Phone widths (390 and 360), dark and light: backup buttons readable and tall enough, Dashboard line wraps, nothing sideways.
7. No page errors, no browser pop-ups, no CSP errors.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys, urllib.parse
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v27 as s27   # the shared minifolio.app routing and counter helpers
import test_v31 as t     # the shared page helpers

URL, read, shot, no_sideways, ROOT = t.URL, t.read, t.shot, t.no_sideways, t.ROOT
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def rgb(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

NEUTRAL = URL.rsplit("/", 1)[0] + "/manifest.json"

def fresh(page, settings=None, units=None, photos=None):
    """Open the local copy with the given saved settings, units and (optionally) photo ids stored."""
    # Seed from a plain page on the same address (not the app), so an app still open from the last case can't write its own
    # state over the seeded values while it is being closed.
    page.goto(NEUTRAL)
    page.evaluate("""([u, s]) => { localStorage.clear();
        if (u) localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        if (s) localStorage.setItem('shades-of-grey-settings', JSON.stringify(s)); }""", [units, settings])
    s27.clear_photos(page)
    page.goto(URL)
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(400)
    if photos:
        page.evaluate("""async (ids) => { for (const id of ids) { const b = new Blob(['photo-' + id], { type: 'image/jpeg' });
            await putPhoto({ id, full: b, thumb: b }); } }""", photos)
        page.evaluate("""(u) => localStorage.setItem('mini-tracker-models', JSON.stringify(u))""", units)
        page.goto(URL)
        page.wait_for_function("() => typeof APP_VERSION === 'string'")
        page.wait_for_timeout(400)

def tab(page, name):
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(200)

def open_more(page, which):
    tab(page, "settings")
    page.click(f'#more-seg button[data-page="{which}"]')
    page.wait_for_timeout(200)

def toast(page):
    return page.inner_text("#toast-text")

# A fake share menu. Modes: ok, cancel (AbortError), fail (another error), late (the FIRST call is refused with NotAllowedError
# because the tap was too long ago; later calls work), refused (every call NotAllowedError), nocan, none.
def fake_share(page, mode):
    page.evaluate("""(mode) => {
        window.__shared = []; window.__calls = 0;
        const set = (name, value) => Object.defineProperty(navigator, name, { configurable: true, writable: true, value });
        if (mode === "none") { set("share", undefined); set("canShare", undefined); return; }
        set("canShare", (data) => mode !== "nocan" && !!(data && data.files && data.files.length));
        set("share", async (data) => {
            window.__calls++;
            const f = data.files[0];
            window.__shared.push({ name: f.name, type: f.type, text: await f.text(), count: data.files.length });
            const err = (name) => { const e = new Error(name); e.name = name; return e; };
            if (mode === "cancel") throw err("AbortError");
            if (mode === "fail") throw err("TypeError");
            if (mode === "refused") throw err("NotAllowedError");
            if (mode === "late" && window.__calls === 1) throw err("NotAllowedError");
        });
    }""", mode)

def shared(page):
    return page.evaluate("() => window.__shared || []")

def today(page):
    return page.evaluate("todayISO()")

def saved_settings(page):
    text = page.evaluate("() => localStorage.getItem('shades-of-grey-settings')")
    return json.loads(text) if text else {}

BASE_UNITS = [{"id": 1, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 10},
              {"id": 2, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 2, "count": 5},
              {"id": 3, "name": "Genestealers", "hobby": "40K", "faction": "Tyranids", "stage": 3, "count": 5}]
PHOTO_UNITS = [{"id": 1, "name": "Captain", "hobby": "40K", "faction": "Ultramarines", "stage": 2, "count": 1,
                "photos": [{"id": "p1"}, {"id": "p2"}]}]
OLD = {"lastBackup": "2026-01-01", "lastFullBackup": "2026-01-01"}

def main():
    errors, csp, popups, downloads, notices_ = [], [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ===================== the minifolio.app context (for the visit counter) =====================
        site_ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        site_ctx.route(s27.SITE_BASE + "**", s27.serve_site)
        site_ctx.route("https://dim3ry.goatcounter.com/**", s27.counter_route)
        site_ctx.on("request", s27.noted_request)
        site = site_ctx.new_page()
        site.on("pageerror", lambda e: errors.append(str(e)))
        site.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        site.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        # ---------- 1. Versions, wording, policy ----------
        print("\n--- 1. Versions, the security policy and the wording ---")
        s27.site_load(site)
        html, app, sw, readme = read("index.html"), read("app.js"), read("sw.js"), read("README.md")
        version = site.evaluate("APP_VERSION")
        check("APP_VERSION is v46 or later", float(version[1:]) >= 46, version)
        m = re.search(r'const VERSION = "v([\d.]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and "v" + m.group(1) == version, m and m.group(1))
        tags = re.findall(r'<script src="[^"]+\?v=(\d+)"', html)
        check("all six script tags carry the same ?v= number as the version", len(tags) == 6 and set(tags) == {version[1:]}, tags)
        check("the comment in index.html names the same number", f'The "?v={version[1:]}" makes' in html)
        check("the comment in app.js names the same number", f'e.g. "app.js?v={version[1:]}"' in app)
        entry = site.evaluate("CHANGELOG.find(r => r.version === 'v46')")
        check("Updates has a v46 entry with four short lines", entry and len(entry["changes"]) == 4, entry)
        check("the newest Updates entry is v46 or later", float(site.evaluate("CHANGELOG[0].version")[1:]) >= 46)
        joined = " ".join(entry["changes"]) if entry else ""
        check("the v46 entry mentions the tag, under way, the arrow and the full backup send button",
              all(w in joined for w in ["?from=club", "under way", "▲", "Send full backup with photos to…"]), joined[:200])
        check("Updates still shows five entries", site.evaluate("UPDATES_SHOWN") == 5)
        csp_now = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
        check("the security policy is exactly what it was (no new address, no new rule)", csp_now == s27.V27_CSP, csp_now)
        check("sw.js still leaves the counter picture alone", 'endsWith(".goatcounter.com")' in sw)
        check("the page's own comment about the policy still names only the counter picture", "https://dim3ry.goatcounter.com/count" in html)
        check("README mentions the short tag", "?from=club" in readme and "never saved" in readme)
        s27.site_load(site)
        privacy = site.evaluate("() => document.getElementById('privacy').textContent")
        check("Privacy explains the tag: one short word, where the link was shared, never saved, not in backups, nothing extra without a tag",
              all(w in privacy for w in ["?from=club", "one short word", "never saved", "never goes into your backups", "sends nothing extra"]), privacy[:100])
        check("Privacy still says it doesn't tell GoatCounter which page you came from and that you can switch it off",
              "doesn't tell GoatCounter which page you came from" in privacy and "You can switch it off" in privacy)
        check("Privacy now names both Send buttons as only opening the share menu",
              "Send full backup with photos to… only open" in privacy, privacy[:100])
        helptext = site.evaluate("() => document.getElementById('help-send-full-backup').textContent")
        check("Help explains Send full backup with photos to… (photos, tap again, saved instead)",
              all(w in helptext for w in ["photos", "Backup ready: tap to send", "share menu", "saved to your device instead"]), helptext)

        # ---------- 2. The link tag ----------
        print("\n--- 2. The link tag ---")
        cases = [
            ("?from=dakka", "dakka"), ("?from=a", "a"), ("?from=abcdefghij0123456789", "abcdefghij0123456789"),
            ("?from=my-club-2", "my-club-2"), ("?from=--", "--"), ("?from=a&from=b", "a"), ("?x=1&from=dakka&y=2", "dakka"),
            ("?from=abcdefghij01234567890", None), ("?from=Dakka", None), ("?from=da_kka", None), ("?from=da%20kka", None),
            ("?from=da+kka", None), ("?from=", None), ("?from=dak.ka", None), ("?from=%3Cb%3Ex%3C%2Fb%3E", None),
            ("?from=dakka%0A", None), ("?from=%C3%BCn%C3%AF", None), ("?other=dakka", None), ("", None), ("?from", None),
            ("?from=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E", None), ("?FROM=dakka", None),
        ]
        bad = []
        for query, want in cases:
            s27.counter["hits"].clear()
            s27.site_load(site, url=s27.SITE_BASE + "index.html" + query)
            hits = s27.counter["hits"]
            if len(hits) != 1:
                bad.append((query, "requests", len(hits))); continue
            q = s27.query_of(hits[0]["url"])
            keys = sorted(q.keys())
            want_keys = ["p", "q", "rnd"] if want else ["p", "rnd"]
            if (not hits[0]["url"].startswith(s27.COUNTER + "?") or keys != want_keys or q["p"] != ["/"]
                    or (want and q["q"] != ["campaign=" + want]) or hits[0]["type"] != "image" or hits[0]["referer"]):
                bad.append((query, hits[0]["url"], hits[0]["referer"]))
        check(f"{len(cases)} link shapes: only 1 to 20 lowercase letters, digits and dashes are sent (as q=campaign=<tag>); everything else still counts the visit with no tag; always one image request, no referrer",
              not bad, bad[:3])
        s27.counter["hits"].clear()
        s27.site_load(site, url=s27.SITE_BASE + "index.html?from=dakka")
        url = s27.counter["hits"][0]["url"] if s27.counter["hits"] else ""
        check("the exact address: counter, p=/ then q=campaign%3Ddakka then rnd", re.fullmatch(re.escape(s27.COUNTER) + r"\?p=%2F&q=campaign%3Ddakka&rnd=[a-z0-9]{1,8}", url) is not None, url)
        tabs_before = len(s27.counter["hits"])
        for name in ("units", "recipes", "settings", "dashboard"):
            tab(site, name)
        site.evaluate("() => { render(); renderDashboard(); }")
        check("counted once per start: changing tabs and redrawing sends nothing more", len(s27.counter["hits"]) == tabs_before, len(s27.counter["hits"]))
        check("nothing else leaves the phone (no request outside minifolio.app and the one counter address)", not s27.outside, s27.outside[:3])

        # switch off, local copy, and never saved
        s27.counter["hits"].clear()
        s27.site_load(site, settings={"countVisits": False}, url=s27.SITE_BASE + "index.html?from=dakka")
        check("with Counting visits switched off, a tagged link sends nothing at all", len(s27.counter["hits"]) == 0, s27.counter["hits"])
        s27.counter["hits"].clear()
        site.goto(URL + "?from=dakka"); site.wait_for_timeout(500)
        check("a local copy (not minifolio.app) never counts, tagged or not", len(s27.counter["hits"]) == 0, s27.counter["hits"])
        TAG = "zq-tag-77"
        s27.site_load(site, units=BASE_UNITS, url=s27.SITE_BASE + "index.html?from=" + TAG)
        everything = site.evaluate("""() => JSON.stringify({ local: Object.entries(localStorage), session: Object.entries(sessionStorage),
            backup: backupData(), settings: settings, dom: document.documentElement.outerHTML, title: document.title })""")
        check("the tag is not saved anywhere: not in saved data, session storage, settings or backups", TAG not in everything, "found")
        site.click('nav button[data-tab="settings"]'); site.wait_for_timeout(200)
        all_text = site.evaluate("() => document.body.innerText + document.documentElement.outerHTML")
        check("the tag is not written into the page at all (not as text, not as HTML)", TAG not in all_text)
        s27.counter["hits"].clear()
        site.goto(s27.SITE)   # same phone, no tag: nothing is remembered
        site.wait_for_timeout(500)
        qs = [s27.query_of(h["url"]) for h in s27.counter["hits"]]
        check("opening again without a tag sends no tag (nothing was remembered)", len(qs) == 1 and "q" not in qs[0], qs)
        site.goto(s27.SITE_BASE + "index.html?from=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E"); site.wait_for_timeout(500)
        check("markup in the tag does nothing: no picture, no pop-up, no page error",
              site.locator('img[src="x"]').count() == 0 and not popups and not errors, (popups, errors[:1]))
        body = app[app.index("const LINK_TAG_PATTERN"):app.index("const COUNTER_CODE")]
        check("the tag code only reads the address bar: no storage, no innerHTML, no network call of its own",
              not re.search(r"localStorage|sessionStorage|innerHTML|insertAdjacentHTML|fetch\(|XMLHttpRequest|saveSettings|settings\.", body), body[:200])
        check("the picture is still the only network code (one Image, no fetch or XHR added)",
              len(re.findall(r"new Image\(\)\s*;?\s*\n\s*pixel\.referrerPolicy", app)) == 1 and not re.search(r"sendBeacon|XMLHttpRequest", app))
        check("no request left the phone except the app's own files and the counter",
              not s27.outside, s27.outside[:3])
        site_ctx.close()

        # ===================== the local context =====================
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", accept_downloads=True)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))
        page.on("download", lambda d: downloads.append(d))

        # ---------- 3. The Dashboard line ----------
        print("\n--- 3. Dashboard: models under way ---")
        def dash(units, settings=None):
            fresh(page, settings=settings, units=units)
            tab(page, "dashboard")
            return page.inner_text("#done-percent"), page.inner_text("#done-summary")
        def expected(units):
            n, done_from = page.evaluate("[STAGES.length, settings.doneFrom]")
            stages = []
            for u in units:
                stages += u["stages"] if u.get("each") else [u["stage"]] * u.get("count", 1)
            total, done = len(stages), sum(1 for s in stages if s >= done_from)
            under = sum(1 for s in stages if 1 <= s < done_from)
            return total, done, under
        pct, summary = dash([])
        check("an empty collection reads as before (a dash and the 'No units yet' line)", pct == "–" and summary.startswith("No units yet"), (pct, summary))
        flat = [{"id": 1, "name": "A", "hobby": "40K", "faction": "X", "stage": 0, "count": 10}, {"id": 2, "name": "B", "hobby": "40K", "faction": "X", "stage": 0, "count": 10}]
        pct, summary = dash(flat)
        check("a brand-new collection reads exactly as before: no 'under way' while nothing has started", summary == "0 of 20 models done · 2 units" and pct == "0%", (pct, summary))
        pct, summary = dash(BASE_UNITS)
        total, done, under = expected(BASE_UNITS)
        check("built and primed but none finished: the line says how many are under way (and the headline is still 0%)",
              summary == f"{done} of {total} models done · {under} under way · 3 units" and under == 10 and pct == "0%", (pct, summary, under))
        last = page.evaluate("STAGES.length - 1")
        more = BASE_UNITS + [{"id": 4, "name": "Ravener", "hobby": "40K", "faction": "Tyranids", "stage": last, "count": 4}]
        pct, summary = dash(more)
        total, done, under = expected(more)
        check("finished models count as done and are not 'under way'", summary == f"{done} of {total} models done · {under} under way · 4 units" and done == 4 and under == 10, (pct, summary))
        mixed = [{"id": 1, "name": "Gaunts", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 4, "each": True, "stages": [0, 1, 2, last], "log": [["2026-09-01", 1]]}]
        pct, summary = dash(mixed)
        total, done, under = expected(mixed)
        check("a unit tracked model by model counts each model at its own stage", summary == f"{done} of {total} models done · {under} under way · 1 units" and (done, under) == (1, 2), (summary, done, under))
        one = [{"id": 1, "name": "Solo", "hobby": "40K", "faction": "Tyranids", "stage": 1, "count": 1}]
        pct, summary = dash(one)
        check("one model under way reads sensibly", summary.startswith("0 of 1 models done · 1 under way"), summary)
        dash(BASE_UNITS)
        page.evaluate("() => { settings.doneFrom = 3; saveSettings(); renderDashboard(); }")
        summary = page.inner_text("#done-summary")
        total, done, under = expected(BASE_UNITS)
        check("it follows the 'Done starts at' choice (with Done from the fourth stage, primed models are done, not under way)",
              (done, under) == (5, 5) and summary.startswith(f"{done} of {total} models done · {under} under way"), (summary, done, under))
        shot(page, "v46-dashboard-underway-dark-390.png")
        check("the Dashboard still shows its charts and legend", page.locator("#stage-legend li").count() >= 3 and page.locator("#overall-chart svg").count() == 1)

        # ---------- 4. The up-arrow ----------
        print("\n--- 4. The up-arrow always looks pressable ---")
        arrow_units = [{"id": 1, "name": "Zero stage", "hobby": "40K", "faction": "X", "stage": 0, "count": 3},
                       {"id": 2, "name": "Middle stage", "hobby": "40K", "faction": "X", "stage": 2, "count": 3},
                       {"id": 3, "name": "Finished stage", "hobby": "40K", "faction": "X", "stage": 4, "count": 3}]
        for appearance in ("dark", "light"):
            fresh(page, settings={"appearance": appearance}, units=arrow_units)
            tab(page, "units")
            accent = rgb(page.evaluate("""() => { const i = document.createElement('i'); i.style.color = 'var(--accent)'; document.body.appendChild(i);
                const c = getComputedStyle(i).color; i.remove(); return c; }"""))
            rows = {}
            for name in ("Zero stage", "Middle stage", "Finished stage"):
                li = page.locator("li.unit", has_text=name)
                btn = li.locator(".up-button")
                rows[name] = page.evaluate("""([n]) => { const li = [...document.querySelectorAll('li.unit')].find(x => x.textContent.includes(n));
                    const b = li.querySelector('.up-button'); const cs = getComputedStyle(b); const st = getComputedStyle(li.querySelector('.stage'));
                    return { text: b.textContent, colour: cs.color, border: cs.borderTopColor, bg: cs.backgroundColor, opacity: cs.opacity,
                             disabled: b.disabled, stage: st.color }; }""", [name])
            z, mid, fin = rows["Zero stage"], rows["Middle stage"], rows["Finished stage"]
            check(f"{appearance}: a new unit's ▲ and a middle unit's ▲ are the same accent colour (arrow and border)",
                  rgb(z["colour"]) == accent == rgb(mid["colour"]) and rgb(z["border"]) == accent == rgb(mid["border"]), (z, mid, accent))
            check(f"{appearance}: the new unit's ▲ is enabled, full strength and readable (contrast at least 4.5)",
                  z["text"] == "▲" and not z["disabled"] and float(z["opacity"]) == 1 and contrast(rgb(z["colour"]), rgb(z["bg"])) >= 4.5,
                  (z, contrast(rgb(z["colour"]), rgb(z["bg"]))))
            check(f"{appearance}: a finished unit still shows a faded tick that is switched off",
                  fin["text"] == "✓" and fin["disabled"] and float(fin["opacity"]) < 0.5, fin)
            check(f"{appearance}: the stage name keeps the stage's own colour (the slate grey of the first stage is not the arrow's colour)",
                  rgb(z["stage"]) != accent and rgb(z["stage"]) != rgb(mid["stage"]), (z["stage"], mid["stage"]))
            check(f"{appearance}: pressing the new unit's ▲ still moves it up a stage",
                  page.evaluate("() => { const li = [...document.querySelectorAll('li.unit')].find(x => x.textContent.includes('Zero stage')); li.querySelector('.up-button').click(); return models.find(m => m.name === 'Zero stage').stage; }") == 1)
            shot(page, f"v46-up-arrow-{appearance}-390.png")

        # ---------- 5. Send full backup with photos to... ----------
        print("\n--- 5. Send full backup with photos to… ---")
        def setup(mode, units=PHOTO_UNITS, photos=("p1", "p2"), settings=OLD):
            downloads.clear()
            fresh(page, settings=dict(settings), units=units, photos=photos)
            fake_share(page, mode)
            open_more(page, "settings")
        def tap(wait=900):
            page.click("#full-share-button")
            page.wait_for_timeout(wait)
        def dates(): s = saved_settings(page); return s.get("lastBackup"), s.get("lastFullBackup")
        def label(): return page.inner_text("#full-share-button").strip()

        setup("ok")
        info = page.evaluate("""() => { const c = document.getElementById('backup-card'); const b = [...c.querySelectorAll('button:not(.more-info-button)')];
            return { ids: b.map(x => x.id), labels: b.map(x => x.textContent.trim()), full: [...c.querySelectorAll('#full-share-button')].map(x => x.style.gridColumn),
                     hint: document.getElementById('share-hint').textContent }; }""")
        check("the button sits straight after Save full backup with photos, full width, with the right words",
              info["ids"] == ["export-button", "share-button", "full-export-button", "full-share-button", "restore-button"] and
              info["labels"][3] == "Send full backup with photos to…" and info["full"] == ["1 / -1"], info)
        check("the hint under the buttons still explains Send backup to… and now mentions the full one",
              "share menu" in info["hint"] and "saves the backup instead" in info["hint"] and "Send full backup with photos to…" in info["hint"], info["hint"])
        check("the old Save backup, Send backup to… and Restore buttons are all still there", info["ids"].count("export-button") == 1 and "share-button" in info["ids"] and "restore-button" in info["ids"])
        state = page.evaluate("""() => { const b = document.getElementById('full-share-button'); b.click();
            return [b.disabled, b.textContent, document.getElementById('full-export-button').disabled]; }""")
        page.wait_for_timeout(900)
        check("while it is putting the backup together, both full-backup buttons are switched off and say 'Preparing backup…'",
              state == [True, "Preparing backup…", True], state)
        got = shared(page)
        check("a working share menu is opened once with one JSON file named for today", len(got) == 1 and got[0]["count"] == 1 and got[0]["type"] == "application/json"
              and got[0]["name"] == f"minifolio-full-backup-{today(page)}.json", [(g["name"], g["type"], g["count"]) for g in got])
        parsed = json.loads(got[0]["text"]) if got else {}
        check("the file holds the units, recipes and both photos as text pictures",
              parsed.get("app") == "Minifolio" and len(parsed.get("models", [])) == 1 and sorted(parsed.get("photoFiles", {})) == ["p1", "p2"]
              and all(v["full"].startswith("data:image/jpeg;base64,") for v in parsed.get("photoFiles", {}).values()), list(parsed)[:6])
        check("nothing was downloaded, and both 'last backed up' dates moved to today", not downloads and dates() == (today(page), today(page)), (len(downloads), dates()))
        check("it says the full backup was sent, with the photo count", "Full backup sent with 2 photos" in toast(page), toast(page))
        check("both buttons are back to normal", label() == "Send full backup with photos to…" and not page.is_disabled("#full-share-button") and not page.is_disabled("#full-export-button"))
        # the file is the same one Save full backup makes
        page.click("#full-export-button"); page.wait_for_timeout(900)
        saved = json.loads(open(downloads[-1].path(), encoding="utf-8").read()) if downloads else {}
        check("Save full backup with photos still downloads, with the same units and photos as the sent file",
              len(downloads) == 1 and downloads[0].suggested_filename == f"minifolio-full-backup-{today(page)}.json"
              and saved.get("photoFiles") == parsed.get("photoFiles") and saved.get("models") == parsed.get("models") and "Full backup saved with 2 photos" in toast(page), toast(page))

        setup("cancel")
        tap()
        check("closing the share menu changes nothing: no download, no date, no 'sent' message, button back to normal",
              len(shared(page)) == 1 and not downloads and dates() == ("2026-01-01", "2026-01-01") and "sent" not in toast(page).lower() and label() == "Send full backup with photos to…"
              and page.evaluate("fullBackupReady") is None, (dates(), toast(page)))

        setup("none")
        tap()
        check("no share menu on this phone: the full backup is saved to the device instead, and the dates move",
              len(downloads) == 1 and downloads[0].suggested_filename.startswith("minifolio-full-backup-") and dates() == (today(page), today(page))
              and "can't send files to other apps" in toast(page) and "saved to your device instead" in toast(page) and "2 photos" in toast(page), toast(page))
        setup("nocan")
        tap()
        check("canShare says no: nothing is shared, the backup is saved instead", shared(page) == [] and len(downloads) == 1 and "saved to your device instead" in toast(page), toast(page))
        setup("fail")
        tap()
        check("the share menu fails: the backup is saved instead and the app says so",
              len(downloads) == 1 and "couldn't send the full backup" in toast(page) and dates() == (today(page), today(page)), toast(page))

        setup("late")
        tap()
        check("a tap that came too late for the share menu: nothing is saved yet, no date moves, and the button says 'Backup ready: tap to send'",
              not downloads and dates() == ("2026-01-01", "2026-01-01") and label() == "Backup ready: tap to send" and page.evaluate("fullBackupReady !== null")
              and "ready" in toast(page), (label(), toast(page), dates()))
        first_text = shared(page)[0]["text"]
        tap()
        got = shared(page)
        check("the second tap opens the share menu with the very same finished file (it is not put together again)",
              len(got) == 2 and got[1]["text"] == first_text and got[1]["name"] == got[0]["name"], [(g["name"], len(g["text"])) for g in got])
        check("then the dates move, it says sent, nothing is downloaded and the button is back to normal",
              dates() == (today(page), today(page)) and not downloads and "Full backup sent with 2 photos" in toast(page)
              and label() == "Send full backup with photos to…" and page.evaluate("fullBackupReady") is None, (dates(), toast(page), label()))

        setup("refused")
        tap()
        check("if the first tap is refused it waits; if the second is refused too, the backup is saved instead",
              label() == "Backup ready: tap to send" and not downloads, label())
        tap()
        check("the second refusal saves the backup to the device with an honest message",
              len(downloads) == 1 and "couldn't send the full backup" in toast(page) and dates() == (today(page), today(page)) and label() == "Send full backup with photos to…", (toast(page), label()))
        setup("late")
        tap()
        page.evaluate("dropReadyBackup()")
        check("a finished backup that is dropped (it is kept for two minutes at most) puts the button back to normal",
              label() == "Send full backup with photos to…" and page.evaluate("fullBackupReady") is None)
        check("the waiting time is two minutes", "120000" in app[app.index("fullBackupTimer = setTimeout"):app.index("fullBackupTimer = setTimeout") + 80])

        setup("ok")
        page.evaluate("async () => { await photoStore('readwrite', store => store.delete('p2')); }")   # p2 can no longer be found
        tap()
        got = shared(page)
        parsed = json.loads(got[0]["text"]) if got else {}
        check("a photo that can't be found is left out and counted honestly (here: 1 of 2)",
              sorted(parsed.get("photoFiles", {})) == ["p1"] and "1 photo (1 couldn't be read)" in toast(page), toast(page))
        setup("ok", units=BASE_UNITS, photos=())
        tap()
        check("with no photos at all it still sends, saying 0 photos", len(shared(page)) == 1 and "0 photos" in toast(page), toast(page))

        # ---------- 6. Phone widths ----------
        print("\n--- 6. Phone widths, dark and light ---")
        for appearance in ("dark", "light"):
            for width in (390, 360):
                page.set_viewport_size({"width": width, "height": 800})
                tag = f"{appearance} {width}px"
                fresh(page, settings={"appearance": appearance}, units=BASE_UNITS)
                tab(page, "dashboard")
                check(f"{tag}: the Dashboard line with 'under way' is fully visible and nothing scrolls sideways",
                      "under way" in page.inner_text("#done-summary") and no_sideways(page) and
                      page.evaluate("() => { const e = document.getElementById('done-summary'); return e.getBoundingClientRect().right <= window.innerWidth + 1; }"))
                shot(page, f"v46-dashboard-{appearance}-{width}.png")
                open_more(page, "settings")
                sizes = page.evaluate("""() => [...document.querySelectorAll('#backup-card button:not(.more-info-button)')].map(b => { const r = b.getBoundingClientRect();
                    return { id: b.id, h: r.height, w: r.width, clipped: b.scrollWidth > b.clientWidth + 1, inside: r.left >= 0 && r.right <= window.innerWidth + 1 }; })""")
                check(f"{tag}: all five backup buttons are at least 44 px tall, fully inside the screen, with no clipped words",
                      len(sizes) == 5 and all(s["h"] >= 44 and s["inside"] and not s["clipped"] for s in sizes), sizes)
                check(f"{tag}: Settings does not scroll sideways", no_sideways(page))
                page.locator("#full-share-button").scroll_into_view_if_needed()
                shot(page, f"v46-backup-card-{appearance}-{width}.png")
        page.set_viewport_size({"width": 390, "height": 844})

        # ---------- 7. Clean run ----------
        print("\n--- 7. A clean run ---")
        check("no page errors", not errors, errors[:2])
        check("no browser pop-ups", not popups, popups[:2])
        check("no Content Security Policy errors", not csp, csp[:2])
        browser.close()
    failed = results.count(False)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
