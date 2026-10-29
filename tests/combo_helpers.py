"""Test helpers for the Compendium's search boxes (v37 part 2). Not a test file itself (run_all.py only runs test_*.py).

"Start from" and "Faction" used to be drop-down lists (<select>). They are now a box you type in with a list under it (a combobox).
These helpers choose from them the way a keyboard user does: type some of the name, press the down arrow until the wanted line is
highlighted, press Enter. That also leaves the focus in the box, as the old drop-down did."""
from launch_helpers import quiet

PICK_INDEX_JS = """([sel, text, value]) => {
    const list = document.getElementById(sel.slice(1) + '-list');
    const items = [...list.querySelectorAll('[role="option"]')];
    return items.findIndex(li => (value !== null ? li.dataset.value === value : li.textContent === text)); }"""

PAINT_TEXT_JS = """(key) => { const c = compendiumBaseChoices(); const all = [...c.own, ...c.other, ...c.brands.flatMap(b => b.list)];
    const p = all.find(x => c.key(x) === key); return p ? (p.brand ? `${p.name} (${p.brand})` : p.name) : null; }"""


def pick_combo(page, input_sel, text=None, value=None, index=None, wait=150):
    """Choose one line from a search box. Give the line's text, or (for Start from) the paint's key as `value`, or `index` (1 = the first line,
    like the old drop-down where line 0 was the "Choose..." line)."""
    if index is not None:
        page.click(input_sel)
        for _ in range(index):
            page.keyboard.press("ArrowDown")
    else:
        if text is None:
            text = page.evaluate(PAINT_TEXT_JS, value)
        page.fill(input_sel, text)
        at = page.evaluate(PICK_INDEX_JS, [input_sel, text, value])
        if at < 0:
            raise AssertionError(f"{text!r} is not in the list of {input_sel}")
        for _ in range(at + 1):
            page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    quiet(page) if wait <= 300 else page.wait_for_timeout(wait)
