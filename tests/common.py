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
