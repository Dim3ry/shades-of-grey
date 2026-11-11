"""HS2 test for Minifolio (safety notice, short safety line, safer advice). New behaviour only."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab, open_settings

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:400]}"))

NOTICE = "Common hobby tips, not safety advice. Always follow the maker's instructions and safety sheet, and work somewhere well ventilated and safe."
LINE = "Hobby tip, not safety advice. Follow the maker's instructions and ventilate well."
OLD_HELP = "Guides and Mentor give general hobby tips, not professional safety advice. Always follow the maker's label and safety sheet."
# (key, body paragraph number or "summary", the exact proposed text): a sample of the approved changes, one or more per theme
PARAS = [
    ("hobby-safety", 1, "Work with a window open or good airflow, and take breaks. Spray cans belong outdoors. Airbrushes belong outdoors or in a booth that vents outside, used only with paints the booth's maker says it suits."),
    ("hobby-safety", 3, "For general hobby use, pick a combined filter rated A2 for organic vapours and the top particle class for fine dust. For uncured printing resin, check the resin's safety sheet and your printer maker's advice on the filter and ventilation it needs."),
    ("spray-booth", "summary", "A booth's fan and filters pull overspray away from you; vent it outside and keep the filter clean."),
    ("spray-booth", 8, "Never spray aerosol cans or flammable solvents in a hobby booth, as the fan motor can spark. Only use paints the booth's maker says it suits."),
    ("airbrush-safety", 4, "Spray into a booth that vents outside if you can. Otherwise ventilate well, but an open window alone isn't enough, and a fan only helps if it pushes air outside. Check what your booth's maker says it suits."),
    ("airbrush-safety", 8, "Read the label or safety sheet for everything you spray, follow the maker's instructions, and set the room up before you start."),
    ("superglue-problems", 4, "Clear a clogged nozzle with a pin, or swap in a fresh one. Never heat it or use a flame: the glue's vapour is combustible and heat can set it off."),
    ("speeding-up-drying", 5, "Keep a heat gun away from wet paint: it can warp parts, and oils and enamels still hold flammable solvent. Let those dry in a warm, well ventilated room instead."),
    ("straightening-bent-parts", 2, "Dip a warped resin part in hot water, from about 70 C, for 30 to 60 seconds, or warm it with a hair dryer, until it flexes slightly. Take care not to scald yourself. Keep plastic out of hot water, as polystyrene softens from about 80 C; use a hair dryer on it instead."),
    # house style (v147 KR9): "it is" in the middle of a clause is written "it's", so this one word differs from the drafted text; the meaning is the same
    ("choosing-glue", 6, "Super glue grabs fast and usually snaps cleanly at the joint, so you can test a pose and redo it. Use plastic glue for a permanent bond and super glue where you may change your mind, or on painted parts. Acetone softens super glue to undo a join, but it can harm paint and some plastics, and it's highly flammable: ventilate and keep it from flames. Scrape off old glue before refitting."),
    ("resin-water-effects", 2, None),   # gloves sentence added where epoxy is first named
]
GONE = ["filter booth can sit anywhere", "inorganic vapours (B2", "if you like, wear", "wear gloves with strong cleaners if you like", "an airbrush indoors",
        "the filters alone may do", "heating the metal tip with a lighter", "A small heat gun on its lowest setting works too"]
RESIN_ICE_STEP = "Cut the mirror to fit, stick it down, then, in nitrile gloves, spread thin resin to the edge and cure it."
LISTED = ["airbrush-safety", "choosing-glue", "resin-printing-setup", "stripping-paint", "weathering-pigments"]
UNLISTED = ["brushes-for-rough-jobs", "painting-handles", "real-chain-details", "sculpting-armatures", "wet-palette"]

def main():
    gd = open(os.path.join(ROOT, "guides-data.js"), encoding="utf-8").read()
    by = {g["key"]: g for g in json.load(open(os.path.join(ROOT, "knowledge-base", "data", "k5-tools-prep-problems.json"), encoding="utf-8"))["guides"]}
    for key, i, text in PARAS:
        if text is None:
            continue
        got = by[key]["summary"] if i == "summary" else by[key]["body"][i - 1]
        check(f"{key} {i} is exactly the approved text, and the app carries it", got == text and text in gd, got)
    p2 = by["resin-water-effects"]["body"][1]
    check("resin-water-effects P2 names epoxy and now has the gloves sentence, inside 400 characters",
          p2.startswith("Two part clear epoxy") and p2.endswith("Wear nitrile gloves and keep uncured resin off your skin.") and len(p2) <= 400, len(p2))
    check("no changed paragraph or summary breaks the schema limits",
          all(20 <= len(by[k]["summary"]) <= 140 for k in {c[0] for c in PARAS}) and all(20 <= len(p) <= 400 for k in {c[0] for c in PARAS} for p in by[k]["body"]))
    check("the old risky and soft wordings are gone from the guides", not any(g in gd for g in GONE), [g for g in GONE if g in gd])
    bt = open(os.path.join(ROOT, "basing-tips.js"), encoding="utf-8").read()
    check("resin-ice how-to step 1 is the approved text (105 characters)", RESIN_ICE_STEP in bt and len(RESIN_ICE_STEP) <= 120)
    wb = open(os.path.join(ROOT, "where-to-buy.js"), encoding="utf-8").read()
    keys = re.findall(r'"([a-z0-9-]+)": "(?:guide|basing)"', wb[wb.index("const HOBBY_SAFETY_KEYS"):])
    check("the safety list has the short line's words fixed (81 characters) and 45 guides plus 2 Basing tips",
          f'HOBBY_SAFETY_LINE = "{LINE}"' in wb and len(LINE) == 81 and len(keys) == 47 and "resin-ice" in keys and "cave-floor" in keys, len(keys))
    check("dropped entries are not on the list", not any(k in keys for k in UNLISTED[:4] + ["trees-from-twigs"]))

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((390, 844), (360, 640)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, service_workers="block")
            page = ctx.new_page()
            page.on("pageerror", lambda x: errors.append(str(x)))
            t.load(page, launch=True, settings={"tab": "guides", "examplesChecked": True})
            page.wait_for_function("() => typeof guideGroupsOf === 'function'")
            tap_tab(page, "guides")
            wait_settled(page)
            n = page.locator("#guides-safety-notice")
            check(f"{w}px: the Guides home shows the notice once, in the agreed words",
                  n.count() == 1 and " ".join(n.inner_text().split()) == NOTICE and page.locator("#guides-safety-notice, .guides-safety-notice").count() == 1)
            check(f"{w}px: no sideways scroll on the Guides home", not page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"))
            for key in LISTED + ["resin-ice"]:
                page.evaluate("(k) => openGuide(k)", key)
                page.wait_for_selector(".guides-entry, .basing-sub")
                wait_settled(page)
                lines = page.locator("[data-safety-line]")
                check(f"{w}px: {key} shows the short line once, below its text, and no notice",
                      lines.count() == 1 and lines.get_attribute("data-safety-line") == key and lines.inner_text().strip() == LINE
                      and page.locator("#guides-safety-notice").count() == 0, lines.count())
                if key in ("airbrush-safety", "resin-ice"):
                    check(f"{w}px: {key} line does not overlap a button and the page does not scroll sideways",
                          page.evaluate("""() => { const l = document.querySelector('[data-safety-line]').getBoundingClientRect();
                            return ![...document.querySelectorAll('.guides-main button, .guides-main summary')].some(b => { const r = b.getBoundingClientRect();
                              return r.width && r.height && r.left < l.right && r.right > l.left && r.top < l.bottom - 1 && r.bottom > l.top + 1; })
                              && document.documentElement.scrollWidth <= innerWidth + 1; }"""))
            for key in UNLISTED[:1] + UNLISTED[4:]:
                page.evaluate("(k) => openGuide(k)", key)
                page.wait_for_selector(".guides-entry")
                check(f"{w}px: {key} (not listed) has no short line", page.locator("[data-safety-line]").count() == 0)
            ctx.close()
        # Help and the Mentor answer
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        t.load(page, settings={"examplesChecked": True}, launch=True)
        open_settings(page)
        page.click('#more-seg button[data-page="help"]')
        wait_settled(page)
        h = page.locator("#help-safety")
        body = " ".join(page.inner_text("#view-help").split())
        check("Help has the notice once at the top, and the old line is gone",
              h.count() == 1 and " ".join(h.inner_text().split()) == NOTICE and body.count(NOTICE) == 1 and OLD_HELP not in body and "professional safety advice" not in body)
        ms = open(os.path.join(ROOT, "mentor-engine.js"), encoding="utf-8").read() + open(os.path.join(ROOT, "mentor-data.js"), encoding="utf-8").read()
        check("Mentor does not carry the short line", LINE not in ms and "HOBBY_SAFETY" not in ms)
        browser.close()
    check("no page errors", not errors, errors)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)

main()
