"""Test (v18 Finish): version numbers, the Updates entry, the Help text, and "and" between paints.

1. Version: APP_VERSION and sw.js VERSION are both v18, and the title shows v18.
2. Updates tab: the newest entry is v18, dated, and mentions the big changes.
3. Help: a "Pasting recipes from your notes" topic covering mixes copied as ratios, dividers
   and emoji, the 20,000 character limit, "Do you own these?", ✕ and ✎. Your Palette's Remove
   and Merge into…, and that "Saved" only shows when it really saved.
4. Known answers for "and": "Ushabti Bone and Wraithbone" is both paints (before v18 Finish,
   Wraithbone ended up in the note). Only split when every piece is a paint the app is sure of.
5. The preview shows both paints and saves them. Help reads fine on a 360px phone.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
HERE = os.path.dirname(os.path.abspath(__file__))
RECIPES_KEY = "shades-of-grey-recipes"

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# Same summary as test_v18_paste.py: each step's technique, paint names, ratio and note.
SUMMARY_JS = """text => parseRecipeText(text).schemes.flatMap(s => s.parts).map(p => ({
  name: p.name,
  notes: p.notes.slice(),
  steps: p.steps.map(st => ({
    technique: st.technique || "",
    paints: st.paints.map(m => m.paint ? m.paint.name : m.typed),
    ratio: st.ratio || "",
    note: st.note || "",
  })),
}))"""

# "and" known answers. steps: what each step should have (only the keys listed are checked).
AND_CASES = [
    {"name": "'Ushabti Bone and Wraithbone' is both paints, in one step",
     "text": "Teeth:\nUshabti Bone and Wraithbone",
     "steps": [{"paints": ["Ushabti Bone", "Wraithbone"], "note": ""}]},
    {"name": "'and' inside a list of steps split by commas",
     "text": "Teeth:\nUshabti Bone and Wraithbone, Agrax Earthshade",
     "steps": [{"paints": ["Ushabti Bone", "Wraithbone"]}, {"paints": ["Agrax Earthshade"]}]},
    {"name": "'Wraithbone and Agrax' (a base then a wash) is two steps, like '+'",
     "text": "Teeth:\nWraithbone and Agrax",
     "steps": [{"paints": ["Wraithbone"]}, {"paints": ["Agrax Earthshade"]}]},
    {"name": "'Abaddon Black and Leadbelcher drybrush': two paints, the dry brush on Leadbelcher",
     "text": "Gun:\nAbaddon Black and Leadbelcher drybrush",
     "steps": [{"paints": ["Abaddon Black"]}, {"paints": ["Leadbelcher"], "technique": "Dry brush"}]},
    {"name": "'Ushabti Bone and a bit of white' stays one paint with a note",
     "text": "Teeth:\nUshabti Bone and a bit of white",
     "steps": [{"paints": ["Ushabti Bone"], "note": "and a bit of white"}]},
    {"name": "'Mephiston Red and then Agrax' is two steps (no paint called 'Then Agrax')",
     "text": "Cloak:\nMephiston Red and then Agrax",
     "steps": [{"paints": ["Mephiston Red"]}, {"paints": ["Agrax Earthshade"]}]},
    {"name": "a ratio with 'and' still works: 2:1 Kantor Blue and White",
     "text": "Armour:\n2:1 Kantor Blue and White",
     "steps": [{"paints": ["Kantor Blue", "White"], "ratio": "2:1"}]},
    {"name": "'Sand' is not split on the 'and' inside it",
     "text": "Base:\nTexture Sand",
     "steps": [{"paints": ["Sand"], "technique": "Texture"}]},
    {"name": "the part heading 'Blue and red:' is left alone",
     "text": "Blue and red:\nKantor Blue",
     "parts": ["Blue and red"],
     "steps": [{"paints": ["Kantor Blue"]}]},
]

def start(page):
    page.goto(f"{BASE}/manifest.json")
    page.evaluate("() => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]'); }")
    page.goto(f"{BASE}/index.html")
    page.wait_for_timeout(300)

def compare(case, parts):
    problems = []
    if "parts" in case and [p["name"] for p in parts] != case["parts"]:
        problems.append(f"parts {[p['name'] for p in parts]}, want {case['parts']}")
    steps = [st for p in parts for st in p["steps"]]
    want = case["steps"]
    if len(steps) != len(want):
        return problems + [f"{len(steps)} steps {[s['paints'] for s in steps]}, want {len(want)}"]
    for i, (got, w) in enumerate(zip(steps, want), 1):
        for k, v in w.items():
            if got[k] != v:
                problems.append(f"step {i} {k} is {got[k]!r}, want {v!r}")
    return problems

def help_text(page):
    page.click("nav button[data-tab='help']")
    page.wait_for_timeout(150)
    # Closed topics' text isn't visible, so open them all before reading.
    page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
    return page.inner_text("#view-help")

def main():
    sw = open(os.path.join(HERE, "..", "sw.js"), encoding="utf-8").read()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        start(page)

        print("--- Version numbers ---")
        check("APP_VERSION is v18", page.evaluate("APP_VERSION") == "v18", page.evaluate("APP_VERSION"))
        m = re.search(r'const VERSION = "([^"]+)"', sw)
        check("sw.js VERSION is v18 (so phones fetch the new copy)", m and m.group(1) == "v18", m and m.group(1))
        check("the version next to the title shows v18", page.inner_text("#version-tag").strip() == "v18",
              page.inner_text("#version-tag"))

        print("\n--- Updates tab ---")
        first = page.evaluate("CHANGELOG[0]")
        check("newest Updates entry is v18, dated 10 Oct 2026",
              first["version"] == "v18" and first["date"] == "10 Oct 2026", first["version"] + " " + first["date"])
        text = " ".join(first["changes"])
        for word in ["Paste recipes", "✕", "✎", "Do you own these?", "Remove", "Merge into…", "1:1",
                     "Saved", "20,000", "Ushabti Bone and Wraithbone", "Help"]:
            check(f"v18 entry mentions {word!r}", word in text)
        check("v17.1 is still listed, below v18", page.evaluate("CHANGELOG[1].version") == "v17.1")
        page.click("nav button[data-tab='updates']")
        page.wait_for_timeout(150)
        check("Updates tab shows the v18 entry first",
              page.inner_text("#changelog .release h3 >> nth=0").startswith("v18"),
              page.inner_text("#changelog .release h3 >> nth=0"))

        print("\n--- Help ---")
        body = help_text(page)
        summaries = page.eval_on_selector_all("#view-help summary", "els => els.map(e => e.textContent.trim())")
        check("Help has a 'Pasting recipes from your notes' topic, after 'Paint recipes'",
              "Pasting recipes from your notes" in summaries
              and summaries.index("Pasting recipes from your notes") == summaries.index("Paint recipes") + 1,
              summaries)
        paste_help = page.inner_text("#help-paste")
        wants = {
            "mixes are copied as ratios (an even mix as 1:1)": ["Copy as text", "ratio", "1:1"],
            "dividers and emoji are ignored": ["Divider", "emoji", "skipped"],
            "the 20,000 character limit": ["20,000 characters"],
            "'Do you own these?' with All / None / Let me pick": ["Do you own these?", "All", "None", "Let me pick"],
            "✕ to leave a step, part or note out": ["✕", "step", "part's name", "note", "Read again"],
            "✎ to change a step's technique, mix ratio or paints": ["✎", "technique", "mix ratio", "Change…", "paints"],
            "'and' between two paints": ["Ushabti Bone and Wraithbone"],
            "nothing is saved until Save": ["nothing is saved until"],
        }
        for what, words in wants.items():
            missing = [w for w in words if w not in paste_help]
            check(f"paste help covers {what}", not missing, f"missing {missing}")
        check("Paint recipes help covers Remove and Merge into… on Your Palette",
              "Remove" in body and "Merge into…" in body and "typo twin" in body)
        check("Paint recipes help covers 'Do you own these?' in the recipe editor",
              "Save recipe" in body and body.count("Do you own these?") >= 2)
        check("data help says 'Saved' only shows when it really saved",
              "only shows when your change really was saved" in body and "Not saved" in body)
        check("every Help topic still opens and closes (no broken markup)",
              page.evaluate("document.querySelectorAll('#view-help details').length") == len(summaries) >= 12,
              len(summaries))

        print("\n--- 'and' between paints: known answers ---")
        for case in AND_CASES:
            try:
                problems = compare(case, page.evaluate(SUMMARY_JS, case["text"]))
            except Exception as e:
                problems = [f"the reader crashed: {str(e).splitlines()[0]}"]
            check(case["name"], not problems, "; ".join(problems))
        # A brand from an earlier line is still only a preference, so "and" still splits.
        branded = page.evaluate(SUMMARY_JS, "Teeth:\nCitadel Ushabti Bone and Wraithbone")
        check("'Citadel Ushabti Bone and Wraithbone' is both paints",
              [s["paints"] for p in branded for s in p["steps"]] == [["Ushabti Bone", "Wraithbone"]], branded)

        print("\n--- Preview and save ---")
        page.evaluate("startImport()")
        page.fill("#import-text", "Bone scheme\n\nTeeth:\nUshabti Bone and Wraithbone\nAgrax Earthshade")
        page.click("#import-page button.primary-button")   # "Read notes"
        page.wait_for_timeout(150)
        lines = page.eval_on_selector_all("#import-page .import-line-body", "els => els.map(e => e.textContent.trim())")
        check("preview: the first step lists Ushabti Bone and Wraithbone",
              lines and "Ushabti Bone" in lines[0] and "Wraithbone" in lines[0], lines)
        check("preview: 'and Wraithbone' isn't shown as a note", not any("and Wraithbone" in l for l in lines), lines)
        save = page.locator("#import-save")
        check("preview: Save is ready", save.count() == 1 and save.is_enabled())
        save.click()
        page.wait_for_timeout(200)
        book = json.loads(page.evaluate(f"localStorage.getItem('{RECIPES_KEY}') || '{{}}'"))
        names = {p["id"]: p["name"] for p in book.get("paints", [])}
        teeth = next((r for r in book.get("recipes", []) if r.get("name") == "Teeth"), None)
        first_step = [names.get(sp.get("paint")) for sp in teeth["steps"][0]["paints"]] if teeth else None
        check("saved: the Teeth recipe's first step has both paints", first_step == ["Ushabti Bone", "Wraithbone"],
              teeth and teeth["steps"][0])
        check("saved: Wraithbone is in Your Palette", "Wraithbone" in names.values(), sorted(names.values()))

        print("\n--- Small phone ---")
        page.set_viewport_size({"width": 360, "height": 740})
        help_text(page)
        page.evaluate("document.querySelectorAll('#view-help details').forEach(d => d.open = true)")
        page.wait_for_timeout(100)
        wide = page.evaluate("document.documentElement.scrollWidth")
        check("360px phone: Help with every topic open has no sideways scrolling", wide <= 360, wide)
        shots = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
        os.makedirs(shots, exist_ok=True)
        page.locator("#help-paste").screenshot(path=os.path.join(shots, "v18_help_paste.png"))

        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
