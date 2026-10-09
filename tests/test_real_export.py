"""Test: a real Warhammer 40K army-list export (tests/real_40k_tyranids.txt) imports as the
Tyranids faction with 17 units and the right model counts (75 models in total).

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_real_export.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, re, sys
from collections import Counter
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
HERE = os.path.dirname(os.path.abspath(__file__))

# What the export contains, counted by hand from the file: name -> model count, in file order.
# Gargoyles and Termagants each appear twice, so they are listed twice.
EXPECTED = [
    ("Deathleaper", 1), ("Hive Tyrant", 1), ("Neurotyrant", 1), ("Tervigon", 1),
    ("Gargoyles", 10), ("Gargoyles", 10), ("Termagants", 20), ("Termagants", 20),
    ("Biovores", 1), ("Exocrine", 1), ("Exocrine", 1), ("Lictor", 1), ("Lictor", 1),
    ("Maleceptor", 1), ("Neurolictor", 1), ("Norn Emissary", 1), ("Von Ryan's Leapers", 3),
]
EXPECTED_UNITS = 17
EXPECTED_MODELS = 75

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def base_name(name):
    # Drops a trailing copy number (for example "Lictor 2") so the names can be compared.
    return re.sub(r"\s+\d+$", "", name).replace("’", "'")

def main():
    export = open(os.path.join(HERE, "real_40k_tyranids.txt"), encoding="utf-8").read()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page_errors = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        # Start from an empty store on the same site, without running the app first.
        page.goto(f"{BASE}/manifest.json")
        # An empty unit list stops the app adding its three first-run example units.
        page.evaluate("() => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]'); }")
        page.goto(f"{BASE}/index.html")
        page.wait_for_timeout(300)
        page.click('nav button[data-tab="settings"]')
        page.click("#wh-button")
        page.fill("#wh-text", export)
        page.click("#wh-read")
        page.click("#review-go")
        page.wait_for_timeout(300)

        units = json.loads(page.evaluate("localStorage.getItem('mini-tracker-models') || '[]'"))
        browser.close()

    check("the app opened the export without page errors", not page_errors, page_errors)
    check(f"imports {EXPECTED_UNITS} units", len(units) == EXPECTED_UNITS, f"got {len(units)}")
    factions = {u.get("faction") for u in units}
    check("every unit is in the Tyranids faction", factions == {"Tyranids"}, f"got {factions}")

    got = sorted((base_name(u["name"]), u["count"]) for u in units)
    want = sorted(EXPECTED)
    check("unit names and model counts match the export", got == want,
          f"missing {list((Counter(want) - Counter(got)).elements())}, extra {list((Counter(got) - Counter(want)).elements())}")
    total = sum(u["count"] for u in units)
    check(f"{EXPECTED_MODELS} models in total", total == EXPECTED_MODELS, f"got {total}")
    check("no points are stored", all("points" not in json.dumps(u).lower() for u in units))

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
