"""X1 (v96): the colour parts of the Compendium moved to Painting > Colour Lab. Older tests that used them go to the new place through
these helpers. Section names are the old fold names too: wheel, ideas, history, starter (now "Colour plans"), mentor (now "Picker")."""
from launch_helpers import quiet

SECTION = {"wheel": "wheel", "ideas": "ideas", "history": "history", "starter": "plans", "mentor": "picker",
           "plans": "plans", "picker": "picker"}

def open_lab(page, section="wheel"):
    """Painting > Colour Lab with one section open (the old fold name or the new key)."""
    key = SECTION[section]
    if page.evaluate("() => document.activeElement && document.activeElement.blur && document.activeElement.blur()") is None:
        pass
    if page.evaluate("() => settings.tab !== 'recipes' || settings.recipeView !== 'colourlab'"):
        page.click('nav button[data-tab="recipes"]')
        quiet(page)
        page.click('#recipe-seg button[data-view="colourlab"]')
        quiet(page)
    if page.get_attribute(f'#lab-seg [data-lab="{key}"]', "aria-selected") != "true":
        page.click(f'#lab-seg [data-lab="{key}"]')
        quiet(page)
    page.wait_for_selector(f"#cmp-lab-{key}")


# ---- The old all-in-one Compendium page, for the older tests ----
# Before v96 the Compendium showed the colour wheel and five fold-outs on ONE page, and about thirty older test files read that page (their
# checks are about the building blocks: the rows, tags, ids and picks, not about where the page puts them). v96 moved those parts into
# Painting > Colour Lab (one section at a time). So those files can still run their checks unchanged, go_compendium() puts the old
# arrangement back for the test only: it replaces renderGuides in the page with the old one, built from the SAME app functions
# (appendColourWheel, libraryParts, buildMentor, buildCompendiumIdeas, foldSection, ...). Nothing in the app is changed by this. The new arrangement
# is tested in test_v96_colour_lab.py and in the few files that test navigation (v69, v71, v73, v88 to v94).
_LEGACY = """() => {
  if (!document.getElementById('legacy-compendium-style')) {   // X2: these two wide-screen rules were the app's own until the Compendium tab went; only this copy uses them
    const st = document.createElement('style'); st.id = 'legacy-compendium-style';
    st.textContent = '.compendium-split { display: grid; gap: 12px; } @media (min-width: 900px) { .compendium-split .wheel-block { border-bottom: 0; padding-bottom: 0; } .compendium-split > .layout-main { align-self: start; position: sticky; top: 84px; max-height: calc(100vh - 100px); overflow-y: auto; } }';
    document.head.appendChild(st);
  }
  window.renderGuides = function (focusSelector) {   // X2: the app's renderer is now renderGuides (it was renderGuides)
    const body = document.getElementById('compendium-body');
    if (!body) return;
    body.replaceChildren();
    const say = (text, id) => { const p = document.createElement('p'); p.className = 'hint'; if (id) p.id = compendiumId(id); p.textContent = text; body.appendChild(p); return p; };
    const door = compendiumDoor();
    const redraw = (selector) => renderGuides(selector);
    const intro = say("A colour wheel (tap a colour to open its groups), Ask the Mentor, colour ideas, colour plans, detail recipes and basing tips, without needing a recipe. Tap a heading to open it, and type in a search box to find things fast. Use Copy as text to keep anything, or Save into a new recipe\\u2026 to start a recipe from colour ideas, colour plans, detail recipes and basing tips.", 'intro');
    appendIdeasFocus(body, door, redraw);
    const split = document.createElement('div'); split.className = 'compendium-split layout-split layout-detail-wide';
    const left = document.createElement('div'); left.className = 'layout-main';
    const right = document.createElement('div'); right.className = 'layout-side compendium-folds';
    split.append(left, right); body.appendChild(split);
    appendColourWheel(left, door, redraw);
    const parts = libraryParts(door, redraw);
    const fold = (key, label, make) => { if (make) right.appendChild(foldSection(door, key, label, make)); };
    fold('mentor', 'Ask the Mentor', () => buildMentor(door, redraw));
    fold('ideas', 'Colour ideas', () => { const out = document.createDocumentFragment(); buildCompendiumIdeas(out, door, redraw); return out; });
    fold('history', "Colours you've used", parts.history && (() => dropTitle(parts.history(), "Colours you've used on this faction before.")));
    fold('starter', 'Colour plans', parts.starter && (() => dropTitle(parts.starter())));
    fold('detail', 'Detail recipes', parts.detail && (() => dropTitle(parts.detail())));
    fold('basing', 'Basing tips', parts.basing && (() => dropTitle(parts.basing())));
    right.appendChild(say('Ideas use paints you own first. Colours on screen are a guide.', 'foot'));
    body.insertBefore(buildMoreInfo([intro], { state: infoState(door, 'page'), id: compendiumId('page-info-panel'), label: 'the Compendium' }), body.firstChild);
    if (focusSelector) { const target = body.querySelector(focusSelector); if (target) target.focus(); }
  };
}"""

def legacy_compendium(page):
    page.evaluate(_LEGACY)

def go_compendium(page):
    """Tap the fourth segment (Tools and Settings > Guides; X2), with the old all-in-one page installed first."""
    legacy_compendium(page)
    page.click('nav button[data-tab="guides"]')
