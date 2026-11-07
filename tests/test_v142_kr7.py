"""KR7 tests for Minifolio (George's decided knowledge-base corrections, and related links up to five). New behaviour only:
1. The knowledge-base checker accepts a related list of five and refuses six.
2. The 21 guides that gained a fifth related link show five buttons, the added link is last, and it opens the right guide.
3. The new oils, spray-primer, metal and starter-kit wording is in, and the old wording is gone.
4. A fifth related button wraps on a 320 px phone with no sideways scroll.
Not covered: applying-transfers (correction c084) was held back because George's wording makes that paragraph longer than the
400-character limit, so there is no check for it here.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "knowledge-base"))
import check_knowledge as C

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# guide key -> the link added as the fifth one (from the decided corrections c128 to c148)
ADDED = {
    "designing-a-base": "easiest-first-base", "photographing-models": "photos-with-a-phone", "transporting-models": "storing-terrain",
    "varnishing": "brush-on-varnish", "protecting-painted-models": "fixing-chipped-paint", "touching-up-old-models": "fixing-chipped-paint",
    "using-value": "painting-with-colour-blindness", "consistent-bases": "movement-trays", "glowing-light-sources": "lights-in-models",
    "painting-terms-glossary": "more-painting-terms", "weathering-basics": "first-weathering-job", "nmm-basics": "first-nmm-sword",
    "oil-washes": "first-oil-paints", "applying-contrast-paints": "airbrushing-one-coat-paints", "hairspray-chipping": "salt-weathering",
    "airbrush-masking": "masking-fluid-by-brush", "mixing-skin-tones": "real-skin-tone-range", "camouflage-patterns": "digital-pixel-camo",
    "membrane-wings": "painting-insect-wings", "damp-patches-and-drips": "rain-and-wet-surfaces", "angular-surfaces": "painting-robots-and-mechs",
}

# guide key -> (text that must be in the body, text that must be gone)
TEXT = {
    "oil-washes": ("let the paint cure first, ideally overnight", "need only about half an hour to dry"),
    "oil-paints-on-models": ("once the paint has cured, ideally over", "dried for about half an hour"),
    "fix-priming-problems": ("roughly 10 to 27 C", "20 to 28"),
    "spray-priming": ("check the can's label", None),
    "preparing-metal-models": ("lead", None),
    "starter-tool-kit": ("mask", None),
}

def main():
    errors = []

    print("\n--- 1. The checker's related limit ---")
    def related_problems(n):
        rep = C.Report()
        C.need_list(rep, "x", {"related": ["k%d" % i for i in range(n)]}, "related", 0, 5)
        return len(rep.problems)
    check("a related list of 5 is accepted", related_problems(5) == 0)
    check("a related list of 6 is refused", related_problems(6) == 1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.goto(t.URL)
        wait_settled(page)
        guides = page.evaluate("() => Object.fromEntries(GUIDE_ENTRIES.map(e => [e.key, e]))")

        print("\n--- 2. Five related links on 21 guides ---")
        check("all 21 guides are there", all(k in guides for k in ADDED), [k for k in ADDED if k not in guides])
        check("each has five related links, the added one last",
              all(len(guides[k]["related"]) == 5 and guides[k]["related"][-1] == v for k, v in ADDED.items()),
              {k: guides[k]["related"] for k, v in ADDED.items() if guides[k]["related"][-1:] != [v]})
        check("every added link is a real entry", all(v in guides for v in ADDED.values()), [v for v in ADDED.values() if v not in guides])

        print("\n--- 3. New wording ---")
        for key, (new, old) in TEXT.items():
            body = " ".join(guides[key]["body"])
            check(f"{key}: new wording in", new in body, body[:200])
            if old:
                check(f"{key}: old wording gone", old not in body)
        check("the oils-over-acrylic wording also reaches the oils drying guide and the pin wash and filter guides",
              all("overnight" in " ".join(guides[k]["body"]) for k in ("drying-and-curing-times", "oil-pin-wash", "oil-filters")))
        pale = page.evaluate("() => (typeof BASING_TIPS !== 'undefined' ? JSON.stringify(BASING_TIPS) : '')")
        check("pale stone ground now mentions letting the paint cure or varnishing first", "pale-stone-ground" in pale and "varnish" in pale.split("pale-stone-ground")[1][:1500].lower())

        print("\n--- 4. Fifth button on a small phone ---")
        for w, h in ((320, 568), (360, 640)):
            page.set_viewport_size({"width": w, "height": h})
            page.evaluate("(k) => openGuide(k)", "nmm-basics")
            wait_settled(page)
            r = page.evaluate("""() => { const b = [...document.querySelectorAll('.guides-related button')];
                const last = b[b.length - 1].getBoundingClientRect(); return { n: b.length, inside: last.right <= innerWidth + 0.5 && last.left >= 0,
                  scroll: document.documentElement.scrollWidth > innerWidth, key: b[b.length - 1].dataset.related }; }""")
            check(f"{w} px: five buttons, the fifth inside the screen, no sideways scroll", r["n"] == 5 and r["inside"] and not r["scroll"], r)
        page.click(".guides-related button:last-child")
        wait_settled(page)
        check("the fifth button opens first-nmm-sword", page.get_attribute(".guides-entry", "data-key") == "first-nmm-sword")

        check("no page errors", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
