"""v19.1 tests for Minifolio: the "Buy these" bar on the shopping list, and file checks.

(This is the second half of the v19 plan, called "v19b" in the notes. App version: v19.1.)

Checks:
1. Version numbers, the Updates entry, CNAME and the ocr folder kept, storage names unchanged.
2. Shop list: every shop's details in ONE list (SHOPS), plain links (no affiliate codes yet).
3. Buy these bar: at the top of the shopping list; one button per shop that sells something on the
   list (The Army Painter only for Army Painter paints); tapping a shop shows a search link per paint,
   opening in a new tab without telling the shop where you came from; a paint name with HTML in it
   is shown as plain text; an empty list has no bar and the old "Coming later" box is gone.
4. Import CSV: needs a "name" column; columns found by title in any order; pictures, Excel files,
   non-text files and files over 2 MB are refused and nothing changes; a normal CSV still works.
5. Restore backup: pictures, files over 300 MB and damaged backups are refused; a good one still works.
6. Help: shopping list, Privacy, About, CSV and backup checks explained.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

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

EVIL = "<img src=x onerror=alert(1)>"
BOOK = {
    "paints": [
        {"id": 1, "brand": "Citadel", "name": "Macragge Blue", "colour": "#1f3a8a", "status": "wishlist"},
        {"id": 2, "brand": "The Army Painter", "name": "Matt White", "colour": "#f5f5f5", "status": "empty"},
        {"id": 3, "brand": "Vallejo", "name": "Ivory", "colour": "#efe6cf", "status": "low"},
        {"id": 4, "brand": "Citadel", "name": "Nuln Oil", "colour": "#222222", "status": "owned"},
    ],
    "recipes": [], "schemes": [],
}
CITADEL_ONLY = {"paints": [BOOK["paints"][0], BOOK["paints"][3]], "recipes": [], "schemes": []}
ALL_OWNED = {"paints": [BOOK["paints"][3]], "recipes": [], "schemes": []}
EVIL_BOOK = {"paints": [{"id": 1, "brand": "Citadel", "name": EVIL, "colour": "#222222", "status": "wishlist"}],
             "recipes": [], "schemes": []}
UNITS = [{"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 0, "count": 5}]
# The first bytes of a real PNG picture (includes zero bytes, like every picture file).
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082")

def seed(page, units=None, book=None):
    page.goto(URL)
    page.evaluate("""([u, b]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u || []));
        if (b) localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b)); }""", [units, book])
    page.reload()
    page.wait_for_timeout(300)

def tab(page, name):
    page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(80)

def open_shop(page):
    page.evaluate("showTab('recipes')")
    page.click("#recipe-seg button[data-view='palette']")
    page.click("#shop-button")
    page.wait_for_timeout(100)

def shop_buttons(page):
    return page.locator("#buy-bar .buy-shops button").all_inner_texts()

def links(page):
    return page.evaluate("""[...document.querySelectorAll('#buy-links a')].map(a =>
        ({ text: a.querySelector('span').textContent, href: a.getAttribute('href'), target: a.target, rel: a.rel }))""")

def stored_units(page):
    return json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))

def main():
    sw = read("sw.js")
    html = read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialogs = []
        def on_dialog(d):
            dialogs.append(d.message)
            d.accept()
        page.on("dialog", on_dialog)

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        seed(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v19.1 or later", float(version[1:]) >= 19.1, version)
        check("APP_VERSION is a plain number (no letters)", re.fullmatch(r"v\d+(\.\d+)?", version), version)
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        tab(page, "updates")
        heads = page.locator("#changelog h3").all_inner_texts()
        v191 = [i for i, h in enumerate(heads) if h.startswith("v19.1")]
        check("the Updates tab has a v19.1 entry", bool(v191), heads[:3])
        if v191:
            text = page.locator("#changelog .release").nth(v191[-1]).inner_text()
            check("the v19.1 entry mentions Buy these, Import CSV and Restore backup",
                  "Buy these" in text and "Import CSV" in text and "Restore backup" in text, text)
        check("CNAME file kept (minifolio.app)", read("CNAME").strip() == "minifolio.app")
        check("ocr folder kept", all(os.path.exists(os.path.join(ROOT, "ocr", f)) for f in
                                     ["ocr-worker.js", "eng.traineddata", "tesseract-core-simd-lstm.wasm"]))
        for key in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"',
                    'RECIPES_KEY = "shades-of-grey-recipes"', "shades-of-grey-recipes-before-recipes-restore"]:
            check(f"storage name kept: {key}", key in html)
        check("DATA_VERSION unchanged (saved data didn't change shape)", page.evaluate("DATA_VERSION") == 1)

        # ---------- 2. The shop list ----------
        print("--- 2. The shop list ---")
        shops = page.evaluate("SHOPS")
        names = [s["name"] for s in shops]
        check("SHOPS has the four agreed shops",
              names == ["Firestorm Games", "Wayland Games", "Element Games", "The Army Painter"], names)
        check("every shop has a name, an https search address, brands and an extra slot",
              all(s["search"].startswith("https://") and "brands" in s and "extra" in s for s in shops), shops)
        check("no affiliate codes yet (extra is empty for every shop)", all(s["extra"] == "" for s in shops))
        check("The Army Painter only sells Army Painter paints",
              shops[3]["brands"] == ["The Army Painter"] and all(s["brands"] == "all" for s in shops[:3]))
        check("search addresses are the ones checked on 10 Oct", [s["search"] for s in shops] == [
              "https://www.firestormgames.co.uk/products?q={q}",
              "https://www.waylandgames.co.uk/search?query={q}&q={q}",
              "https://elementgames.co.uk/search?q={q}",
              "https://thearmypainter.com/search?q={q}"], [s["search"] for s in shops])
        check("every shop's address was checked by hand", all(s["checked"] for s in shops), shops)
        check("Wayland gets the paint's name in both places it needs",
              page.evaluate("shopLink(SHOPS[1], { brand: 'Citadel', name: 'Nuln Oil' })") ==
              "https://www.waylandgames.co.uk/search?query=Nuln+Oil&q=Nuln+Oil")
        check("an affiliate code would go on the end of every link (tried with a pretend code)",
              page.evaluate("shopLink({ ...SHOPS[0], extra: '&ref=TEST' }, { name: 'Nuln Oil' })") ==
              "https://www.firestormgames.co.uk/products?q=Nuln+Oil&ref=TEST")

        # ---------- 3. Buy these bar ----------
        print("--- 3. Buy these bar ---")
        seed(page, [], BOOK)
        open_shop(page)
        check("the Buy these bar shows on the shopping list", page.is_visible("#buy-bar"))
        check("…headed 'Buy these'", page.inner_text("#buy-bar h3") == "Buy these")
        order = page.evaluate("""(() => { const card = document.querySelector('#shop-panel .card');
            const kids = [...card.children]; return [kids.indexOf(document.getElementById('buy-bar')),
            kids.findIndex(k => k.classList.contains('shop-brand'))]; })()""")
        check("…at the top, above the brand groups", 0 <= order[0] < order[1], order)
        check("the old 'Coming later' box is gone", page.locator("#shop-links-slot").count() == 0
              and "Coming later" not in page.inner_text("#shop-panel"))
        check("one button per shop, Army Painter included (an Army Painter paint is on the list)",
              shop_buttons(page) == ["Firestorm Games", "Wayland Games", "Element Games", "The Army Painter"],
              shop_buttons(page))
        btn_h = page.locator("#buy-bar .buy-shops button").first.bounding_box()["height"]
        check("shop buttons are big enough to tap (44 px)", btn_h >= 44, btn_h)
        check("no links show until a shop is tapped", page.locator("#buy-links").count() == 0)
        page.screenshot(path=f"{SHOTS}/v19_1-buy-bar.png")

        page.click("#buy-bar button[data-shop='firestorm']")
        page.wait_for_timeout(100)
        got = links(page)
        check("Firestorm: one link per paint on the list (3)", len(got) == 3, got)
        by_name = {g["text"]: g for g in got}
        check("Citadel paint: the name alone", by_name.get("Macragge Blue", {}).get("href") ==
              "https://www.firestormgames.co.uk/products?q=Macragge+Blue", by_name.get("Macragge Blue"))
        # The brand is left out on purpose: shops' titles often don't include it, so
        # "The Army Painter Matt White" found nothing at Firestorm (checked 10 Oct).
        check("Army Painter paint: the name alone", by_name.get("Matt White", {}).get("href") ==
              "https://www.firestormgames.co.uk/products?q=Matt+White", by_name.get("Matt White"))
        check("Vallejo paint: the name alone", by_name.get("Ivory", {}).get("href") ==
              "https://www.firestormgames.co.uk/products?q=Ivory", by_name.get("Ivory"))
        check("links open in a new tab", all(g["target"] == "_blank" for g in got), got)
        check("links don't tell the shop where you came from (noopener noreferrer)",
              all("noopener" in g["rel"] and "noreferrer" in g["rel"] for g in got), got)
        check("the open shop's button is marked as open",
              page.get_attribute("#buy-bar button[data-shop='firestorm']", "aria-expanded") == "true")
        check("the note says they're plain links", "Plain links" in page.inner_text("#buy-bar"))
        link_h = page.locator("#buy-links a").first.bounding_box()["height"]
        check("links are big enough to tap (44 px)", link_h >= 44, link_h)
        page.screenshot(path=f"{SHOTS}/v19_1-buy-links.png")

        page.click("#buy-bar button[data-shop='element']")
        page.wait_for_timeout(100)
        got = links(page)
        check("tapping another shop switches to its links",
              len(got) == 3 and all(g["href"].startswith("https://elementgames.co.uk/search?q=") for g in got), got)
        page.click("#buy-bar button[data-shop='armypainter']")
        page.wait_for_timeout(100)
        got = links(page)
        check("The Army Painter: only the Army Painter paint",
              [g["href"] for g in got] == ["https://thearmypainter.com/search?q=Matt+White"], got)
        page.click("#buy-bar button[data-shop='armypainter']")
        page.wait_for_timeout(100)
        check("tapping the open shop again closes its links", page.locator("#buy-links").count() == 0)
        check("the links send nothing but the paint name (no app or personal details)",
              all("minifolio" not in page.evaluate(f"shopLink(SHOPS[{i}], {{ brand: 'Citadel', name: 'Nuln Oil' }})").lower()
                  for i in range(4)))

        seed(page, [], CITADEL_ONLY)
        open_shop(page)
        check("only Citadel paints on the list: no Army Painter button",
              shop_buttons(page) == ["Firestorm Games", "Wayland Games", "Element Games"], shop_buttons(page))

        seed(page, [], ALL_OWNED)
        open_shop(page)
        check("nothing to buy: no Buy these bar", page.locator("#buy-bar").count() == 0)
        check("…and no 'Coming later' box", "Coming later" not in page.inner_text("#shop-panel"))

        seed(page, [], EVIL_BOOK)
        before = len(dialogs)
        open_shop(page)
        page.click("#buy-bar button[data-shop='firestorm']")
        page.wait_for_timeout(200)
        got = links(page)
        check("a paint name with HTML in it shows as plain text", got and got[0]["text"] == EVIL, got)
        check("…and runs nothing", len(dialogs) == before and page.locator("#buy-links img").count() == 0, dialogs[before:])
        check("…and is safely encoded in the link",
              got and "<" not in got[0]["href"] and got[0]["href"].startswith("https://www.firestormgames.co.uk/products?q=%3Cimg"), got)

        # ---------- 4. Import CSV checks ----------
        print("--- 4. Import CSV checks ---")
        def csv_try(name, data, mime="text/csv"):
            seed(page, UNITS)
            tab(page, "settings")
            n = len(dialogs)
            page.set_input_files("#csv-file", files=[{"name": name, "mimeType": mime, "buffer": data}])
            page.wait_for_timeout(300)
            return dialogs[n:], page.is_visible("#review")

        said, review = csv_try("nonames.csv", b"unit_title,faction\nBoyz,Orks\n")
        check("CSV without a name column is refused", said and 'no "name" column' in said[0] and not review, said)
        check("…and nothing changed", [u["name"] for u in stored_units(page)] == ["Intercessors"])
        said, review = csv_try("noheader.csv", b"Boyz,40K,Orks,,,10,no,\n")
        check("CSV without column titles is refused too", said and 'no "name" column' in said[0] and not review, said)
        said, review = csv_try("picture.png", PNG, "image/png")
        check("a picture is refused before reading", said and "isn't a CSV file" in said[0] and not review, said)
        said, review = csv_try("renamed.csv", PNG)
        check("a picture renamed to .csv is refused (not plain text)", said and "isn't a CSV file" in said[0] and not review, said)
        said, review = csv_try("army.xlsx", b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        check("an Excel file gets a 'save it as CSV' message", said and "spreadsheet file, not a CSV" in said[0] and not review, said)
        big = b"name\n" + b"Boyz\n" * (430 * 1024)
        said, review = csv_try("huge.csv", big)
        check("a CSV over 2 MB is refused", said and "too big" in said[0] and "2 MB" in said[0] and not review, said)
        check("…and nothing changed", [u["name"] for u in stored_units(page)] == ["Intercessors"])
        check("a picture never turns into units", not any(u["name"] != "Intercessors" for u in stored_units(page)))

        said, review = csv_try("reordered.csv", b"faction,count,Name\nOrks,10,Boyz\nOrks,1,Warboss\n")
        check("columns in another order (and 'Name' in capitals) are read by their titles", review and not said, said)
        page.click("#review-go")
        page.wait_for_timeout(300)
        got = {u["name"]: u for u in stored_units(page)}
        check("…Boyz imported with faction Orks and 10 models",
              got.get("Boyz", {}).get("faction") == "Orks" and got.get("Boyz", {}).get("count") == 10, got.get("Boyz"))
        said, review = csv_try("template.csv",
            b"name,game,faction,stage,nickname,count,repaint,notes\nRedemptor,40K,Ultramarines,,,1,yes,\"Magnetised, swaps guns\"\n")
        check("a normal CSV (template columns) still works", review and not said, said)
        page.click("#review-go")
        page.wait_for_timeout(300)
        got = {u["name"]: u for u in stored_units(page)}
        check("…with repaint and notes read", got.get("Redemptor", {}).get("repaint") is True
              and "swaps guns" in (got.get("Redemptor", {}).get("note") or ""), got.get("Redemptor"))

        # ---------- 5. Restore backup checks ----------
        print("--- 5. Restore backup checks ---")
        def restore_try(name, data, mime="application/json"):
            seed(page, UNITS)
            tab(page, "settings")
            n = len(dialogs)
            page.set_input_files("#restore-file", files=[{"name": name, "mimeType": mime, "buffer": data}])
            page.wait_for_timeout(500)
            return dialogs[n:]

        good = {"app": "Minifolio", "version": 6, "dataVersion": 1, "stages": page.evaluate("STAGES"),
                "models": [{"id": 9, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 10}]}
        said = restore_try("photo.jpg", PNG, "image/jpeg")
        check("a picture is refused as a backup", said and "isn't a Minifolio backup" in said[0], said)
        for label, bad in [("units that aren't a list", {**good, "models": {"a": 1}}),
                           ("recipes that are a list", {**good, "recipes": [1, 2]}),
                           ("photos that are a list", {**good, "photoFiles": ["x"]})]:
            said = restore_try("bad.json", json.dumps(bad).encode())
            check(f"a damaged backup ({label}) is refused", said and "damaged" in said[0], said)
            check("…and nothing changed", [u["name"] for u in stored_units(page)] == ["Intercessors"])
        too_big = page.evaluate("fileProblem({ name: 'b.json', size: 301 * 1024 * 1024, type: 'application/json' }, 'backup')")
        check("a backup over 300 MB is refused (before reading it)", "too big" in too_big and "300 MB" in too_big, too_big)
        ok_size = page.evaluate("fileProblem({ name: 'b.json', size: 250 * 1024 * 1024, type: 'application/json' }, 'backup')")
        check("a big full backup under 300 MB is allowed", ok_size == "", ok_size)
        said = restore_try("good.json", json.dumps(good).encode())
        check("a good backup still restores", [u["name"] for u in stored_units(page)] == ["Hormagaunts"], said)

        # ---------- 6. Help ----------
        print("--- 6. Help ---")
        tab(page, "help")
        shop_help = page.text_content("#help-shop") or ""
        check("Help explains Buy these and names the shops",
              "Buy these" in shop_help and all(n in shop_help for n in ["Firestorm", "Wayland", "Element", "Army Painter"]), shop_help)
        check("…and says they're plain links", "plain links" in shop_help, shop_help)
        privacy = page.text_content("#privacy")
        check("Privacy explains shop links (only the paint's name goes out)", "Shop links" in privacy and "paint's name" in privacy, privacy)
        about = page.text_content("#about")
        check("About mentions shop links in what's sent", "shop link" in about, about)
        check("Help explains the CSV checks", "name" in (page.text_content("#help-csv-checks") or "")
              and "2 MB" in (page.text_content("#help-csv-checks") or ""))
        check("Help explains the backup checks", "300 MB" in (page.text_content("#help-backup-checks") or ""))
        check("no page errors", not errors, errors)

        browser.close()

    passed = sum(results)
    print(f"\n{passed} passed, {len(results) - passed} failed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
