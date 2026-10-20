"""v21.7 tests for Minifolio: the in-app question box (no more browser confirm() / prompt() pop-ups).

Written the "v21.7 or later" way, so it still passes after later versions.

Checks:
1. Version numbers (plain numbers), sw.js and both ?v= tags match, the Updates entry, kept things (CNAME,
   the ocr folder, LICENSE-paint-list.txt, the passive ZAP workflow, the CSP exactly as v21.4, storage
   names, DATA_VERSION 1), no code in index.html.
2. The source: no alert( / confirm( / prompt( left in app.js (comments aside), the box's markup in
   index.html has role="dialog", aria-modal and a label, and backTarget() puts the box at the very top.
3. The box itself, with REAL taps and key presses: Yes / No buttons, Escape = No, Enter = Yes, focus moves
   into the box and goes back to what was pressed, Tab stays inside, the phone's Back button = No, a second
   question replaces the first (counting as No), "type a name" boxes (typed text, OK, Cancel, Escape, Enter),
   the copy box, buttons at least 44 px, long names wrap.
4. Every question the app asks (16 yes/no, 5 type-a-name): it still says the same words, "No" leaves
   everything as it was, "Yes" does what it did before.
5. Dark and light screenshots at 390 and 360 px, readable colours, the box inside the screen, nothing scrolls
   sideways; no browser pop-up at any point, no page errors, no CSP errors.
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

STAGES = ["Unassembled", "Part assembled", "Assembled", "Primed", "Part painted",
          "Battle ready", "Painted with issues", "Parade ready"]
UNITS = [
    {"id": 1, "name": "Intercessors", "hobby": "40K", "faction": "Ultramarines", "stage": 3, "count": 5,
     "log": [["2026-09-01", 0], ["2026-09-05", 3]]},
    {"id": 2, "name": "Termagants", "hobby": "40K", "faction": "Tyranids", "stage": 4, "count": 10,
     "log": [["2026-09-01", 1], ["2026-09-10", 4]]},
    {"id": 3, "name": "Boyz", "hobby": "40K", "faction": "Orks", "stage": 1, "count": 2, "each": True, "stages": [1, 3],
     "log": [["2026-09-01", 1]]},
]
def paint(pid, name, brand="Citadel", colour="#3b5b7a", **extra):
    return {"id": pid, "brand": brand, "name": name, "colour": colour, **extra}
BOOK = {
    "paints": [paint(1, "Macragge Blue"), paint(2, "Macrage Blue", colour="#112233"), paint(4, "Mephiston Red", status="owned")],
    "recipes": [{"id": 1, "name": "Armour", "part": "Armour", "notes": "", "steps": [
        {"technique": "Base coat", "coats": 1, "paints": [{"paint": 2, "mix": 100}]},
        {"technique": "Layer", "coats": 1, "paints": [{"paint": 4, "mix": 100}]}]}],
    "schemes": [{"id": 1, "name": "My Ultramarines", "faction": "Ultramarines", "auto": True, "recipes": [1]}],
    "parts": ["Armour", "Trim"], "techniques": ["Base coat", "Layer"], "v15": True, "shorthand": {},
}
V21_4_CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
             "img-src 'self' blob: data: https://dim3ry.goatcounter.com/count; media-src 'self' blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; "
             "manifest-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")

def full_settings(**extra):
    s = {"palette": "ice", "tab": "units", "stages": STAGES, "doneFrom": 5, "examplesChecked": True}
    s.update(extra)
    return s

def start(page, units=UNITS, book=BOOK, settings=None):
    page.goto(BASE + "manifest.json")
    page.evaluate("""async ([u, b, s]) => { localStorage.clear();
        localStorage.setItem('mini-tracker-models', JSON.stringify(u));
        localStorage.setItem('shades-of-grey-recipes', JSON.stringify(b));
        localStorage.setItem('shades-of-grey-settings', JSON.stringify(s));
        await new Promise(done => { const r = indexedDB.deleteDatabase('shades-of-grey-photos');
                                    r.onsuccess = r.onerror = r.onblocked = () => done(); }); }""",
                  [units, book, settings or full_settings()])
    page.goto(URL)
    page.wait_for_function("() => typeof APP_VERSION === 'string'")
    page.wait_for_timeout(300)

def tab(page, name):
    if name in ("help", "updates"):   # v21.9: these are sub-tabs of Settings now
        page.click('nav button[data-tab="settings"]')
        page.click(f'#more-seg button[data-page="{name}"]')
    else:
        page.click(f'nav button[data-tab="{name}"]')
    page.wait_for_timeout(150)

def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name))

def no_sideways(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def box_open(page):
    return page.evaluate("() => !document.getElementById('dialog-backdrop').classList.contains('hidden')")

def box_text(page):
    return page.evaluate("() => document.getElementById('dialog-message').textContent")

def box_kind(page):
    return page.evaluate("""() => !document.getElementById('dialog-input').classList.contains('hidden') ? 'text'
        : !document.getElementById('dialog-area').classList.contains('hidden') ? 'show' : 'yesno'""")

def yes(page):
    page.click("#dialog-yes")
    page.wait_for_timeout(150)

def no(page):
    page.click("#dialog-no")
    page.wait_for_timeout(150)

def asks(page, expected):
    """The box is open and says this (a string, or a compiled regex)."""
    if not box_open(page):
        return False
    text = box_text(page)
    return bool(expected.search(text)) if hasattr(expected, "search") else text == expected

def saved_units(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mini-tracker-models') || '[]')")

def saved_book(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('shades-of-grey-recipes') || '{}')")

def toast(page):
    return page.evaluate("""() => { const t = document.getElementById('toast');
        return { shown: !t.classList.contains('hidden'), text: document.getElementById('toast-text').textContent,
                 undo: !document.getElementById('toast-undo').classList.contains('hidden') }; }""")

def rgb(text):
    return [int(x) for x in re.findall(r"\d+(?:\.\d+)?", text)[:3]]

def luminance(c):
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)

def main():
    errors, csp, native = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
        def on_native(d):
            native.append((d.type, d.message))
            d.dismiss()
        page.on("dialog", on_native)   # any browser pop-up at all is a failure

        # ---------- 1. Versions and kept things ----------
        print("--- 1. Versions and kept things ---")
        start(page)
        version = page.evaluate("APP_VERSION")
        check("APP_VERSION is v21.7 or later", float(version[1:]) >= 21.7, version)
        check("version is a plain number", re.fullmatch(r"v\d+(\.\d+)?", version) is not None, version)
        sw = read("sw.js")
        m = re.search(r'const VERSION = "(v[\d.]+)"', sw)
        check("sw.js VERSION matches APP_VERSION", m and m.group(1) == version, m and m.group(1))
        index = read("index.html")
        tags = re.findall(r'<script src="(early|app)\.js\?v=([\d.]+)"></script>', index)
        check("both script tags carry ?v= matching APP_VERSION", sorted(tags) == [("app", version[1:]), ("early", version[1:])], tags)
        entry = page.evaluate("CHANGELOG.find(r => r.version === 'v21.7')")
        if page.evaluate("['v21.7'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("Updates has a v21.7 entry", entry and len(entry["changes"]) >= 2, entry)
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'Updates has a v21.7 entry')
        check("v21.7 is the newest Updates entry or later", float(page.evaluate("CHANGELOG[0].version")[1:]) >= 21.7)
        tab(page, "updates")
        heads = page.evaluate("() => [...document.querySelectorAll('#view-updates h2, #view-updates h3')].map(h => h.textContent.trim())")
        if page.evaluate("['v21.7'].every(v => CHANGELOG.some(r => r.version === v))"):
            check("the Updates tab lists v21.7", any(h.startswith("v21.7") for h in heads), heads[:4])
        else:
            print("SKIP (entry no longer in the public Updates list): " + 'the Updates tab lists v21.7')
        check("CNAME, if there, says minifolio.app (it belonged to the old GitHub Pages address; hosting moved to Cloudflare)", not os.path.exists(os.path.join(ROOT, "CNAME")) or read("CNAME").strip() == "minifolio.app")
        check("ocr folder kept", os.path.isfile(os.path.join(ROOT, "ocr", "ocr-worker.js")) and os.path.isfile(os.path.join(ROOT, "ocr", "eng.traineddata")))
        check("LICENSE-paint-list.txt kept", os.path.isfile(os.path.join(ROOT, "LICENSE-paint-list.txt")))
        wf = read(".github/workflows/zap-scan.yml")
        check("ZAP workflow is still the passive baseline scan", "zaproxy/action-baseline" in wf and "action-full-scan" not in wf)
        csp_tag = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', index)
        check("CSP is exactly v21.4's", csp_tag and " ".join(csp_tag.group(1).split()) == V21_4_CSP, csp_tag and csp_tag.group(1))
        check("DATA_VERSION is still 1", page.evaluate("DATA_VERSION") == 1)
        app = read("app.js")
        for key in ['STORAGE_KEY = "mini-tracker-models"', 'SETTINGS_KEY = "shades-of-grey-settings"', 'RECIPES_KEY = "shades-of-grey-recipes"']:
            check(f"storage name kept: {key}", key in app)
        check("index.html has no code in it", re.findall(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", index) == [] and not re.search(r"\son[a-z]+=", index))

        # ---------- 2. The source ----------
        print("\n--- 2. The source ---")
        code = "\n".join(re.sub(r"\s//.*$", "", l) for l in app.splitlines() if not l.strip().startswith("//"))
        for word in ["alert", "confirm", "prompt"]:
            check(f"no {word}( left in app.js", re.search(r"(?<![A-Za-z_.])" + word + r"\(", code) is None)
            check(f"no window.{word} either", f"window.{word}" not in app)
        check("the box asks through askYesNo / askText / showTextToCopy",
              len(re.findall(r"(?<![A-Za-z_.])askYesNo\(", code)) >= 16 and len(re.findall(r"(?<![A-Za-z_.])askText\(", code)) >= 4
              and "showTextToCopy(" in code)
        check("backTarget() puts the box at the very top",
              re.search(r"function backTarget\(\) \{\s*if \(dialogState\) return cancelDialog;", code) is not None)
        dlg = page.evaluate("""() => { const d = document.getElementById('dialog');
            const label = document.getElementById(d.getAttribute('aria-labelledby'));
            return { role: d.getAttribute('role'), modal: d.getAttribute('aria-modal'), label: !!label,
                     inputLabel: !!document.getElementById(document.getElementById('dialog-input').getAttribute('aria-labelledby')) }; }""")
        check("the box has role=dialog, aria-modal and a label", dlg["role"] == "dialog" and dlg["modal"] == "true" and dlg["label"], dlg)
        check("the type-a-name box is labelled by the question", dlg["inputLabel"], dlg)
        check("the box starts hidden", not box_open(page))

        # ---------- 3. The box itself ----------
        print("\n--- 3. The box itself ---")
        tab(page, "settings")
        ask = """([text, danger]) => { window.__r = []; askYesNo(text, () => window.__r.push('yes'), { onNo: () => window.__r.push('no'), danger }); }"""
        res = lambda: page.evaluate("() => window.__r")
        page.focus("#delete-all")
        page.evaluate(ask, ["Sure?", False])
        page.wait_for_timeout(100)
        check("a question opens the box with its words", asks(page, "Sure?") and box_kind(page) == "yesno")
        check("the buttons say Yes and No", page.inner_text("#dialog-yes") == "Yes" and page.inner_text("#dialog-no") == "No")
        check("focus moves into the box", page.evaluate("() => document.getElementById('dialog').contains(document.activeElement)"))
        sizes = page.evaluate("""() => ['dialog-yes', 'dialog-no'].map(id => { const r = document.getElementById(id).getBoundingClientRect(); return [r.width, r.height]; })""")
        check("both buttons are at least 44 px tall (and wide)", all(h >= 43.9 and w >= 43.9 for w, h in sizes), sizes)
        stayed = True
        for _ in range(6):
            page.keyboard.press("Tab")
            stayed = stayed and page.evaluate("() => document.getElementById('dialog').contains(document.activeElement)")
        check("Tab stays inside the box", stayed)
        stayed = True
        for _ in range(3):
            page.keyboard.press("Shift+Tab")
            stayed = stayed and page.evaluate("() => document.getElementById('dialog').contains(document.activeElement)")
        check("Shift+Tab stays inside the box too", stayed)
        page.click("#dialog-yes")
        page.wait_for_timeout(100)
        check("tapping Yes carries on with the yes answer, and closes the box", res() == ["yes"] and not box_open(page), res())
        check("focus goes back to what was pressed", page.evaluate("() => document.activeElement.id") == "delete-all")

        page.focus("#delete-all")
        page.evaluate(ask, ["Sure?", False]); page.wait_for_timeout(100)
        page.click("#dialog-no"); page.wait_for_timeout(100)
        check("tapping No carries on with the no answer", res() == ["no"] and not box_open(page), res())
        check("…and focus goes back", page.evaluate("() => document.activeElement.id") == "delete-all")

        page.evaluate(ask, ["Sure?", False]); page.wait_for_timeout(100)
        page.keyboard.press("Escape"); page.wait_for_timeout(100)
        check("Escape means No", res() == ["no"] and not box_open(page), res())
        page.evaluate(ask, ["Sure?", False]); page.wait_for_timeout(100)
        page.keyboard.press("Enter"); page.wait_for_timeout(100)
        check("Enter means Yes (focus starts on the Yes button)", res() == ["yes"] and not box_open(page), res())
        page.evaluate(ask, ["Sure?", True]); page.wait_for_timeout(100)
        page.keyboard.press("Tab"); page.keyboard.press("Tab")
        page.keyboard.press("Escape"); page.wait_for_timeout(100)
        check("a danger question works the same (Escape = No)", res() == ["no"] and not box_open(page), res())
        page.evaluate("""() => { window.__r = []; askYesNo('First?', () => window.__r.push('first yes'), { onNo: () => window.__r.push('first no') });
                                   askYesNo('Second?', () => window.__r.push('second yes'), { onNo: () => window.__r.push('second no') }); }""")
        page.wait_for_timeout(100)
        check("a second question replaces the first, which counts as No", box_text(page) == "Second?" and res() == ["first no"], (box_text(page), res()))
        yes(page)
        check("…and then the second one is answered on its own", res() == ["first no", "second yes"] and not box_open(page), res())

        # "type a name" boxes
        text_ask = """([text, start]) => { window.__t = 'unanswered'; askText(text, start, v => { window.__t = v; }); }"""
        typed = lambda: page.evaluate("() => window.__t")
        page.evaluate(text_ask, ["Name of the new part:", "Hull"]); page.wait_for_timeout(100)
        check("a 'type a name' question shows a text box with its start text",
              asks(page, "Name of the new part:") and box_kind(page) == "text" and page.input_value("#dialog-input") == "Hull")
        check("…with OK and Cancel buttons", page.inner_text("#dialog-yes") == "OK" and page.inner_text("#dialog-no") == "Cancel")
        check("…and focus is in the text box", page.evaluate("() => document.activeElement.id") == "dialog-input")
        page.fill("#dialog-input", "Shoulder pads")
        yes(page)
        check("OK hands back what was typed", typed() == "Shoulder pads" and not box_open(page), typed())
        page.evaluate(text_ask, ["Name?", ""]); page.wait_for_timeout(100)
        page.fill("#dialog-input", "Nope")
        no(page)
        check("Cancel hands back nothing (null)", typed() is None and not box_open(page), typed())
        page.evaluate(text_ask, ["Name?", ""]); page.wait_for_timeout(100)
        page.fill("#dialog-input", "Nope")
        page.keyboard.press("Escape"); page.wait_for_timeout(100)
        check("Escape in the text box means Cancel", typed() is None and not box_open(page), typed())
        page.evaluate(text_ask, ["Name?", ""]); page.wait_for_timeout(100)
        page.fill("#dialog-input", "Enter works")
        page.keyboard.press("Enter"); page.wait_for_timeout(100)
        check("Enter in the text box means OK", typed() == "Enter works" and not box_open(page), typed())
        page.evaluate(text_ask, ["Name?", "Old"]); page.wait_for_timeout(100)
        page.evaluate("() => { document.getElementById('dialog-input').value = 'left over'; }")
        no(page)
        page.evaluate(text_ask, ["Name?", ""]); page.wait_for_timeout(100)
        check("the text box starts empty next time (nothing left over)", page.input_value("#dialog-input") == "")
        no(page)

        # The phone's Back button, with a real question from the app.
        tab(page, "settings")
        page.click("#delete-all")
        page.wait_for_timeout(250)
        check("Delete all opens the box", box_open(page))
        page.go_back()
        page.wait_for_timeout(300)
        check("the phone's Back button closes the box as No", not box_open(page) and len(saved_units(page)) == 3 and page.url == URL, (box_open(page), page.url))
        check("…and the app is still there (Back didn't leave it)", page.evaluate("() => settings.tab") == "settings")
        page.click("#delete-all")
        page.wait_for_timeout(250)
        page.evaluate("() => { window.__backTarget = backTarget() === cancelDialog; }")
        check("while the box is open, Back's target is the box", page.evaluate("() => window.__backTarget"))
        page.keyboard.press("Escape"); page.wait_for_timeout(250)
        check("Escape closed it; Back goes on to the Dashboard next, not into the box",
              page.evaluate("() => backTarget() !== cancelDialog"))

        # The copy box
        page.evaluate("""() => { navigator.clipboard.writeText = () => Promise.reject(new Error('no')); document.execCommand = () => false;
                                 copyText('Armour: Macragge Blue', 'Recipe'); }""")
        page.wait_for_timeout(300)
        check("if copying isn't allowed, a box shows the text to copy by hand",
              asks(page, "Copy this text:") and box_kind(page) == "show" and page.input_value("#dialog-area") == "Armour: Macragge Blue")
        check("…with a single Close button", page.is_hidden("#dialog-no") and page.inner_text("#dialog-yes") == "Close")
        yes(page)
        check("Close closes it", not box_open(page))

        # ---------- 4. Every question ----------
        print("\n--- 4. Every question: same words, No changes nothing, Yes does the job ---")

        # 4.1 Delete a unit
        start(page); tab(page, "units")
        page.evaluate("() => deleteModel(2)"); page.wait_for_timeout(100)
        check("delete unit: asks the same thing", asks(page, 'Delete "Termagants"?'), box_text(page))
        no(page)
        check("…No keeps the unit and shows no message", len(saved_units(page)) == 3 and not toast(page)["shown"])
        page.evaluate("() => deleteModel(2)"); page.wait_for_timeout(100)
        yes(page)
        t = toast(page)
        check("…Yes deletes it, with a message and Undo", [u["id"] for u in saved_units(page)] == [1, 3] and t["undo"] and t["text"].startswith("Deleted Termagants"), t)

        # 4.2 Batch painting
        start(page); tab(page, "units")
        page.evaluate("() => setEach(models.find(m => m.id === 3), false)"); page.wait_for_timeout(100)
        check("track each model off: asks the same thing",
              asks(page, "Go back to painting Boyz as a batch? All its models will be set to Part assembled, the stage of the furthest-behind model."), box_text(page))
        no(page)
        boyz = [u for u in saved_units(page) if u["id"] == 3][0]
        check("…No keeps each model's own stage", page.evaluate("() => models.find(m => m.id === 3).each") is True and page.evaluate("() => models.find(m => m.id === 3).stages") == [1, 3])
        page.evaluate("() => setEach(models.find(m => m.id === 3), false)"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes goes back to a batch at the furthest-behind stage",
              page.evaluate("() => models.find(m => m.id === 3).each") is None and page.evaluate("() => models.find(m => m.id === 3).stage") == 1)

        # 4.3 Discard a recipe being written (Cancel, then Back)
        start(page); tab(page, "recipes")
        page.evaluate("() => startNewRecipe(null)"); page.wait_for_timeout(100)
        page.locator("#recipe-page input").first.fill("Half-written"); page.wait_for_timeout(100)
        page.locator("#recipe-page button", has_text="Cancel").click(); page.wait_for_timeout(150)
        check("Cancel on a changed recipe: asks the same thing", asks(page, "Discard the changes to the recipe you're writing?"), box_text(page))
        no(page)
        check("…No keeps the recipe being written", page.evaluate("() => !!recipeDraft && recipeDraft.name") == "Half-written")
        page.locator("#recipe-page button", has_text="Cancel").click(); page.wait_for_timeout(150)
        yes(page)
        check("…Yes closes it", page.evaluate("() => recipeDraft") is None)
        page.evaluate("() => startNewRecipe(null)"); page.wait_for_timeout(100)
        page.locator("#recipe-page input").first.fill("Half-written"); page.wait_for_timeout(100)
        page.go_back(); page.wait_for_timeout(300)
        check("Back on a changed recipe asks the same thing", asks(page, "Discard the changes to the recipe you're writing?"), box_text(page))
        page.go_back(); page.wait_for_timeout(300)
        check("…and Back again answers No: the recipe stays open", not box_open(page) and page.evaluate("() => !!recipeDraft"))
        page.evaluate("() => { recipeDraft = null; renderRecipes(); }")
        page.evaluate("() => startNewRecipe(null)"); page.wait_for_timeout(100)
        page.evaluate("() => openRecipe(1)"); page.wait_for_timeout(100)
        check("an unchanged recipe is left without asking", not box_open(page) and page.evaluate("() => recipeDraft") is None)

        # 4.4 Discard changes to a scheme
        start(page); tab(page, "recipes")
        page.evaluate("() => startScheme(null)"); page.wait_for_timeout(100)
        page.locator("#scheme-page input").first.fill("New scheme"); page.wait_for_timeout(100)
        page.locator("#scheme-page .link-button").first.click(); page.wait_for_timeout(150)
        check("scheme editor ← Schemes: asks the same thing", asks(page, "Discard the changes to this scheme?"), box_text(page))
        no(page)
        check("…No keeps the scheme being edited", page.evaluate("() => !!schemeDraft"))
        page.locator("#scheme-page .link-button").first.click(); page.wait_for_timeout(150)
        yes(page)
        check("…Yes closes it", page.evaluate("() => schemeDraft") is None)

        # 4.5 Delete a scheme
        start(page); tab(page, "recipes")
        page.evaluate("() => deleteScheme(1)"); page.wait_for_timeout(100)
        check("delete scheme: asks the same thing",
              asks(page, 'Delete the scheme "My Ultramarines"? Its recipes, and the units they\'re linked to, stay as they are.'), box_text(page))
        no(page)
        check("…No keeps it", len(saved_book(page)["schemes"]) == 1)
        page.evaluate("() => deleteScheme(1)"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes deletes it, with Undo", len(saved_book(page)["schemes"]) == 0 and toast(page)["undo"] and toast(page)["text"] == "Deleted My Ultramarines", toast(page))
        page.click("#toast-undo"); page.wait_for_timeout(150)
        check("…and Undo brings it back", len(saved_book(page)["schemes"]) == 1)

        # 4.6 Delete a recipe
        start(page); tab(page, "recipes")
        page.evaluate("() => deleteRecipe(1)"); page.wait_for_timeout(100)
        check("delete recipe: asks the same thing", asks(page, re.compile(r'^Delete the recipe "Armour"\? It will be removed from 1 scheme\.$')), box_text(page))
        no(page)
        check("…No keeps it", len(saved_book(page)["recipes"]) == 1 and not toast(page)["shown"])
        page.evaluate("() => deleteRecipe(1)"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes deletes it, with Undo", len(saved_book(page)["recipes"]) == 0 and toast(page)["text"] == "Deleted Armour" and toast(page)["undo"], toast(page))

        # 4.7 Remove a step
        start(page); tab(page, "recipes")
        page.evaluate("() => openRecipe(1)"); page.wait_for_timeout(100)
        page.locator("#recipe-page button", has_text="Edit").first.click(); page.wait_for_timeout(150)
        page.locator("#recipe-page li.step-edit .step-line").first.click()   # v50: a step is one line until you open it
        page.click('button[aria-label="Remove step 1"]'); page.wait_for_timeout(150)
        check("remove step: asks the same thing", asks(page, "Remove step 1?"), box_text(page))
        no(page)
        check("…No keeps both steps", page.evaluate("() => recipeDraft.steps.length") == 2)
        page.click('button[aria-label="Remove step 1"]'); page.wait_for_timeout(150)
        yes(page)
        check("…Yes removes it", page.evaluate("() => recipeDraft.steps.length") == 1)

        # 4.8 Leave Paste recipes
        start(page); tab(page, "recipes")
        page.evaluate("() => startImport()"); page.wait_for_timeout(100)
        page.fill("#import-text", "Test scheme\n\nArmour:\nLeadbelcher"); page.wait_for_timeout(100)
        page.locator("#import-page .link-button").first.click(); page.wait_for_timeout(150)
        check("leave Paste recipes: asks the same thing", asks(page, "Leave without saving these recipes?"), box_text(page))
        no(page)
        check("…No keeps the paste open with its text", page.evaluate("() => !!importDraft") and page.input_value("#import-text").startswith("Test scheme"))
        page.locator("#import-page .link-button").first.click(); page.wait_for_timeout(150)
        yes(page)
        check("…Yes closes it", page.evaluate("() => importDraft") is None)

        # 4.9 Merge two paints
        start(page); tab(page, "recipes")
        page.evaluate("() => { book.paints.find(p => p.id === 2).brand = 'Citadel'; editPaint(book.paints.find(p => p.id === 2), 'name', 'Macragge Blue'); }")
        page.wait_for_timeout(100)
        check("rename into a twin: asks the same thing", asks(page, "You already have Citadel Macragge Blue. Merge the two into one paint?"), box_text(page))
        no(page)
        check("…No leaves both paints, the first one as it was",
              page.evaluate("() => book.paints.filter(p => p.id === 1 || p.id === 2).map(p => p.name)") == ["Macragge Blue", "Macrage Blue"])
        page.evaluate("() => editPaint(book.paints.find(p => p.id === 2), 'name', 'Macragge Blue')"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes merges them into one", page.evaluate("() => book.paints.some(p => p.id === 2)") is False and toast(page)["text"] == "Merged into Macragge Blue", toast(page))
        check("…and the recipe now uses the kept paint", saved_book(page)["recipes"][0]["steps"][0]["paints"][0]["paint"] == 1)

        # 4.10 Remove a stage that has units in it
        start(page); tab(page, "settings")
        page.evaluate("() => { startDraft(); draft.splice(4, 1); renderStageEditor(); }")
        page.click("#save-stages"); page.wait_for_timeout(150)
        check("removing a used stage: asks the same thing",
              asks(page, "1 unit(s) are in a stage you've removed. They'll move to the nearest earlier stage. Continue?"), box_text(page))
        no(page)
        check("…No changes nothing", page.evaluate("() => STAGES.length") == 8 and page.evaluate("() => models.find(m => m.id === 2).stage") == 4)
        page.click("#save-stages"); page.wait_for_timeout(150)
        yes(page)
        check("…Yes saves the stages and moves the unit to the earlier one",
              page.evaluate("() => STAGES.length") == 7 and page.evaluate("() => models.find(m => m.id === 2).stage") == 3 and toast(page)["text"] == "Stages saved", toast(page))

        # 4.11 Recover recipes (recipes-only copy)
        start(page); tab(page, "settings")
        page.evaluate("() => { keepRecipesCopy(); book.recipes = []; save(); recoverRecipesCopy(); }"); page.wait_for_timeout(100)
        check("recover recipes: asks the same thing",
              asks(page, "Replace your current 0 recipes with the 1 recipe in this copy? (Your units stay as they are.)"), box_text(page))
        no(page)
        check("…No leaves your recipes as they are", page.evaluate("() => book.recipes.length") == 0)
        page.evaluate("() => recoverRecipesCopy()"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes puts the copy back, with Undo", page.evaluate("() => book.recipes.length") == 1 and toast(page)["text"] == "Recovered 1 recipe" and toast(page)["undo"], toast(page))

        # 4.12 Recover units (safety copy)
        start(page); tab(page, "settings")
        page.evaluate("() => { keepSafetyCopy('-before-delete-all'); models = models.slice(0, 1); save(); recoverSafetyCopy('-before-delete-all'); }"); page.wait_for_timeout(100)
        check("recover units: asks the same thing",
              asks(page, re.compile(r"^Replace your current 1 unit with the 3 units in this copy( \(and its recipes\))?\?$")), box_text(page))
        no(page)
        check("…No leaves your units as they are", page.evaluate("() => models.length") == 1)
        page.evaluate("() => recoverSafetyCopy('-before-delete-all')"); page.wait_for_timeout(100)
        yes(page)
        check("…Yes puts the copy back, with Undo", page.evaluate("() => models.length") == 3 and toast(page)["text"] == "Recovered 3 units" and toast(page)["undo"], toast(page))

        # 4.13 Clean up photo storage
        start(page); tab(page, "settings")
        page.evaluate("""async () => { await photoStore('readwrite', s => s.put({ id: 'orphan-1', full: new Blob(['x']), thumb: new Blob(['y']) }));
                                         await renderPhotoSummary(); }""")
        page.wait_for_timeout(200)
        page.click("#clean-photos"); page.wait_for_timeout(250)
        check("clean up photos: asks the same thing", asks(page, re.compile(r"^Delete 1 photo file that no unit uses\? This frees about \d+ KB\.$")), box_text(page))
        no(page)
        check("…No keeps the file", page.evaluate("async () => (await photoStoreReport()).orphans.length") == 1)
        page.click("#clean-photos"); page.wait_for_timeout(250)
        yes(page)
        page.wait_for_timeout(300)
        check("…Yes removes it", page.evaluate("async () => (await photoStoreReport()).orphans.length") == 0 and toast(page)["text"].startswith("Cleaned up: 1 photo file removed"), toast(page))

        # 4.14 Delete all units (with Escape, then Yes)
        start(page); tab(page, "settings")
        days = page.evaluate("() => SAFETY_DAYS")
        page.click("#delete-all"); page.wait_for_timeout(150)
        check("delete all: asks the same thing",
              asks(page, f"Delete all 3 units? A copy is kept on this device for {days} days (Settings → Recover earlier data), but please save a backup first."), box_text(page))
        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        check("…Escape (No) deletes nothing", len(saved_units(page)) == 3 and not toast(page)["shown"] and page.evaluate("() => document.activeElement.id") == "delete-all")
        page.click("#delete-all"); page.wait_for_timeout(150)
        yes(page)
        check("…Yes deletes them, keeps a copy, offers Undo", saved_units(page) == [] and toast(page)["text"] == "Deleted 3 units" and toast(page)["undo"]
              and page.evaluate("() => readSafetyCopy('-before-delete-all').models.length") == 3, toast(page))

        # 4.15 Restore a backup
        start(page); tab(page, "settings")
        backup = [{"id": 9, "name": "Hormagaunts", "hobby": "40K", "faction": "Tyranids", "stage": 0, "count": 10}]
        page.set_input_files("#restore-file", files=[{"name": "one.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_timeout(400)
        check("restore backup: asks the same thing", asks(page, "Replace your current 3 units with 1 from the backup? (Your recipes stay as they are.)"), box_text(page))
        no(page)
        check("…No changes nothing", len(saved_units(page)) == 3)
        page.set_input_files("#restore-file", files=[{"name": "two.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()}])
        page.wait_for_timeout(400)
        yes(page)
        page.wait_for_timeout(400)
        check("…Yes restores it", [u["name"] for u in saved_units(page)] == ["Hormagaunts"] and toast(page)["text"] == "Backup restored", toast(page))

        # 4.16 Replace everything from an import
        start(page); tab(page, "settings")
        page.set_input_files("#csv-file", files=[{"name": "one.csv", "mimeType": "text/csv", "buffer": b"name,faction\nWarboss,Orks\n"}])
        page.wait_for_timeout(400)
        page.click('.mode-button[data-mode="replace"]'); page.wait_for_timeout(100)
        page.click("#review-go"); page.wait_for_timeout(200)
        check("replace from an import: asks the same thing", asks(page, "Remove your 3 units and replace them with 1 unit?"), box_text(page))
        no(page)
        check("…No changes nothing", len(saved_units(page)) == 3)
        page.click("#review-go"); page.wait_for_timeout(200)
        yes(page)
        check("…Yes replaces them, with Undo", [u["name"] for u in saved_units(page)] == ["Warboss"] and toast(page)["undo"], toast(page))

        # 4.17 Rename a faction (type a name)
        start(page); tab(page, "settings")
        page.locator('button[aria-label="Rename Ultramarines"]').click(); page.wait_for_timeout(150)
        check("rename faction: asks the same thing, with the old name in the box",
              asks(page, 'Rename "Ultramarines" on all 1 unit to:') and box_kind(page) == "text" and page.input_value("#dialog-input") == "Ultramarines", box_text(page))
        page.fill("#dialog-input", "Changed"); no(page)
        check("…Cancel changes nothing", saved_units(page)[0]["faction"] == "Ultramarines")
        page.locator('button[aria-label="Rename Ultramarines"]').click(); page.wait_for_timeout(150)
        page.fill("#dialog-input", "Ultramarine Guard"); yes(page)
        check("…OK renames it on the unit", saved_units(page)[0]["faction"] == "Ultramarine Guard", saved_units(page)[0])

        # 4.18 Add a part to the list (type a name)
        start(page); tab(page, "recipes")
        page.evaluate("() => { settings.recipeView = 'recipes'; renderRecipes(); }"); page.wait_for_timeout(100)
        page.locator("#recipe-lists summary").click(); page.wait_for_timeout(100)
        page.locator('#part-chips button', has_text="+ Add part").click(); page.wait_for_timeout(150)
        check("+ Add part: asks the same thing", asks(page, "Name of the new part:") and box_kind(page) == "text", box_text(page))
        page.fill("#dialog-input", "Ignored"); no(page)
        check("…Cancel adds nothing", saved_book(page).get("parts") == ["Armour", "Trim"] or page.evaluate("() => book.parts") == ["Armour", "Trim"])
        page.locator('#part-chips button', has_text="+ Add part").click(); page.wait_for_timeout(150)
        page.fill("#dialog-input", "Shoulder pads"); yes(page)
        check("…OK adds it", "Shoulder pads" in page.evaluate("() => book.parts"), page.evaluate("() => book.parts"))
        page.locator('#technique-chips button', has_text="+ Add technique").click(); page.wait_for_timeout(150)
        check("+ Add technique: asks the same thing", asks(page, "Name of the new technique:"), box_text(page))
        no(page)

        # 4.19 "＋ Add a new technique…" in the recipe editor (type a name)
        start(page); tab(page, "recipes")
        page.evaluate("() => startNewRecipe(null)"); page.wait_for_timeout(150)
        page.locator("#recipe-page .step-edit .more-info-button").first.click()   # v50: the technique is under More options
        sel = page.locator("#recipe-page .step-edit select").first
        sel.select_option(value="\u0000new"); page.wait_for_timeout(150)
        check("recipe editor ＋ Add a new technique…: asks the same thing", asks(page, "Name of the new technique:") and box_kind(page) == "text", box_text(page))
        page.fill("#dialog-input", "Zenithal"); no(page)
        check("…Cancel adds nothing and the menu goes back",
              "Zenithal" not in page.evaluate("() => book.techniques") and page.evaluate("() => !!recipeDraft")
              and page.locator("#recipe-page .step-edit select").first.input_value() != "\u0000new")
        page.locator("#recipe-page .step-edit select").first.select_option(value="\u0000new"); page.wait_for_timeout(150)
        page.fill("#dialog-input", "Zenithal"); yes(page)
        check("…OK adds it to the list and picks it for the step",
              "Zenithal" in page.evaluate("() => book.techniques") and page.evaluate("() => recipeDraft.steps[0].technique") == "Zenithal")

        # 4.20 "Other…" on a paint the paste reader wasn't sure of (type a name)
        start(page); tab(page, "recipes")
        page.evaluate("() => startImport()"); page.wait_for_timeout(100)
        page.fill("#import-text", "Test scheme\n\nArmour:\nIvory")
        page.click("text=Read notes"); page.wait_for_timeout(300)
        other = page.locator("#import-page .import-ask .chip, #import-page .import-ask button", has_text="Other…")
        if other.count():
            other.first.click(); page.wait_for_timeout(150)
            check("paste check Other…: asks the same thing (with the name it didn't know)",
                  asks(page, re.compile(r"^What is “.+”\? Type the paint's name:$")) and box_kind(page) == "text", box_text(page))
            page.fill("#dialog-input", "Macragge Blue"); no(page)
            check("…Cancel leaves the paint unanswered", page.locator("#import-page .import-ask button", has_text="Other: ").count() == 0)
            page.locator("#import-page .import-ask button", has_text="Other…").first.click(); page.wait_for_timeout(150)
            page.fill("#dialog-input", "Macragge Blue"); yes(page)
            check("…OK picks that paint", page.locator("#import-page .import-ask button", has_text="Other: Macragge Blue").count() == 1)
        else:
            check("paste check Other…: the note produced a paint to check", False, page.inner_text("#import-page")[:200])

        # ---------- 5. Screenshots, colours, widths ----------
        print("\n--- 5. Screenshots, colours and widths ---")
        long_name = "Hormagaunts_with_a_very_long_unbroken_nickname_" * 3
        for appearance in ["dark", "light"]:
            for width in [390, 360]:
                page.set_viewport_size({"width": width, "height": 800})
                start(page, settings=full_settings(appearance=appearance, tab="settings"))
                for kind in ["yesno", "text"]:
                    if kind == "yesno":
                        page.evaluate("t => askYesNo('Delete \"' + t + '\"?', () => {}, { danger: true })", long_name)
                    else:
                        page.evaluate("t => askText('Rename \"' + t + '\" on all 3 units to:', t, () => {})", long_name)
                    page.wait_for_timeout(200)
                    label = f"{kind} {appearance} {width}px"
                    box = page.evaluate("""() => { const r = document.getElementById('dialog').getBoundingClientRect();
                        const m = document.getElementById('dialog-message');
                        return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: window.innerWidth, h: window.innerHeight,
                                 wraps: m.scrollWidth <= m.clientWidth + 1 }; }""")
                    check(f"{label}: the box sits inside the screen", box["left"] >= 0 and box["right"] <= box["w"] and box["top"] >= 0 and box["bottom"] <= box["h"], box)
                    check(f"{label}: the long name wraps, nothing scrolls sideways", box["wraps"] and no_sideways(page), box)
                    btn = page.evaluate("""() => ['dialog-yes', 'dialog-no'].map(id => document.getElementById(id).getBoundingClientRect().height)""")
                    check(f"{label}: buttons are at least 44 px tall", all(h >= 43.9 for h in btn), btn)
                    colours = page.evaluate("""() => { const s = getComputedStyle(document.getElementById('dialog'));
                        const bg = getComputedStyle(document.body).backgroundColor;
                        return { text: s.color, box: s.backgroundColor, page: bg }; }""")
                    check(f"{label}: the words are easy to read on the box (contrast 4.5+)", contrast(rgb(colours["text"]), rgb(colours["box"])) >= 4.5, colours)
                    shot(page, f"v21-7-box-{kind}-{appearance}-{width}.png")
                    page.keyboard.press("Escape"); page.wait_for_timeout(100)
        context.close()
        browser.close()

    check("no browser pop-up (alert, confirm or prompt) at any point", not native, native[:3])
    check("no page errors", not errors, errors[:3])
    check("no CSP errors", not csp, csp[:3])
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
