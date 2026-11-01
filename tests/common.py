"""Small helpers shared by several tests."""

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
