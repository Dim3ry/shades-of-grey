"""v54 helper for the older tests.

Since v53 and v54, five Settings cards (Stages, Faction colours, Paint brands, Import, Your data) fold shut every time the app opens.
Older tests were written when those cards were always open, and they work with what is inside them (the stage list, Import CSV, Delete all
units, Restore example recipes...). They are not about the folding, so each of them calls open_cards_on_load(page) once after it makes its
page: the cards are then opened whenever the app loads, and the test goes on as it always did. The folding itself is tested in test_v53.py
and test_v54.py, which do not use this."""

INIT = """() => {
  const openAll = () => document.querySelectorAll('.card-fold-button[aria-expanded="false"]').forEach(b => b.click());
  document.addEventListener('DOMContentLoaded', openAll);
  window.addEventListener('load', () => { openAll(); setTimeout(openAll, 50); });
}"""

def open_cards_on_load(page):
    page.add_init_script("(" + INIT + ")();")
