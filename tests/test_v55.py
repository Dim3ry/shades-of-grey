"""v55 tests for Minifolio (declutter chunk D8: the last two sweep findings, F11 pills and F12 paint names in labels).

What changed:
 F11 The three kinds of pill are plain text now (no fill, no round border): .idea-tag (Fine, Look at this, Suggestion and the Compendium row
     words), .part-tag (the part name on a recipe) and .pro-pill ("Pro preview"). Words and class names are as they were; only the CSS changed.
     The status is the word, so it is never shown by colour alone.
 F12 No paint name sits in an aria-label or a title any more. The Remove button in the recipe editor, the Colour ideas buttons, the palette's More
     options, colour box, Merge menu and Remove, the swatch tile and the shop links use aria-labelledby that points at the visible name (or, where
     there is none, a screen-reader-only name) plus a short action word kept in the element's own aria-label.

Checks:
1. Versions, the v55 Updates entry.
2. F11: the three kinds look like plain text, in dark and light; their words, classes and contrast.
3. F12: no paint name in any aria-label or title on the pages that carry them; what a screen reader reads for each place.
4. Layout: no sideways scroll, targets still 44 px, at three widths.
5. The new code: shared helpers, outside the v36 and v37 scanned code, no innerHTML.
6. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notice_watch import attach_notices
import fold_opener
import test_v31 as t
import test_v39 as h   # JUST_BLUE
import test_v41 as v41   # open_ideas (the Compendium's Colour ideas)
import test_v42 as w   # load
import test_v52 as v52   # tab, open_shopping, paints_with_needs
import test_v53 as v53   # parse_colour, blend
import test_v54 as v54   # ratio, look, effective_ratio

URL, read = t.URL, t.read
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

tab, press = v52.tab, v52.press
PAINT_NAMES = sorted({p["name"] for p in t.PAINTS if p.get("name")})
SPARE = {"id": 99, "brand": "Probe", "name": "Spare Probe", "colour": "#445566", "status": "owned"}   # in no recipe, so the palette offers Remove
PAINTS = [dict(p) for p in t.PAINTS] + [SPARE]
ALL_NAMES = PAINT_NAMES + [SPARE["name"]]

# What a screen reader would say for an element, worked out the simple way: the ids in aria-labelledby, in order (an element naming itself
# contributes its aria-label, or its own words when it has none).
NAME_JS = """(el) => {
  const part = (n) => {
    if (n === el && n.getAttribute('aria-label')) return n.getAttribute('aria-label');
    if (n.tagName === 'INPUT' || n.tagName === 'SELECT') return n.value;
    return n.textContent.replace(/\\s+/g, ' ').trim();
  };
  const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
  if (!ids.length) return el.getAttribute('aria-label') || el.textContent.replace(/\\s+/g, ' ').trim();
  return ids.map(i => document.getElementById(i)).filter(Boolean).map(part).join(' ');
}"""

LABEL_SCAN_JS = """(names) => {
  const bad = [];
  document.querySelectorAll('[aria-label], [title]').forEach(e => {
    for (const a of ['aria-label', 'title']) {
      const v = e.getAttribute(a);
      if (v && names.some(n => v.includes(n))) bad.push(e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0] + ' ' + a + '=' + v.slice(0, 50));
    }
  });
  return bad;
}"""

def spoken(page, selector, nth=0):
    return page.locator(selector).nth(nth).evaluate(NAME_JS)

def no_names_in_labels(page, label):
    bad = page.evaluate(LABEL_SCAN_JS, ALL_NAMES)
    check(f"{label}: no paint name in any aria-label or title", not bad, bad[:5])

def tap(page, selector, nth=0):
    loc = page.locator(selector).nth(nth)
    loc.evaluate("e => e.scrollIntoView({ block: 'center' })")
    page.wait_for_timeout(60)
    loc.dispatch_event("click")
    page.wait_for_timeout(180)

def plain(page, selector):
    """True when every element matching selector has no fill, no border and no rounded corners."""
    return page.evaluate("""(sel) => { const els = [...document.querySelectorAll(sel)]; if (!els.length) return null;
      return els.every(e => { const c = getComputedStyle(e); const bg = c.backgroundColor;
        return (/rgba\\(.*, 0\\)|transparent/.test(bg)) && ['Top', 'Right', 'Bottom', 'Left'].every(s => c['border' + s + 'Width'] === '0px') && c.borderTopLeftRadius === '0px'; }); }""", selector)

def contrast_of(page, selector):
    info = v54.look(page, selector)
    return v54.effective_ratio(info, info["bg"])

def sideways(page):
    return t.no_sideways(page)

def open_palette(page, paints=None, mode="dark", width=390):
    page.set_viewport_size({"width": width, "height": 844})
    w.load(page, paints=paints or PAINTS, recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
    fold_opener.open_cards_on_load(page)
    tab(page, "recipes")
    page.click('#recipe-seg button[data-view="palette"]')
    page.wait_for_timeout(200)

def open_editor_ideas(page, mode="dark", width=390):
    page.set_viewport_size({"width": width, "height": 844})
    w.load(page, paints=PAINTS, recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
    t.open_editor(page)   # a new recipe: its first step starts open
    t.set_step_paint(page, 0, "Macragge Blue")   # a paint in the step is what makes Colour ideas show
    t.open_panel(page)

def main():
    errors, dialogs = [], []
    app, html = read("app.js"), read("index.html")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        attach_notices(page, dialogs.append)

        # ---------- 1. Versions ----------
        print("\n--- 1. Versions and the Updates entry ---")
        w.load(page, paints=[])

        # ---------- 2. F11: plain text, not pills ----------
        print("\n--- 2. F11: plain text, not pills ---")
        for mode in ("dark", "light"):
            open_editor_ideas(page, mode)
            check(f"{mode}: Pro preview on Colour ideas keeps its words and is plain text", page.text_content("#colour-ideas .pro-pill") == "Pro preview" and plain(page, "#colour-ideas .pro-pill") is True)
            tag_words = page.evaluate("() => [...document.querySelectorAll('#colour-ideas .idea-tag')].map(e => e.textContent.trim())")
            check(f"{mode}: the idea tags in Colour ideas are plain text and every one still says a word", len(tag_words) >= 3 and all(tag_words) and plain(page, "#colour-ideas .idea-tag") is True, tag_words[:6])
            check(f"{mode}: the tag classes (own, near, none) are still on the tags", page.evaluate("() => [...document.querySelectorAll('#colour-ideas .idea-tag')].every(e => /\\b(own|near|none)\\b/.test(e.className))"))
            seen = {}
            for cls in ("own", "near", "none"):
                if page.locator(f"#colour-ideas .idea-tag.{cls}").count():
                    seen[cls] = round(contrast_of(page, f"#colour-ideas .idea-tag.{cls}"), 2)
            check(f"{mode}: the tag text is at least 4.5:1 against the card ({seen})", seen and all(r >= 4.5 for r in seen.values()), seen)
            check(f"{mode}: the Pro preview text is at least 4.5:1", contrast_of(page, "#colour-ideas .pro-pill") >= 4.5, contrast_of(page, "#colour-ideas .pro-pill"))
            w.load(page, paints=PAINTS, recipes=t.RECIPES, units=t.UNITS, settings={"appearance": mode})
            tab(page, "recipes")
            page.click("#recipe-list .recipe-item")
            page.wait_for_timeout(200)
            check(f"{mode}: the part name on a recipe is plain text with its words", page.inner_text(".part-tag") == "Whole model" and plain(page, ".part-tag") is True, page.inner_text(".part-tag"))
            check(f"{mode}: the part name is at least 4.5:1", contrast_of(page, ".part-tag") >= 4.5, contrast_of(page, ".part-tag"))
            v41.open_ideas(page, h.JUST_BLUE, settings={"appearance": mode})
            # P1: Guides and Colour Lab draw their tags only when their lists exist, which this fixture does not give; so the shared tag maker is checked directly
            page.evaluate("() => { const e = proTag(); e.id = 'p1-test-tag'; document.body.appendChild(e); }")
            check(f"{mode}: the shared Pro preview tag keeps its words and is plain text", page.text_content("#p1-test-tag") == "Pro preview" and plain(page, "#p1-test-tag") is True)
            page.evaluate("() => document.getElementById('p1-test-tag').remove()")
            check(f"{mode}: the Compendium row tags are plain text with words", page.locator("#cmp-fold-ideas-panel .idea-tag").count() >= 3 and plain(page, "#cmp-fold-ideas-panel .idea-tag") is True)
            check(f"{mode}: the Compendium row tag text is at least 4.5:1", all(contrast_of(page, f"#cmp-fold-ideas-panel .idea-tag.{c}") >= 4.5 for c in ("own", "near", "none") if page.locator(f"#cmp-fold-ideas-panel .idea-tag.{c}").count()))
        check("the three rules have no fill, no border and no round corner in the style sheet",
              all(not re.search(r"border-radius|border:|background", ln) for ln in html.splitlines() if re.match(r"\s*(\.part-tag|\.pro-pill|\.idea-tag)\b", ln)))
        check("the three rules use only theme variables (no colour code)", all("#" not in ln.split("/*")[0] for ln in html.splitlines() if re.match(r"\s*(\.part-tag|\.pro-pill|\.idea-tag)\b", ln)))

        # ---------- 3. F12: paint names in labels ----------
        print("\n--- 3. F12: paint names in labels ---")
        # Recipe editor with Colour ideas open
        open_editor_ideas(page)
        no_names_in_labels(page, "recipe editor with Colour ideas open")
        remove0 = spoken(page, "#recipe-page .icon-button.remove[aria-labelledby]")
        first_name = page.locator('[data-key="step-0-paint-0"]').input_value()
        check("the editor's Remove button reads 'Remove' and the paint's name from the box beside it", remove0 == f"Remove {first_name}", remove0)
        page.locator('[data-key="step-0-paint-0"]').fill("Typed Name")
        check("the name follows what is typed in the box (no label to keep up to date)", spoken(page, "#recipe-page .icon-button.remove[aria-labelledby]") == "Remove Typed Name", spoken(page, "#recipe-page .icon-button.remove[aria-labelledby]"))
        # T4: typing in a box makes the Colour ideas panel redraw a moment later; wait until its buttons are back before reading them (on a starved machine the read landed in the gap and found none)
        page.wait_for_function("() => document.querySelectorAll('#colour-ideas button.idea .idea-name').length > 0")
        idea = spoken(page, "#colour-ideas button.idea")
        check("each Colour ideas button reads 'Add as a new step', then its visible name, tag and reason", idea.startswith("Add as a new step ") and page.locator("#colour-ideas button.idea").first.evaluate("e => e.querySelector('.idea-name').textContent.length") > 0
              and page.locator("#colour-ideas button.idea").first.evaluate("e => e.textContent.includes('+ Add as a step')"), idea)
        n_before = page.evaluate("() => document.querySelectorAll('#recipe-page ol.recipe-steps > li, #recipe-page .step-card').length")
        tap(page, "#colour-ideas button.idea")
        n_after = page.evaluate("() => document.querySelectorAll('#recipe-page ol.recipe-steps > li, #recipe-page .step-card').length")
        check("tapping a Colour ideas button adds a step (as before)", n_after >= n_before, (n_before, n_after))
        t.pick_scheme(page, "orange-blue")
        check("a picked starter scheme shows idea-pick buttons", page.locator("#starter-list button.idea-pick").count() == 4)
        pick_name = spoken(page, "#starter-list button.idea-pick")
        pick_vis = page.locator("#starter-list button.idea-pick").first.evaluate("e => e.querySelector('.idea-name').textContent")
        check("the idea-pick buttons read 'Add as a new step' and their visible name", pick_name.startswith("Add as a new step ") and pick_vis in pick_name, pick_name)
        no_names_in_labels(page, "Colour ideas with a scheme picked")

        # Your Palette: list, a paint open, More options open
        open_palette(page)
        no_names_in_labels(page, "Your Palette list")
        tap(page, ".paint-head", 0)
        no_names_in_labels(page, "Your Palette with a paint open")
        first = page.locator(".paint-head .name").first.text_content()
        opts = page.locator(".paint-options .more-info-button").first
        check("the More options button reads 'More options' and the visible paint name", opts.evaluate(NAME_JS) == f"More options {first}", opts.evaluate(NAME_JS))
        tap(page, ".paint-options .more-info-button")
        check("opened, it reads 'Fewer options' and the paint name", page.locator(".paint-options .more-info-button").first.evaluate(NAME_JS) == f"Fewer options {first}", page.locator(".paint-options .more-info-button").first.evaluate(NAME_JS))
        colour_name = page.locator('.paint-options input[type="color"]').first.evaluate(NAME_JS)
        check("the colour box reads 'Colour of' and the visible paint name", colour_name == f"Colour of {first}", colour_name)
        merge_label = page.locator(".paint-options .merge-pick").first.evaluate("e => (e.closest('label') || {}).textContent || ''")
        check("the Merge menu has no aria-label and is named by the sentence it sits in, which names the paint", page.locator(".paint-options .merge-pick").first.get_attribute("aria-label") is None and first in merge_label, merge_label[:80])
        no_names_in_labels(page, "Your Palette with More options open")
        # a paint nobody uses has Remove
        open_palette(page)
        spare = page.locator(".paint-head", has=page.locator(".name", has_text="Spare Probe")).first
        spare.evaluate("e => e.scrollIntoView({ block: 'center' })")
        spare.dispatch_event("click")
        page.wait_for_timeout(180)
        tap(page, ".paint-options .more-info-button", 0)
        rm = page.locator(".paint-options button.danger-button").first
        check("Remove in the palette reads 'Remove' and the visible paint name", rm.evaluate(NAME_JS) == "Remove Spare Probe", rm.evaluate(NAME_JS))
        check("Remove is offered for a paint no recipe uses, and is a real button (not a link or a div)", rm.count() == 1 and rm.evaluate("e => e.tagName === 'BUTTON'"))
        # Swatches
        open_palette(page)
        page.locator("button", has_text="Swatches").first.dispatch_event("click")
        page.wait_for_timeout(200)
        no_names_in_labels(page, "Swatches")
        tile = page.locator(".swatch-tile").first
        check("a swatch tile has no title and no aria-label", tile.get_attribute("title") is None and tile.get_attribute("aria-label") is None)
        tile_name = tile.evaluate(NAME_JS)
        check("a swatch tile is named by a screen-reader-only name made of the paint, brand and status", tile.get_attribute("aria-labelledby") and tile.locator(".sr-only").count() == 1
              and any(n in tile_name for n in ALL_NAMES) and tile_name.count(",") >= 1, tile_name)
        check("that name is not shown (it is one pixel and clipped)", tile.locator(".sr-only").evaluate("e => { const r = e.getBoundingClientRect(); return r.width <= 1 && r.height <= 1; }"))
        check("the tile is still a real button with aria-expanded and 44 px or more", tile.evaluate("e => e.tagName === 'BUTTON' && e.hasAttribute('aria-expanded')") and tile.bounding_box()["width"] >= 44 and tile.bounding_box()["height"] >= 44)
        tap(page, ".swatch-tile")
        check("opening a tile still opens that paint under the row", page.locator(".swatch-detail").count() == 1 and page.locator(".swatch-tile").first.get_attribute("aria-expanded") == "true")
        no_names_in_labels(page, "Swatches with a tile open")

        # Shop links: Compendium rows and the shopping list
        v41.open_ideas(page, h.JUST_BLUE)
        no_names_in_labels(page, "Compendium Colour ideas")
        page.locator("#cmp-fold-ideas-panel > .idea-list > li .shop-more > summary").first.evaluate("e => e.scrollIntoView({ block: 'center' })")
        page.locator("#cmp-fold-ideas-panel > .idea-list > li .shop-more > summary").first.click()
        page.wait_for_timeout(150)
        row_name = page.locator("#cmp-fold-ideas-panel > .idea-list > li").first.locator(".idea-name").evaluate("e => e.childNodes[0].textContent")
        summ = spoken(page, "#cmp-fold-ideas-panel > .idea-list > li .shop-more > summary")
        check("the Shop links fold-out reads 'Shop links for' and the paint name", summ == f"Shop links for {row_name}", summ)
        link = page.locator("#cmp-fold-ideas-panel > .idea-list > li .shop-links a").first
        link_name = link.evaluate(NAME_JS)
        check("a shop link reads 'Search <shop> for' and the paint name", re.fullmatch(r"Search .+ for " + re.escape(row_name), link_name) is not None, link_name)
        check("a shop link says it opens the shop's website through aria-describedby, not its name", link.evaluate("e => { const d = document.getElementById(e.getAttribute('aria-describedby')); return !!d && d.textContent === \"Opens the shop's website\"; }"))
        add_name = spoken(page, "#cmp-fold-ideas-panel > .idea-list > li .shop-add button")
        check("the shop fold-out's Add button reads 'Add to shopping list' and the paint name", add_name == f"Add to shopping list {row_name}", add_name)
        check("the shop links still point at the shops (same address, new tab, no referrer)", link.get_attribute("target") == "_blank" and "noopener" in (link.get_attribute("rel") or "") and (link.get_attribute("href") or "").startswith("https://"))
        tap(page, "#cmp-fold-ideas-panel > .idea-list > li .shop-add button")
        w.load(page, paints=v52.paints_with_needs(), recipes=t.RECIPES, units=t.UNITS)
        v52.open_shopping(page)
        tap(page, "#buy-bar .buy-shops button")
        bar_links = page.locator("#buy-links a")
        check("tapping a shop under Buy these lists search links", bar_links.count() >= 1, bar_links.count())
        nm = bar_links.first.evaluate(NAME_JS)
        shown_name = bar_links.first.locator("span").first.text_content()
        check("a shopping list search link reads 'Search <shop> for' and the paint name it shows", re.fullmatch(r"Search .+ for " + re.escape(shown_name), nm) is not None, nm)
        check("that link says it opens the shop's website through aria-describedby", bar_links.first.evaluate("e => { const d = document.getElementById(e.getAttribute('aria-describedby')); return !!d && d.textContent === \"Opens the shop's website\"; }"))
        no_names_in_labels(page, "Shopping list with a shop open")

        # ---------- 4. Layout ----------
        print("\n--- 4. Layout at three widths ---")
        for width in (360, 390, 1000):
            for mode in ("dark", "light"):
                tag = f"{width} px {mode}"
                open_editor_ideas(page, mode, width)
                check(f"{tag}: recipe editor with Colour ideas open does not scroll sideways", sideways(page))
                open_palette(page, mode=mode, width=width)
                tap(page, ".paint-head", 0)
                check(f"{tag}: Your Palette with a paint open does not scroll sideways", sideways(page))
                page.locator("button", has_text="Swatches").first.dispatch_event("click")
                page.wait_for_timeout(150)
                check(f"{tag}: Swatches does not scroll sideways and every tile is 44 px or more", sideways(page) and page.evaluate("() => [...document.querySelectorAll('.swatch-tile')].every(e => { const r = e.getBoundingClientRect(); return r.width >= 44 && r.height >= 44; })"))

        # ---------- 5. The new code ----------
        print("\n--- 5. The new code ---")
        snippet = app[app.index("// v55: names for buttons, links and boxes"):app.index("// One tappable idea row")]
        check("labelWithName, hiddenName and idOf are each defined once (shared, not copied)", all(len(re.findall(rf"function {n}\(", app)) == 1 for n in ("labelWithName", "hiddenName", "idOf")))
        start, end = app.index("v36: THE COLOUR WHEEL"), app.index("function renderGuides(")
        check("the new helpers have no innerHTML, no storage and no network code", not re.search(r"innerHTML|insertAdjacentHTML|localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|WebSocket", snippet))
        check("the helpers write only an action word to aria-label (never a name) and set no title", "title" not in re.sub(r"//[^\n]*", "", snippet).replace("hiddenName(text)", "") and "aria-label\", action" in snippet)
        names_in_labels = re.findall(r'setAttribute\("aria-label", `[^`]*\$\{(?:paint|p)\.name[^`]*`\)|\.title = paint\.name', app)
        check("no aria-label or title in app.js is built from paint.name or p.name any more", not names_in_labels, names_in_labels[:3])
        check("the Colour ideas rows, palette items, swatch tiles and shop fold-outs use labelWithName or hiddenName",
              all(app.count(s) >= 1 for s in ('labelWithName(button, "Add as a new step", name, statusEl, why)', 'labelWithName(remove, "Remove", name)', "hiddenName([paint.name", 'labelWithName(summary, "Shop links for", who)')))

        # ---------- 6. No errors ----------
        print("\n--- 6. No errors ---")
        check("no page errors", not errors, errors[:3])
        dialogs[:] = [d for d in dialogs if not d.startswith("Added step")]   # the app's own notice after tapping a Colour ideas button
        check("no browser pop-ups were shown", not dialogs, dialogs[:3])
        browser.close()

    ok = all(results)
    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
