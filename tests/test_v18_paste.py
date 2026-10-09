"""Test (v18a): Paste recipes "known answers".

Each case below is a bit of pasted notes plus what the paste reader SHOULD make of it.
Many of these fail on v17.1 on purpose: they show the bugs from the v17 review, and they
will pass once the v18b fixes land. The rest guard things that already work.

For every case it checks two things:
1. The reader's answer (parts, steps, paints, mix ratios, notes), by calling the app's own
   reader, parseRecipeText(), inside the page.
2. The on-screen preview: Paste recipes -> Read notes must show a preview with a Save
   button and no page error. (v17.1 stops dead on dividers, emoji and accented lines.)

Then it reads tests/keep_note.txt, a real Google Keep note, and checks the main results
and that reading it takes under 200 ms.

Serve the repo folder first (run_all.py does this for you), then run:
python3 tests/test_v18_paste.py
The port comes from the SOG_PORT environment variable, or 8765 if it isn't set."""
import json, os, sys
from playwright.sync_api import sync_playwright

PORT = os.environ.get("SOG_PORT", "8765")
BASE = f"http://localhost:{PORT}"
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------------------
# The known answers.
#   text   : what is pasted
#   parts  : the part names it should find, in order (across all schemes)
#   scheme : the first scheme's name, if it matters
#   steps  : for a part, its steps in order. Each step only lists what matters:
#            "paints" (names, in order), "ratio", "technique", "note".
#   notes  : text that should end up as a note on that part (not a step)
#   not_paints : names that must NOT appear as a paint anywhere
# ---------------------------------------------------------------------------------------
CASES = [
    # --- Mix lines (review section 1, item 1) ---
    {"name": "mix line with a technique: Wet blend 3:1 Kantor Blue:White",
     "text": "Armour:\nWet blend 3:1 Kantor Blue:White\nAgrax Earthshade",
     "parts": ["Armour"],
     "steps": {"Armour": [{"technique": "Wet blend", "paints": ["Kantor Blue", "White"], "ratio": "3:1"},
                          {"paints": ["Agrax Earthshade"]}]}},
    {"name": "mix line with 'with': Seraphim Sepia wash 1:2 with Contrast Medium",
     "text": "Cloak:\nSeraphim Sepia wash 1:2 with Contrast Medium",
     "parts": ["Cloak"],
     "steps": {"Cloak": [{"technique": "Wash", "paints": ["Seraphim Sepia", "Contrast Medium"], "ratio": "1:2"}]}},
    {"name": "mix line as Copy as text writes it: Contrast 1:2 Skeleton Horde:Contrast Medium",
     "text": "Skin:\nContrast 1:2 Skeleton Horde:Contrast Medium",
     "parts": ["Skin"],
     "steps": {"Skin": [{"technique": "Contrast", "paints": ["Skeleton Horde", "Contrast Medium"], "ratio": "1:2"}]}},
    {"name": "mix line, ratio first: 2:1 Frostheart:Contrast Medium (already works)",
     "text": "Gems:\n2:1 Frostheart:Contrast Medium",
     "parts": ["Gems"],
     "steps": {"Gems": [{"paints": ["Frostheart", "Contrast Medium"], "ratio": "2:1"}]}},

    # --- A faction name as the first line (item 5) ---
    *[{"name": f"faction first line: {f}",
       "text": f"{f}\n\nArmour:\nCaliban Green",
       "scheme": f, "parts": ["Armour"],
       "steps": {"Armour": [{"paints": ["Caliban Green"]}]},
       "not_paints": [f"{f} Green", f"{f} Red", f"{f} Blue", f"{f} Grey", f"{f} Plaguebearer Flesh"]}
      for f in ["Dark Angels", "Ultramarines", "Blood Angels", "Space Wolves", "Death Guard"]],

    # --- "Base;" and "Base:" as section headers (review section 2) ---
    {"name": "'Base;' is a section header, not a technique",
     "text": "Cloak:\nMephiston Red\n\nBase;\nStirland Mud\nAgrax Earthshade",
     "parts": ["Cloak", "Base"],
     "steps": {"Cloak": [{"paints": ["Mephiston Red"]}],
               "Base": [{"paints": ["Stirland Mud"]}, {"paints": ["Agrax Earthshade"]}]}},
    {"name": "'Base:' is a section header, not a technique",
     "text": "Base:\nTexture Sand\nAgrax Earthshade",
     "parts": ["Base"],
     # "Texture Sand" is the Texture technique with sand (how Copy as text writes it).
     "steps": {"Base": [{"technique": "Texture", "paints": ["Sand"]}, {"paints": ["Agrax Earthshade"]}]}},

    # --- Words after a paint are a note (review section 2) ---
    {"name": "trailing words: Waywatcher Green to tie it together",
     "text": "Cloak:\nWaywatcher Green to tie it together",
     "parts": ["Cloak"],
     "steps": {"Cloak": [{"paints": ["Waywatcher Green"], "note": "to tie it together"}]}},
    {"name": "trailing words: Nuln Oil to tie it together (already works)",
     "text": "Cloak:\nNuln Oil to tie it together\nSigvald Burgundy in gaps",
     "parts": ["Cloak"],
     "steps": {"Cloak": [{"paints": ["Nuln Oil"], "note": "to tie it together"},
                         {"paints": ["Sigvald Burgundy"], "note": "in gaps"}]}},

    # --- Dividers, emoji, accents (item 9) ---
    *[{"name": f"divider line {d!r} is skipped",
       "text": f"Eyes:\nYriel Yellow\n{d}\nTeeth:\nWraithbone",
       "parts": ["Eyes", "Teeth"],
       "steps": {"Eyes": [{"paints": ["Yriel Yellow"]}], "Teeth": [{"paints": ["Wraithbone"]}]}}
      for d in ["-----", "...", "***", "___", "==="]],
    {"name": "emoji-only line is not a step",
     "text": "Eyes:\nYriel Yellow\n👍",
     "parts": ["Eyes"],
     "steps": {"Eyes": [{"paints": ["Yriel Yellow"]}]}},
    {"name": "accented header keeps its accents",
     "text": "Écailles:\nRhinox Hide",
     "parts": ["Écailles"],
     "steps": {"Écailles": [{"paints": ["Rhinox Hide"]}]}},
    {"name": "Japanese line is kept as a note, not a step",
     "text": "Eyes:\nYriel Yellow\n下地は黒",
     "parts": ["Eyes"],
     "steps": {"Eyes": [{"paints": ["Yriel Yellow"]}]},
     "notes": {"Eyes": ["下地は黒"]}},
    {"name": "Russian line is kept as a note, not a step",
     "text": "Eyes:\nYriel Yellow\nГрунт чёрный",
     "parts": ["Eyes"],
     "steps": {"Eyes": [{"paints": ["Yriel Yellow"]}]},
     "notes": {"Eyes": ["Грунт чёрный"]}},

    # --- Windows line endings (already works) ---
    {"name": "Windows line endings",
     "text": "Eyes:\r\nYriel Yellow\r\n\r\nTeeth:\r\nWraithbone\r\n",
     "parts": ["Eyes", "Teeth"],
     "steps": {"Eyes": [{"paints": ["Yriel Yellow"]}], "Teeth": [{"paints": ["Wraithbone"]}]}},
]

