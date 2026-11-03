"""Small helpers shared by several tests."""

def node_command():
    """T6: the Node.js program the .js checks run in (test_colour_engine, test_v101_mentor_engine, test_v105_mentor_words).
    `node` when it is installed; otherwise the copy of Node that comes inside Playwright for Python, which every test needs anyway.
    So those checks also run on a computer without Node.js installed, instead of always failing there."""
    import os, shutil
    found = shutil.which("node")
    if found:
        return found
    try:
        import playwright
        bundled = os.path.join(os.path.dirname(playwright.__file__), "driver", "node.exe" if os.name == "nt" else "node")
        if os.path.exists(bundled):
            return bundled
    except ImportError:
        pass
    return "node"


def speed_factor():
    """T6: how much slower this machine is than the one the time budget was recorded on (1 to 3), as measured by tests/run_all.py's
    speed check at the start of the run and handed over as SOG_SPEED_FACTOR. A file run on its own, without the runner, gets 1.
    For the few checks that time the app in milliseconds: the limits were set on the reference machine, so a machine measured
    2.3 times slower, with other test files running beside it, gets 2.3 times the limit. A real slowdown still fails."""
    import os
    try:
        return max(1.0, min(3.0, float(os.environ.get("SOG_SPEED_FACTOR", "1"))))
    except ValueError:
        return 1.0

def open_unit_card(page, card):
    """MC1 (v130): a unit card starts closed (compact: name, game, army and stage only). Older tests that tap its stepper, its recipe
    buttons or its Details button open the card first with this. `card` is a CSS selector for the li.unit; nothing happens if it is
    already open. Only one card is open at a time, so opening this one closes any other."""
    page.evaluate("(sel) => { const c = document.querySelector(sel); if (c && c.classList.contains('compact')) c.querySelector('.info').click(); }", card)
    page.wait_for_selector(card + ":not(.compact) .details-toggle", state="attached")

def open_unit_details(page, card):
    """MC1 (v130): before MC1 a tap on a unit's name opened its Details; now it opens the card. This opens the card, then its
    Details (if they are not open already). `card` is a CSS selector for the li.unit."""
    open_unit_card(page, card)
    if page.get_attribute(card + " .details-toggle", "aria-expanded") != "true":
        page.click(card + " .details-toggle")


def click_card_chip(page, selector):
    """Click a recipe or tip chip in the recipe editor's Colour ideas card.
    X8d (v106): that card shows only the first 12 chips of a long list, with a Show all button under it. A chip past
    the first 12 is hidden until Show all is pressed, so press it first when the chip is hidden, then click."""
    if not page.locator(selector).is_visible():
        more = page.locator(selector).locator("xpath=ancestor::div[contains(@class,'detail-recipes') or contains(@class,'basing-tips')][1]").locator(".chips-more")
        if more.count() and more.get_attribute("aria-expanded") == "false":
            more.click()
    page.click(selector)


# The three Mentor sample tips were removed from mentor-tips.js (chunk A1). Older tests that need a tip to show use this:
# call use_sample_tips(context) before opening pages and the page gets the file with the old sample tips put back, in memory only.
SAMPLE_TIPS_JS = """const MENTOR_TIPS = [
  { key: "sample-armour", sample: true, part: "armour", colour: "a cold blue", technique: "Layer",
    advice: "Sample tip. It only shows the format. A real tip from George's notes goes here.",
    colours: [{ look: "a deep blue", hex: "#1f3a66" }, { look: "a light blue", hex: "#6f93c9" }] },
  { key: "sample-eyes", sample: true, part: "eyes", colour: "a warm red", technique: "Glaze",
    advice: "Sample tip. It only shows the format. A real tip from George's notes goes here.",
    colours: [{ look: "a bright red", hex: "#c8321e" }] },
  { key: "sample-base", sample: true, part: "base", colour: "a dry brown", technique: "Drybrush",
    advice: "Sample tip. It only shows the format and the optional credit.",
    colours: [{ look: "a mid brown", hex: "#7a5c3a" }, { look: "a pale sand", hex: "#cdbd94" }],
    credit: { name: "Sample creator", url: "https://example.com/" } },
];"""

def use_sample_tips(context):
    import os
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mentor-tips.js"), encoding="utf-8").read()
    body = src.replace("const MENTOR_TIPS = [\n];", SAMPLE_TIPS_JS)
    context.route("**/mentor-tips.js*", lambda r: r.fulfill(status=200, content_type="application/javascript", body=body))
