"""KR3a tests for Minifolio (approved wording rewrites in Problems, Basing and Detailed recipes). New behaviour only:
the new wording is in the app and the old wording is gone, for a sample of each, and the whole set of 24 fields is checked by text.
Run with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# (list, key, new text, old text)
GUIDES = [
    ("disguising-rough-sculpts", "Or play up odd features with bold, characterful painting instead of hiding them.", "Lean into odd features"),
    ("fix-transfer-problems", "the grime ties them into the paint and they look painted on.", "Done well, they look painted on."),
    ("fix-glow-effects", "A glow comes from lightness more than colour.", "A glow is about light, not colour."),
    ("fix-glow-effects", "each one shows up.", "so each one reads."),
    ("beating-perfectionism", "If you keep saving it, you never start it.", "Saving it forever just means never starting."),
    ("following-tutorials", "only come from practice with your own tools, so expect to adjust things as you go.", "Expect to adjust and experiment"),
    ("fix-rough-paint-texture", "come from paint that is too thick, or from brushing over paint that has started to dry.", "come from two things:"),
]
# (list, key, new text, old text); text is searched in the entry's summary, materials, how-to and paint notes
TIPS = [
    ("blending-base-textures", "so they look like one ground", "so they read as one ground"),
    ("wet-muddy-ground", "trampled, not fresh", "trampled rather than fresh"),
    ("forest-floor", "Garden soil, baked dry", "Dry garden soil, baked dry"),
    ("swamp-and-bog", "Gloss over the matt wash so the mud looks boggy.", "make the mud read as boggy"),
    ("trees-from-twigs", "so it looks like bark", "so it reads as bark"),
    ("wooden-plank-floors", "small gaps here and there", "small gaps for interest"),
    ("coloured-liquid-pools", "so it looks deeper in the middle", "so it reads deeper in the middle"),
    ("resin-ice", "Clear resin over a mirror and tint for depth, with cracks on top", "cracks for real depth"),
]
RECIPES = [
    ("exposed-muscle", "looks more like meat", "reads more like meat"),
    ("pale-sickly-skin", "Pale, clammy skin with a warm wash and a sickly tint", "Clammy, pale and unhealthy skin"),
    ("glowing-water", "so it looks wet", "so it reads as wet"),
    ("drab-greatcoat", "using a warm pale tone, not white", "beats white"),
    ("olive-uniform-cloth", "strong contrast works well", "strong contrast reads well"),
    ("dark-iron", "in the rivets looks like rust", "in the rivets reads as rust"),
    ("gold-treasure", "Silver over gold looks brighter than a lighter gold.", "gives more punch"),
    ("light-rust", "as kept armour needs very little", "less is more on kept armour"),
    ("painted-copper-and-bronze", "makes it look like copper", "gives copper its character"),
]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.goto(t.URL)
        wait_settled(page)
        g = page.evaluate("() => Object.fromEntries(GUIDE_ENTRIES.map(e => [e.key, JSON.stringify(e)]))")
        r = page.evaluate("() => Object.fromEntries(DETAIL_RECIPES.map(e => [e.key, JSON.stringify(e)]))")
        b = page.evaluate("() => Object.fromEntries(BASING_TIPS.map(e => [e.key, JSON.stringify(e)]))")
        print("\n--- Problems ---")
        for key, new, old in GUIDES:
            s = g.get(key, "")
            check(f"{key}: new wording in, old gone", new in s and old not in s)
        print("\n--- Basing ---")
        for key, new, old in TIPS:
            s = b.get(key, "")
            check(f"{key}: new wording in, old gone", new in s and old not in s)
        print("\n--- Detailed recipes ---")
        for key, new, old in RECIPES:
            s = r.get(key, "")
            check(f"{key}: new wording in, old gone", new in s and old not in s)
        check("no page errors", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