# What the reader makes of the text, cut down to what the tests compare.
SUMMARY_JS = """text => parseRecipeText(text).schemes.map(s => ({
  name: s.name,
  parts: s.parts.map(p => ({
    name: p.name,
    notes: p.notes.slice(),
    steps: p.steps.map(st => ({
      technique: st.technique || "",
      paints: st.paints.map(m => m.paint ? m.paint.name : m.typed),
      ratio: st.ratio || "",
      note: st.note || "",
    })),
  })),
}))"""

results = []
def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def compare(case, schemes):
    """Checks one case's answer. Returns a list of problems (empty = all good)."""
    problems = []
    parts = [p for s in schemes for p in s["parts"]]
    names = [p["name"] for p in parts]
    if "parts" in case and names != case["parts"]:
        problems.append(f"parts {names}, want {case['parts']}")
    if "scheme" in case:
        got = schemes[0]["name"] if schemes else None
        if got != case["scheme"]:
            problems.append(f"scheme name {got!r}, want {case['scheme']!r}")
    for part_name, want_steps in case.get("steps", {}).items():
        part = next((p for p in parts if p["name"] == part_name), None)
        if not part:
            continue  # already reported as a parts problem
        got_steps = part["steps"]
        if len(got_steps) != len(want_steps):
            problems.append(f"'{part_name}' has {len(got_steps)} steps {[s['paints'] for s in got_steps]}, "
                            f"want {len(want_steps)}")
            continue
        for i, (got, want) in enumerate(zip(got_steps, want_steps), 1):
            for key, value in want.items():
                if got[key] != value:
                    problems.append(f"'{part_name}' step {i} {key} is {got[key]!r}, want {value!r}")
    for part_name, want_notes in case.get("notes", {}).items():
        part = next((p for p in parts if p["name"] == part_name), None)
        for n in want_notes:
            if part and n not in " ".join(part["notes"]):
                problems.append(f"'{part_name}' notes {part['notes']}, want them to include {n!r}")
    all_paints = [n for p in parts for st in p["steps"] for n in st["paints"]]
    for bad in case.get("not_paints", []):
        if bad in all_paints:
            problems.append(f"{bad!r} was read as a paint")
    return problems

