"""F2 tests for Minifolio: an easier Colour Lab start.

New behaviour only:
1. Start from (Colour Lab > Colour ideas) shows your own paints as swatches under its heading: up to 12, the ones used in the most
   recipe steps first. A tap chooses the paint exactly as the list does, and the chosen one is pressed. More paints shows only when you
   own more than 12 and opens the full type-or-choose list. A tap in the box no longer opens the long list by itself; typing does.
   With no paints of your own there are no swatches and the box works as before.
2. Typing: the list narrows as you type, and Enter (the phone's Done key) picks the first match. This is in the shared box builder, so the
   Faction box and the Paint Picker's boxes pick the first match on Enter too.
3. Primers and inks are never suggested as a colour idea, whatever the part (Colour ideas, the Paint Picker and Mentor's colour answers).
   The type decides when a paint has one, otherwise the name; a paint whose type and name say neither is allowed. Primers and inks stay
   choosable in Start from.
4. The Paint Picker's Base colour and Second colour boxes have their own hints; the labels are unchanged.
5. 390x844, 360x640 and 320 px, dark and light: no sideways scroll, swatches wrap, a long name stays on its swatch, 44 px taps.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v31 as t

load, no_sideways = t.load, t.no_sideways
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

# an independent copy of the rule: the type decides when there is one, otherwise the name
PI_NAME = re.compile(r"\bprimers?\b|\bprime\b|\bspray$|\binks?\b|^inktense\b", re.I)
PI_TYPE = re.compile(r"\b(primers?|inks?)\b", re.I)
def primer_or_ink(p):
    ty = p.get("type")
    if isinstance(ty, str) and ty.strip():
        return bool(PI_TYPE.search(ty))
    return bool(PI_NAME.search((p.get("name") or "").strip()))

def P(i, name, colour, status="owned", brand="Test Paints", **more):
    return dict({"id": i, "brand": brand, "name": name, "colour": colour, "status": status}, **more)

LONG = "A Very Long Paint Name That Keeps On Going Well Past The Edge"
OWN = [P(i + 1, f"Own {c}", h) for i, (c, h) in enumerate([("Red", "#b22222"), ("Blue", "#2a4d9b"), ("Green", "#2e8b57"), ("Yellow", "#e0c020"),
       ("Orange", "#e07020"), ("Purple", "#6a3d9a"), ("Bone", "#d8cba0"), ("Grey", "#808890"), ("Black", "#1a1a1a"), ("White", "#f4f4f4"),
       ("Teal", "#1f8a8a"), ("Pink", "#e090b0"), ("Brown", "#6b4423")])]
OWN.append(P(20, LONG, "#7a5a3a"))
OWN.append(P(21, "Not Mine", "#3a7a5a", status="notowned"))
RECIPES = [t.rec(1, "Uses", "Armour", [13, 13, 13, 20, 20, 12])]   # Own Brown 3 steps, the long name 2, Own Pink 1
LAB = {"tab": "recipes", "recipeView": "colourlab", "examplesChecked": True, "recipeExamplesChecked": True}
UNITS = [t.unit(1, "Troop A", "Gloom Legion", [1]), t.unit(2, "Other", "Other Host", [1])]
BASE, LIST, STAT = "#cmp-colour-ideas-base", "#cmp-colour-ideas-base-list", "#cmp-colour-ideas-base-status"

def open_lab(page, lab):
    page.evaluate("(k) => openColourLab(k)", lab)
    page.wait_for_timeout(100)

def swatches(page):
    return page.evaluate("() => [...document.querySelectorAll('#cmp-start-swatches .start-swatch')].map(b => ({ name: b.querySelector('.start-swatch-name').textContent, key: b.dataset.startSwatch, on: b.getAttribute('aria-pressed') }))")

def idea_names(page, sel):
    return page.evaluate("(s) => [...document.querySelectorAll(s + ' .idea-list > li')].map(li => li.querySelector('.idea-name').childNodes[0].textContent)", sel)

def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))

        print("\n--- 1. Start from: your own paints as swatches ---")
        load(page, paints=OWN, recipes=RECIPES, units=UNITS, settings=LAB)
        open_lab(page, "ideas")
        sw = swatches(page)
        names = [s["name"] for s in sw]
        check("12 swatches show: the most used in your recipes first (Own Brown, the long name, Own Pink), then the rest by name; a paint you do not own is not one",
              len(sw) == 12 and names[:3] == ["Own Brown", LONG, "Own Pink"] and names[3:] == sorted(names[3:]) and "Not Mine" not in names, names)
        head = page.evaluate("""() => { const g = document.getElementById('cmp-start-swatches'), l = document.getElementById('cmp-colour-ideas-base-label');
            return { role: g.getAttribute('role'), by: g.getAttribute('aria-labelledby'), lab: l.textContent,
                     under: l.getBoundingClientRect().bottom <= g.getBoundingClientRect().top + 1 && g.getBoundingClientRect().bottom <= document.getElementById('cmp-colour-ideas-base').getBoundingClientRect().top + 1 }; }""")
        check("they sit under the Start from heading, above the box, as a group named by the heading", head == {"role": "group", "by": "cmp-colour-ideas-base-label", "lab": "Start from", "under": True}, head)
        check("each swatch has its colour dot and name, and none is pressed yet", page.locator("#cmp-start-swatches .start-swatch .swatch").count() == 12
              and all(s["on"] == "false" for s in sw))
        check("with 14 paints owned, More paints shows after them", page.locator("#cmp-start-swatches > .start-more").inner_text() == "More paints")
        check("nothing chosen: the plain line is still there and no ideas show", page.locator("#cmp-colour-ideas-none").count() == 1 and page.locator("#cmp-lab-ideas .idea-list > li").count() == 0)
        page.click("#cmp-start-swatches .start-swatch >> nth=4")
        page.wait_for_timeout(150)
        k4 = sw[4]["key"]
        check("tapping a swatch chooses that paint as the list does: the box shows it, the ideas appear, the swatch is pressed and keeps the focus",
              page.evaluate("() => compendiumState.base") == k4 and page.input_value(BASE) == f"{names[4]} (Test Paints)"
              and page.locator("#cmp-lab-ideas .idea-list > li").count() == 3 and swatches(page)[4]["on"] == "true"
              and sum(s["on"] == "true" for s in swatches(page)) == 1 and page.evaluate("() => document.activeElement.dataset.startSwatch") == k4)
        page.click(BASE)
        page.wait_for_timeout(100)
        check("a tap in the box does not open the long list by itself (it selects the name, ready to type over)", page.get_attribute(BASE, "aria-expanded") == "false"
              and not page.is_visible(LIST) and page.evaluate("(s) => { const i = document.querySelector(s); return i.selectionStart === 0 && i.selectionEnd === i.value.length; }", BASE))
        page.keyboard.press("Escape")
        page.click("#cmp-start-more")
        page.wait_for_timeout(150)
        groups = page.evaluate("() => [...document.querySelectorAll('#cmp-colour-ideas-base-list > li.combo-group')].map(e => e.textContent)")
        check("More paints opens the full list (yours, then the brands) with the focus in the box", page.get_attribute(BASE, "aria-expanded") == "true"
              and groups[:2] == ["Paints you own", "Other paints in your palette"] and any(g.startswith("More ") for g in groups)
              and page.evaluate("() => document.activeElement.id") == "cmp-colour-ideas-base", groups[:3])
        page.click(f"{LIST} [role=option] >> nth=5")
        page.wait_for_timeout(150)
        check("a paint picked from that list is chosen as before", page.evaluate("() => compendiumState.base") == "test paints|own green"
              and page.locator("#cmp-lab-ideas .idea-list > li").count() == 3, page.evaluate("() => compendiumState.base"))

        print("\n--- 2. Typing ---")
        page.click(BASE)
        page.keyboard.press("Control+A")
        page.keyboard.type("test own b")
        page.wait_for_timeout(80)
        opts = page.evaluate("(s) => [...document.querySelectorAll(s + ' [role=option]')].map(o => o.textContent)", LIST)
        check("typing opens the list and narrows it as you type, with the count", page.get_attribute(BASE, "aria-expanded") == "true"
              and opts == ["Own Black (Test Paints)", "Own Blue (Test Paints)", "Own Bone (Test Paints)", "Own Brown (Test Paints)"]
              and page.inner_text(STAT).strip() == "4 matches.", (opts, page.inner_text(STAT)))
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("Enter picks the first match, with several matches and nothing highlighted", page.evaluate("() => compendiumState.base") == "test paints|own black"
              and page.input_value(BASE) == "Own Black (Test Paints)" and page.get_attribute(BASE, "aria-expanded") == "false")
        page.click(BASE)
        page.keyboard.press("Control+A")
        page.keyboard.type("test own b")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("the keyboard still works: the down arrow highlights a line (aria-activedescendant) and Enter picks that one", page.evaluate("() => compendiumState.base") == "test paints|own blue")
        page.click(BASE)
        page.keyboard.press("Control+A")
        page.keyboard.type("zzqq")
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        check("Enter with no match picks nothing and keeps the paint you had", page.evaluate("() => compendiumState.base") == "test paints|own blue" and page.inner_text(STAT).strip() == "No matches.")
        page.keyboard.press("Escape")

        open_lab(page, "history")
        page.click("#cmp-faction-history-pick")
        page.keyboard.type("o")
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("the shared box: in Faction, Enter picks the first of several matches too", page.evaluate("() => compendiumState.faction") == "gloom legion"
              and page.input_value("#cmp-faction-history-pick") == "Gloom Legion")
        open_lab(page, "picker")
        page.click("#cmp-mentor-base")
        page.keyboard.type("test own r")
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
        check("and in the Paint Picker's Base colour box (it opens on a tap, as before)", page.evaluate("() => compendiumState.mentorBase") == "test paints|own brown", page.evaluate("() => compendiumState.mentorBase"))
        hints = page.evaluate("""() => ['mentor-base', 'mentor-second'].map(i => ({ label: document.getElementById('cmp-' + i + '-label').textContent, hint: document.getElementById('cmp-' + i).placeholder }))""")
        check("Paint Picker: the labels stay Base colour and Second colour, and each box has its own short hint (Second colour says it is optional)",
              hints == [{"label": "Base colour", "hint": "Choose your main paint"}, {"label": "Second colour", "hint": "Optional second paint"}]
              and page.locator("#cmp-lab-picker .idea-label", has_text="Part").count() == 1, hints)
        check("the hints are one short phrase each: no second sentence, no em dash", all(len(h["hint"].split()) <= 4 and "—" not in h["hint"] and "." not in h["hint"] for h in hints))

        print("\n--- 3. Primers and inks are never suggested ---")
        # Paints placed exactly on the colours the ideas aim for, so only the rule can keep them out.
        setup = page.evaluate("""() => { const C = MinifolioColour, base = '#2a4d9b', out = {};
            for (const key of ['glow', 'weapon', 'trim']) { const role = COLOUR_ROLES.find(r => r.key === key), h = C.harmonies(base); let slot = 0;
                out[key] = role.picks.map(pk => { const w = colourIdeaWanted(h, role, pk, slot); if (!['dark', 'mid', 'light'].includes(pk)) slot++; return w.hex; }); }
            return out; }""")
        g = setup["glow"]
        extra = [P(30, "Bright Primer", g[0]), P(31, "Glow Ink", g[1]), P(32, "Plain Name", g[2], type="Ink"), P(33, "Ink Wolf Layer", setup["trim"][0], type="Layer"),
                 P(34, "No Type Glow", "#" + format(int(g[0][1:], 16) ^ 1, "06x")), P(35, "Dark Spray", setup["weapon"][1]), P(36, "Weapon Prime", setup["weapon"][0], brand="Pro Acryl")]
        load(page, paints=OWN[:2] + extra, settings=LAB)
        open_lab(page, "ideas")
        page.evaluate("() => { compendiumState.base = 'test paints|own blue'; compendiumState.role = 'glow'; renderColourLab(); }")
        eyes = idea_names(page, "#cmp-lab-ideas")
        check("Eyes or glow: the primer and the inks on the very colours wanted are left out (by name, and by type with a plain name)",
              len(eyes) == 3 and not {"Bright Primer", "Glow Ink", "Plain Name"} & set(eyes), eyes)
        check("a paint with no type and a plain name is allowed: the near twin of the primer is suggested instead", "No Type Glow" in eyes, eyes)
        page.click('#cmp-lab-ideas [data-role="weapon"]')
        page.wait_for_timeout(120)
        weapon = idea_names(page, "#cmp-lab-ideas")
        check("Weapon: no primer spray or PRIME paint either", weapon and not {"Dark Spray", "Weapon Prime"} & set(weapon), weapon)
        page.click('#cmp-lab-ideas [data-role="trim"]')
        page.wait_for_timeout(120)
        check("the type decides when there is one: Ink Wolf Layer (type Layer) can still be suggested", "Ink Wolf Layer" in idea_names(page, "#cmp-lab-ideas"), idea_names(page, "#cmp-lab-ideas"))
        sample = page.evaluate("""() => { const out = []; const bases = ['#2a4d9b', '#b22222', '#808890'];
            for (const b of bases) for (const role of COLOUR_ROLES) for (const i of colourIdeas(null, b, role)) for (const h of fitRows(i.hit)) out.push({ name: h.paint.name, type: h.paint.type || null });
            return out; }""")
        bad = [s for s in sample if primer_or_ink(s)]
        check(f"every part, three base colours, the whole built-in list: no primer or ink in {len(sample)} suggestions", sample and not bad, bad[:4])
        kept = page.evaluate("""() => ({ pal: book.paints.filter(p => ['Bright Primer', 'Glow Ink', 'Dark Spray'].includes(p.name)).length,
            pool: new Set(colourIdeaPool().filter(p => /^(Black Primer|Black Ink|Chaos Black Spray)$/.test(p.name)).map(p => p.name)).size })""")
        check("they stay in Your Palette and in the full paint list (only the suggestions leave them out)", kept == {"pal": 3, "pool": 3}, kept)
        page.click(BASE)
        page.keyboard.press("Control+A")
        page.keyboard.type("black primer")
        opts = page.evaluate("(s) => [...document.querySelectorAll(s + ' [role=option]')].map(o => o.textContent)", LIST)
        check("and you can still choose a primer or an ink in Start from", "Black Primer (Vallejo)" in opts and page.locator("#cmp-start-swatches .start-swatch", has_text="Bright Primer").count() == 1, opts)
        page.keyboard.press("Escape")
        check("with 9 paints owned there is no More paints button", page.locator("#cmp-start-more").count() == 0)

        open_lab(page, "picker")
        page.evaluate("() => { compendiumState.mentorBase = 'test paints|own blue'; compendiumState.mentorSecond = ''; compendiumState.mentorPart = 'eyes'; renderColourLab(); }")
        picks = idea_names(page, "#cmp-lab-picker")
        check("the Paint Picker (Eyes) follows the same rule", len(picks) == 3 and not {"Bright Primer", "Glow Ink", "Plain Name"} & set(picks) and "No Type Glow" in picks, picks)
        ans = page.evaluate("""() => { const first = mentorAsk('eyes for blue armour'); const hex = first.pick && first.pick.hex; if (!hex) return null;
            const role = mentorRole(first.pick.part), h = MinifolioColour.harmonies(hex); let slot = 0;
            const want = role.picks.map(pk => { const w = colourIdeaWanted(h, role, pk, slot); if (!['dark', 'mid', 'light'].includes(pk)) slot++; return w.hex; });
            book.paints.push({ id: 90, brand: 'Test Paints', name: 'Mentor Primer', colour: want[0], status: 'owned' }, { id: 91, brand: 'Test Paints', name: 'Mentor Ink', colour: want[1], status: 'owned' });
            const again = mentorAsk('eyes for blue armour').answer; book.paints.splice(-2, 2);
            return { kind: again.kind, picks: (again.picks || []).map(x => x.paint.name), blends: (again.picks || []).filter(x => x.blend).map(x => [x.blend.a.name, x.blend.b.name]) }; }""")
        check("Mentor's colour answers too: a primer and an ink of yours on the wanted colours are not picked (nor used in a blend)",
              ans and ans["kind"] == "colour" and len(ans["picks"]) == 3 and not {"Mentor Primer", "Mentor Ink"} & set(ans["picks"] + [n for b in ans["blends"] for n in b]), ans)

        print("\n--- 4. No paints of your own ---")
        load(page, paints=[], settings=LAB)
        open_lab(page, "ideas")
        page.click(BASE)
        page.wait_for_timeout(100)
        check("with no paints of your own: no swatches, no More paints, no extra line, and the box opens its list on a tap as before",
              page.locator("#cmp-start-swatches, #cmp-start-more").count() == 0 and page.get_attribute(BASE, "aria-expanded") == "true"
              and page.locator("#cmp-lab-ideas p.hint:not(.combo-status)").count() == 1, (page.get_attribute(BASE, "aria-expanded"), page.locator("#cmp-lab-ideas p.hint").all_inner_texts()))
        page.keyboard.press("Escape")

        print("\n--- 5. Phone sizes, dark and light ---")
        load(page, paints=OWN, recipes=RECIPES, settings=LAB)
        for (w, h), scheme in (((390, 844), "dark"), ((360, 640), "light"), ((320, 640), "dark"), ((320, 640), "light")):
            page.set_viewport_size({"width": w, "height": h})   # one page, no reloads: the size and the appearance change in place
            page.evaluate("(s) => { settings.appearance = s; setAppearanceMark(); applyPalette(settings.palette); openColourLab('ideas'); }", scheme)
            page.wait_for_timeout(100)
            page.evaluate("() => document.fonts.ready")
            fit = page.evaluate("""() => { const box = document.getElementById('cmp-start-swatches').getBoundingClientRect();
                const items = [...document.querySelectorAll('#cmp-start-swatches > button')];
                const inside = items.every(b => { const r = b.getBoundingClientRect(); return r.left >= box.left - 1 && r.right <= box.right + 1 && r.height >= 44 && r.width >= 44; });
                const names = [...document.querySelectorAll('#cmp-start-swatches .start-swatch')].every(b => { const r = b.getBoundingClientRect(), n = b.querySelector('.start-swatch-name').getBoundingClientRect();
                    return n.right <= r.right + 1 && n.left >= r.left - 1 && n.bottom <= r.bottom + 1; });
                const lines = new Set(items.map(b => Math.round(b.getBoundingClientRect().top))).size;
                return { inside, names, lines }; }""")
            check(f"{w}x{h} {scheme}: no sideways scroll; the swatches wrap onto lines, every one is 44 px and inside the card, and the long name stays on its swatch",
                  no_sideways(page) and fit["inside"] and fit["names"] and fit["lines"] >= 4 and page.evaluate("() => document.documentElement.dataset.m") == scheme, fit)
        check("no page errors or pop-ups", not errors, errors)
        browser.close()

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()
