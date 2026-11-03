"""SEC1 tests for Minifolio (fixes from the 2 Nov local security test). New behaviour only.

1. Photos: a backup can't store an SVG (or any type but JPEG, PNG and WebP) as a photo. Old-style photos are drawn
   again as a fresh JPEG when they move to the photo store; anything else is left out and counted in the restore message.
2. Framing: with the _headers file's rules on the response (as Cloudflare sends them), another site can't show the
   app inside its page, while the app's own both-views.html still shows its two copies, and the app opens on its own.
3. The HTML safety scan catches the lines the security test slipped past it.
4. Long names from a backup or CSV file are cut to the typing limits; a very long name saved earlier is drawn quickly
   (cut short on screen, unchanged in storage); a broken address such as #% doesn't stop start-up; "constructor"
   is never matched to a built-in like "Object", and never breaks the Mentor.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import base64, json, os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
import test_html_safety as scan
from launch_helpers import app_ready, quiet

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def unit(i, **kw):
    u = {"id": i, "name": "Unit %d" % i, "count": 1, "stage": 0, "faction": "Orks", "hobby": "40K"}
    u.update(kw)
    return u

# A real 8x8 PNG, so the app can draw it again as a JPEG.
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGM4YWODFTEMLQkAZZlQAVIPr1MAAAAASUVORK5CYII="
SVG = "data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>document.title="ran"</script></svg>').decode()

def restore(page, backup):
    page.set_input_files("#restore-file", files=[{"name": "b.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
    page.wait_for_selector("#dialog-yes", state="visible")
    page.click("#dialog-yes")

def header_rules():
    rules, path = {}, None
    for line in open(os.path.join(ROOT, "_headers"), encoding="utf-8"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            path = line.strip()
            continue
        k, v = line.strip().split(":", 1)
        rules.setdefault(path, {})[k.strip()] = v.strip()
    return rules.get("/*", {})

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        popups = []
        page.on("dialog", lambda d: (popups.append(d.message), d.dismiss()))

        print("\n--- 1. Photos ---")
        t.load(page, units=[unit(9, photo=SVG), unit(8, photo=PNG)])
        saved = page.evaluate("() => models.map(m => [m.id, !!(m.photo || m.photos)])")
        check("an SVG old-style photo saved on this device is dropped when the app opens; the units and a real photo stay",
              saved == [[9, False], [8, True]], saved)
        check("turning an SVG back into a picture is refused",
              page.evaluate("s => { try { dataUrlToBlob(s); return false } catch (e) { return true } }", SVG))
        page.evaluate("""() => { window.__toasts = []; const el = document.getElementById('toast');
            new MutationObserver(() => window.__toasts.push(el.innerText)).observe(el, { childList: true, subtree: true, characterData: true }); }""")
        restore(page, {"models": [unit(1, name="Svg", photo=SVG), unit(2, name="Old", photo=PNG), unit(3, name="New", photos=[{"id": "pf-png"}])],
                       "photoFiles": {"pf-png": {"full": PNG, "thumb": PNG}, "pf-svg": {"full": SVG, "thumb": SVG}}})
        page.wait_for_function("() => models.length === 3 && !models.find(m => m.name === 'Old').photo", timeout=10000)
        page.wait_for_function("() => window.__toasts.some(x => x.includes('Backup restored'))", timeout=10000)
        toast = [x for x in page.evaluate("window.__toasts") if "Backup restored" in x]
        check("the restore message counts the 2 photos left out", "2 photos left out: not a JPEG, PNG or WebP" in toast[-1], toast)
        stored = page.evaluate("""async () => {
            const old = models.find(m => m.name === 'Old'), svg = models.find(m => m.name === 'Svg');
            const moved = old.photos && await getPhoto(old.photos[0].id);
            return { svgUnit: !svg.photo && !svg.photos, moved: moved && [moved.full.type, moved.thumb.type],
                     pfSvg: !!(await getPhoto('pf-svg')), pfPng: !!(await getPhoto('pf-png')) }; }""")
        check("the SVG unit keeps no photo, and the SVG photo file is not in the photo store", stored["svgUnit"] and not stored["pfSvg"], stored)
        check("a real old-style photo moves to the photo store drawn again as a JPEG", stored["moved"] == ["image/jpeg", "image/jpeg"], stored)
        check("a real photo file from the backup is restored", stored["pfPng"], stored)

        print("\n--- 2. Framing ---")
        rules = header_rules()
        url = t.URL
        def with_headers(route):
            r = route.fetch()
            route.fulfill(response=r, headers={**r.headers, **rules})
        fctx = browser.new_context(service_workers="block")
        origin = url.split("/index.html")[0]
        fctx.route(origin + "/**", with_headers)
        fctx.route("http://elsewhere.test/**", lambda r: r.fulfill(content_type="text/html",
                   body=f'<iframe src="{url}#settings" width="390" height="600"></iframe>'))
        fpage = fctx.new_page()
        fpage.goto("http://elsewhere.test/csp-probe-frame.html")   # a refusal on purpose: "csp-probe" tells the CSP watcher
        fpage.wait_for_timeout(1500)
        inside = [f for f in fpage.frames if f.url.startswith(origin)]
        check("another site can't show the app inside its page", not inside, [f.url for f in fpage.frames])
        fpage.goto(origin + "/both-views.html")
        fpage.wait_for_function("() => [...document.querySelectorAll('iframe')].every(f => { try { return typeof f.contentWindow.showTab === 'function' } catch (e) { return false } })", timeout=15000)
        check("the app's own both-views.html still shows both copies", len([f for f in fpage.frames if "/index.html" in f.url]) == 2, [f.url for f in fpage.frames])
        fpage.goto(url)
        app_ready(fpage)
        check("the app still opens on its own with those headers", fpage.evaluate("() => typeof showTab === 'function'"))
        fctx.close()

        print("\n--- 3. HTML safety scan ---")
        check("the scan catches every line the security test slipped past it", all(scan.caught(b) for b in scan.BYPASSES))

        print("\n--- 4. Long names, broken address, built-in words ---")
        t.load(page, units=[unit(9)])
        long = "N" * 500
        restore(page, {"models": [unit(1, name=long, hobby="H" * 500, faction="F" * 500, nickname="K" * 500)],
                       "recipes": {"paints": [], "recipes": [{"id": 1, "name": "R" * 500, "steps": []}],
                                   "schemes": [{"id": 1, "name": "S" * 500, "faction": "F" * 500, "recipes": [1]}]}})
        page.wait_for_function("() => models.length === 1 && models[0].name.startsWith('NNN')", timeout=10000)
        lens = page.evaluate("() => [models[0].name, models[0].hobby, models[0].faction, models[0].nickname, book.recipes[0].name, book.schemes[0].name, book.schemes[0].faction].map(s => s.length)")
        check("a backup's unit name, game, faction and nickname are cut to 80, recipe and scheme names to 200",
              lens == [80, 80, 80, 80, 200, 200, 80], lens)
        csv = "name,game,faction\n" + "C" * 300 + ",Game," + "F" * 300 + "\n"
        page.set_input_files("#csv-file", files=[{"name": "u.csv", "mimeType": "text/csv", "buffer": csv.encode()}])
        page.wait_for_function("() => incoming && incoming.rows.length === 1", timeout=10000)
        check("a CSV file's name and faction are cut to 80", page.evaluate("() => [incoming.rows[0].name.length, incoming.rows[0].faction.length]") == [80, 80])

        huge = "A" * 20000
        t.load(page, units=[unit(1, name=huge)])
        took = page.evaluate("() => { showTab('units'); const s = performance.now(); renderUnits(); document.body.offsetHeight; return performance.now() - s; }")
        shown = page.evaluate("() => document.querySelector('#unit-list .unit .name').textContent")
        check("a 20,000-character name saved earlier is drawn in under half a second", took < 500, round(took))
        check("it shows cut short with an ellipsis and stays whole in storage",
              shown.endswith("…") and len(shown) < 400 and page.evaluate("() => models[0].name.length") == 20000, len(shown))

        before = len(errors)
        for frag in ["#%", "#%E0%A4%A"]:
            page.goto(t.URL + frag)
            app_ready(page)
        check("a broken address (#% and #%E0%A4%A) doesn't stop start-up",
              len(errors) == before and page.evaluate("() => launchMotionReady === true"), errors[before:])

        r = page.evaluate("""() => { const out = {};
            out.shorthand = [shorthandFor('constructor'), shorthandFor('toString'), shorthandFor('__proto__')];
            out.match = ['constructor', 'valueOf', 'hasOwnProperty'].map(w => { const m = matchPaint(w); return m.status + ':' + (m.paint && m.paint.name); });
            showTab('constructor'); out.tab = settings.tab; return out; }""")
        check("'constructor', 'valueOf' and similar words never match a built-in such as Object",
              r["shorthand"] == [None, None, None] and not any(":Object" in m or "function" in m for m in r["match"]) and r["tab"] == "dashboard", r)

        mentor = page.evaluate("""() => ['constructor armour', 'what colour goes with constructor', 'toString eyes'].map(q => {
            try { return MinifolioMentor.mentorAnswer(q, { index: { entries: [] }, paints: [], colour: MinifolioColour }).kind } catch (e) { return 'ERR ' + e.message } })""")
        check("the Mentor answers 'constructor' and 'toString' questions instead of failing", not any(k.startswith("ERR") for k in mentor), mentor)

        check("no page errors", not errors, errors[:5])
        check("no browser pop-ups", not popups, popups[:3])
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