def main():
    keep = open(os.path.join(HERE, "keep_note.txt"), encoding="utf-8").read()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        # Start from an empty store; an empty unit list stops the three example units.
        page.goto(f"{BASE}/manifest.json")
        page.evaluate("() => { localStorage.clear(); localStorage.setItem('mini-tracker-models', '[]'); }")
        page.goto(f"{BASE}/index.html")
        page.wait_for_timeout(300)

        print("--- Known answers: what the reader makes of each paste ---")
        for case in CASES:
            try:
                schemes = page.evaluate(SUMMARY_JS, case["text"])
                problems = compare(case, schemes)
            except Exception as e:  # the reader itself crashed
                problems = [f"the reader crashed: {str(e).splitlines()[0]}"]
            check(case["name"], not problems, "; ".join(problems))

        print("\n--- Preview: Read notes shows a preview with a Save button ---")
        for case in CASES:
            errors = []
            handler = lambda e: errors.append(str(e))
            page.on("pageerror", handler)
            page.evaluate("startImport()")   # what the "Paste recipes from your notes" button does
            page.fill("#import-text", case["text"])
            page.click("#import-page button.primary-button")   # "Read notes"
            page.wait_for_timeout(100)
            has_save = page.locator("#import-save").count() == 1
            page.remove_listener("pageerror", handler)
            check(f"preview: {case['name']}", has_save and not errors,
                  f"Save button shown: {has_save}; page errors: {errors}")

        print("\n--- Brand named in the note, and very long pastes ---")
        # Your palette has AK Interactive "Ivory". A note saying "Vallejo Ivory" must not pick it.
        brand = page.evaluate("""() => {
            book.paints.push({ id: 9999, brand: "AK Interactive", name: "Ivory", colour: "#eeeedd" });
            const m = matchPaint("Vallejo Ivory");
            const plain = matchPaint("Ivory");
            book.paints.pop();
            return { brand: m.paint && m.paint.brand, status: m.status, plainBrand: plain.paint && plain.paint.brand };
        }""")
        check("'Vallejo Ivory' is a Vallejo paint, not your AK Ivory",
              brand["brand"] == "Vallejo" and brand["status"] == "new", brand)
        check("plain 'Ivory' still finds your AK Ivory", brand["plainBrand"] == "AK Interactive", brand)
        accent = page.evaluate("matchKey('Marrón Écaille')")
        check("accented letters still match (Marrón = marron)", accent == "marron ecaille", accent)

        long_text = "Eyes:\nYriel Yellow\n" + ("Notes: lots of words here\n" * 1500)
        page.evaluate("startImport()")
        page.fill("#import-text", long_text)
        page.click("#import-page button.primary-button")
        page.wait_for_timeout(200)
        body = page.inner_text("#import-page")
        check("a paste over 20,000 characters is cut, and it says so",
              "only the first" in body and page.locator("#import-save").count() == 1, body[:200])

        print("\n--- tests/keep_note.txt (a real Google Keep note) ---")
        schemes = page.evaluate(SUMMARY_JS, keep)
        check("keep note: two schemes, Tyranids and T'au",
              [s["name"] for s in schemes] == ["Tyranids", "T'au"], [s["name"] for s in schemes])
        tyr = [p["name"] for p in schemes[0]["parts"]] if schemes else []
        want_tyr = ["Whole model", "Skin/gun", "Eyes", "Chitin", "Hoofs/scythes", "Teeth", "Tongues",
                    "Red brains", "Blue and red", "Juicy green bits", "Bases"]
        check("keep note: the Tyranid parts", tyr == want_tyr, f"got {tyr}")
        flat = {p["name"]: p for s in schemes for p in s["parts"]}
        skin = flat.get("Skin/gun", {"steps": []})["steps"]
        check("keep note: 'Vallejo express 50/50' + two paints is one 50/50 mix",
              len(skin) == 1 and skin[0]["ratio"] == "50/50" and skin[0]["paints"] == ["Mystic Blue", "Storm Blue"],
              skin)
        brains = flat.get("Red brains", {"steps": []})["steps"]
        check("keep note: '1:1 Baal:CM' is one 1:1 mix of Baal Red and CM",
              any(st["ratio"] == "1:1" and st["paints"] == ["Baal Red", "CM"] for st in brains), brains)
        times = page.evaluate("""t => [1, 2, 3].map(() => {
            const start = performance.now(); parseRecipeText(t); return performance.now() - start; })""", keep)
        fastest = min(times)
        check("keep note: reading it takes under 200 ms", fastest < 200,
              f"fastest of 3 runs took {fastest:.0f} ms")

        errors = []
        handler = lambda e: errors.append(str(e))
        page.on("pageerror", handler)
        page.evaluate("startImport()")
        page.fill("#import-text", keep)
        page.click("#import-page button.primary-button")
        page.wait_for_timeout(200)
        check("keep note: the preview shows, with no page errors",
              page.locator("#import-save").count() == 1 and not errors, errors)
        shots = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "screenshots")
        os.makedirs(shots, exist_ok=True)
        page.screenshot(path=os.path.join(shots, "v18_paste_keep_note.png"), full_page=True)
        browser.close()

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
