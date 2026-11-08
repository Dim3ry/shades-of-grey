"""KR8b tests for Minifolio (See also links for the approved pairs). New behaviour only:
1. The 222 approved pairs are in the See also map; the 4 skipped pairs (numbers 30, 31, 35, 36) are not.
2. No guide has more than 3 See also links, and every link points at a real, different guide.
3. A sample of the new links shows on the entry page and opens the right guide.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t
from launch_helpers import wait_settled, tap_tab

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {str(detail)[:600]}"))

APPROVED = [
    ("accent-colour", "fantasy-hero-colours"),
    ("choosing-a-colour-scheme", "fantasy-hero-colours"),
    ("brighten-dark-schemes", "researching-historical-colours"),
    ("unify-army-colours", "varying-colours-across-a-unit"),
    ("vary-skin-across-a-squad", "varying-colours-across-a-unit"),
    ("painting-terms-glossary", "more-painting-terms"),
    ("hue-value-saturation", "more-painting-terms"),
    ("checking-values-in-greyscale", "painting-with-colour-blindness"),
    ("using-value", "painting-with-colour-blindness"),
    ("controlling-saturation", "base-colours-for-weathering"),
    ("mixing-colour-steps", "essential-first-colours"),
    ("limited-palette", "essential-first-colours"),
    ("mixing-colour-steps", "mixing-one-coat-paints"),
    ("fix-chalky-highlights", "painting-blue"),
    ("mixing-greys-and-browns", "painting-brown"),
    ("varying-browns-and-leathers", "painting-brown"),
    ("green-skin", "painting-green"),
    ("mixing-greys-and-browns", "painting-grey"),
    ("tinted-neutrals", "painting-grey"),
    ("fluorescent-paints", "painting-pink"),
    ("controlling-saturation", "painting-purple"),
    ("shading-without-black", "painting-purple"),
    ("blending-methods", "blending-colour-choice"),
    ("fix-airbrush-spidering", "fix-airbrush-spitting"),
    ("fix-clogged-airbrush", "fix-airbrush-spitting"),
    ("fix-priming-problems", "spray-can-faults"),
    ("fix-frosted-varnish", "fix-thick-varnish-or-primer"),
    ("crackle-paint-problems", "fix-basing-problems"),
    ("supporting-3d-prints", "failed-resin-prints"),
    ("gap-filling", "hollow-backs-and-pin-marks"),
    ("replacing-snapped-parts", "resin-print-problems"),
    ("fix-a-paint-job-you-hate", "fix-flat-or-muddy-model"),
    ("rinse-water-habits", "fix-dust-and-hairs-in-paint"),
    ("fix-dry-paint-mistakes", "fix-metallic-glitter-in-paint"),
    ("fix-wash-tide-marks", "fix-blotchy-one-coat-paints"),
    ("brushes-for-rough-jobs", "split-or-hooked-brush-tips"),
    ("airbrush-tinting", "airbrushed-cloth"),
    ("airbrush-highlights", "airbrushed-cloth"),
    ("airbrush-tinting", "airbrushing-one-coat-paints"),
    ("applying-contrast-paints", "airbrushing-one-coat-paints"),
    ("freehand-lettering", "added-panel-lines"),
    ("panel-lining", "added-panel-lines"),
    ("recess-shading", "crisp-armour-method"),
    ("stacked-edge-highlights", "crisp-armour-method"),
    ("stacked-edge-highlights", "painting-joints-and-cables"),
    ("painting-vehicles-by-brush", "painting-robots-and-mechs"),
    ("angular-surfaces", "painting-robots-and-mechs"),
    ("painting-vehicles-by-brush", "rubber-tyres-and-hoses"),
    ("hazard-stripes", "rubber-tyres-and-hoses"),
    ("airbrushed-metal", "weathered-chrome"),
    ("painting-vehicles-by-brush", "weathered-chrome"),
    ("black-lining", "clean-crisp-painting"),
    ("recess-shading", "clean-crisp-painting"),
    ("base-coating", "selective-base-coat"),
    ("black-lining", "black-out-stage"),
    ("order-of-painting", "black-out-stage"),
    ("painting-base-rims", "vignette-bases"),
    ("painting-cloth", "painting-tartan"),
    ("quartered-designs", "painting-tartan"),
    ("painting-cloth", "velvet-and-fur-trim"),
    ("silk-and-satin", "velvet-and-fur-trim"),
    ("streaky-rotten-textures", "maggots-and-grubs"),
    ("wounds-and-gore", "maggots-and-grubs"),
    ("painting-animals", "horses-and-mounts"),
    ("iridescent-colour-shift", "painting-insect-wings"),
    ("membrane-wings", "painting-insect-wings"),
    ("slime-and-goo", "tentacles-and-suckers"),
    ("glazing-for-smooth-gradients", "tentacles-and-suckers"),
    ("creature-eyes", "cube-and-eye-monsters"),
    ("slime-and-goo", "cube-and-eye-monsters"),
    ("freehand-patterns", "snake-and-serpent-patterns"),
    ("painting-scales", "snake-and-serpent-patterns"),
    ("skin-blemishes-and-freckles", "spots-and-markings"),
    ("painting-scales", "spots-and-markings"),
    ("drybrushing", "drybrushed-carapace"),
    ("painting-horns", "drybrushed-carapace"),
    ("quick-faces", "faces-with-contrast-paints"),
    ("face-highlight-placement", "faces-with-contrast-paints"),
    ("painting-cracks", "porcelain-and-doll-faces"),
    ("painting-soft-faces", "porcelain-and-doll-faces"),
    ("masking-tape-stripes", "digital-pixel-camo"),
    ("camouflage-patterns", "digital-pixel-camo"),
    ("freehand-painting", "painting-banners-and-flags"),
    ("freehand-symbols", "painting-banners-and-flags"),
    ("freehand-symbols", "stamping-designs"),
    ("quartered-designs", "stamping-designs"),
    ("applying-transfers", "matching-squad-markings"),
    ("freehand-lettering", "matching-squad-markings"),
    ("masking-tape-stripes", "masking-fluid-by-brush"),
    ("airbrush-masking", "masking-fluid-by-brush"),
    ("batch-painting", "how-long-painting-takes"),
    ("tabletop-vs-display-standard", "how-long-painting-takes"),
    ("asking-for-critique", "painting-with-others"),
    ("improving-your-painting", "painting-with-others"),
    ("edge-highlight-brush-strokes", "jagged-edge-highlights"),
    ("edge-highlighting", "jagged-edge-highlights"),
    ("directional-edge-highlights", "inverted-edge-highlights"),
    ("stacked-edge-highlights", "inverted-edge-highlights"),
    ("painting-glass", "books-bottles-and-props"),
    ("parchment-and-scrolls", "books-bottles-and-props"),
    ("selective-gloss", "painting-marble"),
    ("painting-stone", "painting-marble"),
    ("glazing", "pearl-and-shell"),
    ("painting-gems", "pearl-and-shell"),
    ("painting-rope", "ships-sails-and-rigging"),
    ("painting-wood-grain", "ships-sails-and-rigging"),
    ("tinted-metallics", "metal-powder-paints"),
    ("highlighting-metallics", "scale-mail"),
    ("painting-chainmail", "scale-mail"),
    ("nmm-steel", "first-nmm-sword"),
    ("nmm-reflections", "first-nmm-sword"),
    ("nmm-basics", "nmm-finishing"),
    ("nmm-reflections", "nmm-finishing"),
    ("highlights-by-shape", "nmm-shapes"),
    ("nmm-reflections", "nmm-shapes"),
    ("fluorescent-paints", "glow-in-the-dark-and-uv-paints"),
    ("glowing-runes", "glow-in-the-dark-and-uv-paints"),
    ("glow-on-surroundings", "painting-holograms"),
    ("glowing-light-sources", "painting-holograms"),
    ("oil-pin-wash", "first-oil-paints"),
    ("oil-washes", "first-oil-paints"),
    ("asking-for-critique", "painting-competitions"),
    ("tabletop-vs-display-standard", "painting-competitions"),
    ("comic-style-painting", "finding-your-style"),
    ("graphic-painting-style", "finding-your-style"),
    ("grime-with-washes", "gritty-dark-style"),
    ("weathering-order", "gritty-dark-style"),
    ("smooth-blends-on-large-areas", "busts-and-large-scale-workflow"),
    ("wet-blending-large-areas", "busts-and-large-scale-workflow"),
    ("pre-highlighting", "skin-from-one-undercoat"),
    ("skin-by-layering", "painting-hands-and-limbs"),
    ("painting-muscles", "painting-hands-and-limbs"),
    ("snow-on-models", "frost-and-icicles-on-models"),
    ("painting-fire", "painting-smoke"),
    ("soot-and-scorch", "painting-smoke"),
    ("damp-patches-and-drips", "rain-and-wet-surfaces"),
    ("slime-and-goo", "rain-and-wet-surfaces"),
    ("quick-tabletop-method", "tabletop-stop-points"),
    ("spend-time-where-it-shows", "tabletop-stop-points"),
    ("all-over-wash", "dip-method"),
    ("speed-painting", "dip-method"),
    ("wet-blending", "wet-blending-contrast-paints"),
    ("stippling-texture", "mottled-textured-armour"),
    ("streaky-rotten-textures", "mottled-textured-armour"),
    ("sculpting-with-putty", "pressing-texture-into-putty"),
    ("sponge-gradients", "sponging-texture"),
    ("stippling-texture", "sponging-texture"),
    ("black-lining", "changing-detail-with-paint"),
    ("light-and-volume-sketch", "spotlit-models"),
    ("light-and-volume-sketch", "cast-shadows"),
    ("volumetric-highlights", "cast-shadows"),
    ("applying-washes", "highlight-before-or-after-wash"),
    ("all-over-wash", "highlight-before-or-after-wash"),
    ("recess-shading", "over-shade-then-tidy"),
    ("shading-without-washes", "over-shade-then-tidy"),
    ("enamel-washes", "watercolour-gouache-washes"),
    ("panel-lining", "watercolour-gouache-washes"),
    ("weathering-order", "first-weathering-job"),
    ("weathering-basics", "first-weathering-job"),
    ("oil-filters", "sun-faded-paint"),
    ("painting-chips-and-scratches", "sun-faded-paint"),
    ("hairspray-chipping", "salt-weathering"),
    ("sponge-chipping", "salt-weathering"),
    ("where-chips-go", "rubbed-edge-wear"),
    ("worn-metal-edges", "rubbed-edge-wear"),
    ("enamel-streaks", "fuel-and-oil-stains"),
    ("mud-on-vehicles", "fuel-and-oil-stains"),
    ("blending-tiny-areas", "loaded-brush-blending"),
    ("blending-methods", "loaded-brush-blending"),
    ("glazing", "wet-in-wet-blending"),
    ("smooth-blends-on-large-areas", "wet-in-wet-blending"),
    ("filament-3d-prints", "resin-or-filament-printing"),
    ("resin-printing-setup", "resin-or-filament-printing"),
    ("clippers-and-clipping", "assembly-hand-tools"),
    ("mould-line-removal", "assembly-hand-tools"),
    ("hovering-models", "flying-stands"),
    ("pinning-to-bases", "flying-stands"),
    ("pinning-to-bases", "gluing-models-to-bases"),
    ("rebasing-models", "gluing-models-to-bases"),
    ("magnetising", "movement-trays"),
    ("painting-base-rims", "movement-trays"),
    ("wire-details", "making-barbed-wire"),
    ("cheap-basing-materials", "easiest-first-base"),
    ("basing-glue-and-tools", "easiest-first-base"),
    ("loading-the-brush", "dry-palette"),
    ("wet-palette", "dry-palette"),
    ("stripping-paint", "checking-second-hand-models"),
    ("taking-apart-old-models", "checking-second-hand-models"),
    ("starter-tool-kit", "first-sessions-path"),
    ("building-your-first-kit", "picking-models-to-paint"),
    ("painting-in-sub-assemblies", "picking-models-to-paint"),
    ("painting-in-sub-assemblies", "planning-large-models"),
    ("starter-tool-kit", "starter-sets-vs-separate-paints"),
    ("hobby-on-a-budget", "starter-sets-vs-separate-paints"),
    ("planning-a-diorama", "understanding-scale"),
    ("starter-tool-kit", "what-to-upgrade-first"),
    ("is-an-airbrush-worth-it", "what-to-upgrade-first"),
    ("kitbashing", "army-conversion-theme"),
    ("planning-a-kitbash", "army-conversion-theme"),
    ("camouflage-patterns", "foliage-camouflage-on-vehicles"),
    ("kitbashing", "making-casualty-models"),
    ("dynamic-posing", "making-casualty-models"),
    ("acrylic-enamel-and-oil-paints", "mixing-paint-ranges"),
    ("hobby-paint-types", "mixing-paint-ranges"),
    ("choosing-paints", "paint-markers"),
    ("sprue-goo", "reusing-old-sprue"),
    ("scratch-building-details", "reusing-old-sprue"),
    ("kitbashing-terrain", "building-ruined-walls"),
    ("scratch-built-terrain", "building-ruined-walls"),
    ("carving-stone-and-cracks", "cutting-and-sealing-foam"),
    ("scratch-built-terrain", "cutting-and-sealing-foam"),
    ("mounting-on-plinths", "lights-in-models"),
    ("building-a-gaming-board", "storing-terrain"),
    ("transporting-models", "storing-terrain"),
    ("card-modelling", "thatched-roofs"),
    ("scratch-built-terrain", "thatched-roofs"),
    ("drying-and-curing-times", "brush-on-varnish"),
    ("varnishing", "brush-on-varnish"),
    ("progress-photo-records", "photos-with-a-phone"),
    ("photographing-models", "photos-with-a-phone"),
    ("organising-the-hobby-space", "hobby-kit-pets-and-kids"),
    ("hobby-safety", "hobby-kit-pets-and-kids"),
]

SKIPPED = [
    ("raised-ground-on-bases", "fixing-a-leaning-model"),
    ("sculpting-cloth", "sculpting-over-damage"),
    ("paint-pot-care", "common-beginner-mistakes"),
    ("what-is-acrylic-paint", "paint-on-clothes"),
]

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        t.load(page, settings={"tab": "guides", "examplesChecked": True})
        tap_tab(page, "guides")
        page.click('#more-seg button[data-page="guides"]')
        page.wait_for_function("() => typeof guideSeeAlso === 'function'")
        wait_settled(page)

        print("\n--- 1. The approved pairs ---")
        r = page.evaluate("""(a) => { const m = GUIDE_GROUPS.seeAlso; return a.filter(([f, t]) => !(m[f] || []).includes(t)); }""", [list(x) for x in APPROVED])
        check("all 222 approved pairs are in the See also map", len(APPROVED) == 222 and not r, r)
        r = page.evaluate("""(a) => { const m = GUIDE_GROUPS.seeAlso; return a.filter(([f, t]) => (m[f] || []).includes(t)); }""", [list(x) for x in SKIPPED])
        check("the 4 skipped pairs (30, 31, 35, 36) are not there", len(SKIPPED) == 4 and not r, r)

        print("\n--- 2. Limits and real targets ---")
        r = page.evaluate("""() => { const kn = knowledgeIndex(), bad = [];
            for (const [from, keys] of Object.entries(GUIDE_GROUPS.seeAlso)) {
                if (!kn.get(from)) bad.push(['no entry', from]);
                if (keys.length > 3 || new Set(keys).size !== keys.length) bad.push(['list', from]);
                for (const k of keys) if (!kn.get(k) || k === from) bad.push(['target', from, k]); }
            return bad; }""")
        check("nobody has more than 3 See also links, and every target is a real different entry", not r, r)

        print("\n--- 3. Links open ---")
        for frm, to in [APPROVED[0], APPROVED[100], APPROVED[-1]]:
            page.evaluate("(k) => { Object.assign(guidesState, { view: 'entry', key: k, kind: 'guide', query: '' }); renderGuides(); }", frm)
            wait_settled(page)
            link = page.locator('.guides-seealso-link[data-see-also="%s"]' % to)
            check(f"{frm} shows a See also link to {to}", link.count() == 1)
            if link.count() == 1:
                link.scroll_into_view_if_needed()
                link.click()
                wait_settled(page)
                check(f"the link opens {to}", page.evaluate("() => guidesState.key") == to, page.evaluate("() => guidesState.key"))

        check("no page errors or pop-ups", errors == [], errors)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
