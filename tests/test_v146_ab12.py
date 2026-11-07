"""Chunk AB12 tests for Minifolio: Mentor's answer shape (AT-39) and wrong-question answers (AT-40). New behaviour only.

1. Engine, on the page: no answer ends with "Also see"; a good fit (band "clear") from a guide gives two or three lines from that guide
   and one source; "how do I paint X" ranks a technique entry first (and a colour word in it goes to the entries, not the colour rule);
   a best title without the question's main noun gives two or three "Did you mean" choices and no answer; the gold line's new wording.
2. The window: the good fit shows its lines and one "Read the guide" link that opens the guide; the choices show as chips under
   "Did you mean", and a tapped choice asks that title and is answered plainly.
3. Layout at 390x844 dark and 360x640 light: chips 44 px or more, the link 44 px, no sideways scroll.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import os, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v24 as t

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

ASK = """(qs) => qs.map((q) => { const a = MinifolioMentor.mentorAnswer(q, { index: knowledgeIndex(), paints: [], tips: MENTOR_TIPS });
    const e = a.sources && a.sources[0] ? knowledgeIndex().get(a.sources[0].key) : null;
    return { q, kind: a.kind, band: a.band || '', lead: a.lead, more: a.more || [], readGuide: !!a.readGuide, choices: (a.choices || []).map(c => c.text),
             keys: (a.sources || []).map(s => s.key), cat: e ? e.category + ':' + e.kind : '', body: e && e.body ? e.body.join(' ') : '' }; })"""

# a sample of questions that gave "Also see" before AB12, plus the hand-checked ones from the chunk
SAMPLE = ["how do I paint a wash", "how do I thin my paints", "how do I paint eyes", "how do I fix tide marks", "wet palette", "highlite",
          "my paint is too thick", "how do I paint rust", "my wash went chalky", "how do I paint gold", "how do I paint metal"]

def open_it(page):
    page.click("#mentor-button")
    page.wait_for_selector(".mentor-window")
    page.wait_for_function("() => document.querySelector('.mentor-window').getAnimations().every(a => a.playState === 'finished')")

def ask(page, text):
    page.fill(".mentor-input", text)
    page.keyboard.press("Enter")

LAYOUT = """() => { const box = [...document.querySelectorAll('.mentor-reply')].pop();
    const taps = [...box.querySelectorAll('.mentor-chip, .mentor-source')].map(c => c.getBoundingClientRect());
    return { sideways: document.documentElement.scrollWidth > innerWidth, small: taps.filter(r => r.height < 44).length, n: taps.length }; }"""

def main():
    errors, dialogs = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block", reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda x: errors.append(str(x)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        t.fresh(page)

        print("\n--- 1. The engine ---")
        got = {a["q"]: a for a in page.evaluate(ASK, SAMPLE)}
        tails = [a["q"] for a in got.values() if "Also see" in a["lead"] or any("Also see" in x for x in a["more"])]
        check("no answer ends with (or holds) 'Also see'", not tails, tails)
        fit = got["how do I paint eyes"]
        lines = [fit["lead"]] + fit["more"]
        check("a good fit from a guide: two or three lines, the extra ones from the best guide's own text",
              fit["band"] == "clear" and fit["readGuide"] and 2 <= len(lines) <= 3 and all(x in fit["body"] for x in fit["more"]) and fit["keys"][:1] == ["painting-eyes"], fit)
        weak = got["how do I paint metal"]
        check("a weaker match keeps the old shape (no extra lines, no Read the guide)", weak["band"] == "maybe" and not weak["more"] and not weak["readGuide"], weak)
        tech = page.evaluate(ASK, ["how do I paint skin", "how to paint dark brown"])
        check("'how do I paint skin' ranks a technique guide first", tech[0]["cat"] == "techniques:guide", tech[0])
        check("in 'how do I paint X' the main noun is the last of two words ('dark brown' is about brown)", tech[1]["keys"][:1] == ["painting-brown"], tech[1])
        gold, blue = got["how do I paint gold"], page.evaluate(ASK, ["how do I paint blue"])[0]
        check("'how do I paint gold' and 'how do I paint blue' get an entry, not the colour rule",
              gold["kind"] == "answer" and "gold" in gold["keys"][0] and blue["keys"][:1] == ["painting-blue"], [gold, blue])
        wrong = got["my wash went chalky"]
        check("a best title without the main noun: 'Did you mean' with two or three choices and no answer",
              wrong["kind"] == "answer" and wrong["band"] == "maybe" and 2 <= len(wrong["choices"]) <= 3 and wrong["lead"] == "Did you mean"
              and any("wash" in c.lower() for c in wrong["choices"]) and "Fixing chalky highlights" in wrong["choices"], wrong)
        plain = page.evaluate(ASK, ["gold", "blue"])
        check("the gold line has the new wording", plain[0]["lead"] == "Gold looks brightest next to blue, and quieter next to orange or lime.", plain[0])
        check("other colours follow the same wording", plain[1]["lead"].startswith("Blue looks brightest next to ") and "sits calmly" not in plain[1]["lead"], plain[1])

        print("\n--- 2. The window ---")
        open_it(page)
        ask(page, "how do I paint eyes")
        r = page.locator(".mentor-reply").last
        check("the good fit shows the lead and its next lines", r.locator(".mentor-lead").count() == 1 and 1 <= r.locator(".mentor-more").count() <= 2)
        check("one link, 'Read the guide', that names the guide for screen readers",
              r.locator(".mentor-source").count() == 1 and r.locator(".mentor-source").inner_text().strip() == "Read the guide"
              and "Painting eyes on faces" in (r.locator(".mentor-source").get_attribute("aria-label") or ""))
        lay = page.evaluate(LAYOUT)
        check("390x844 dark: the link is 44 px or more, nothing scrolls sideways", lay["n"] >= 1 and lay["small"] == 0 and not lay["sideways"], lay)
        r.locator(".mentor-source").click()
        page.wait_for_function("() => !document.querySelector('.mentor-window')")
        page.wait_for_timeout(300)
        check("Read the guide opens that guide", page.locator("#guide-painting-eyes").count() == 1 and page.locator("#guide-painting-eyes").is_visible())

        page.set_viewport_size({"width": 360, "height": 640})
        page.evaluate("() => document.documentElement.setAttribute('data-appearance', 'light')")
        open_it(page)
        ask(page, "my wash went chalky")
        r = page.locator(".mentor-reply").last
        chips = r.locator(".mentor-dym-choices .mentor-chip").evaluate_all("els => els.map(e => e.textContent)")
        check("the choices show as two or three chips under 'Did you mean', with no answer line or links",
              r.locator(".mentor-dym").inner_text() == "Did you mean" and 2 <= len(chips) <= 3 and r.locator(".mentor-lead").count() == 0 and r.locator(".mentor-source").count() == 0, chips)
        check("the choices are announced", page.locator(".mentor-window [role=status]").inner_text().startswith("Did you mean " + chips[0]))
        lay = page.evaluate(LAYOUT)
        check("360x640 light: the chips are 44 px or more, nothing scrolls sideways", lay["n"] >= 2 and lay["small"] == 0 and not lay["sideways"], lay)
        r.locator(".mentor-dym-choices .mentor-chip").first.click()
        check("a tapped choice asks that title and gets a plain answer; the other choices go",
              page.locator(".mentor-me").last.inner_text() == chips[0] and page.locator(".mentor-reply").last.locator(".mentor-dym").count() == 0
              and page.locator(".mentor-reply").last.locator(".mentor-source").count() >= 1 and page.locator(".mentor-dym-choices .mentor-chip").count() == 0)

        check("no page errors", not errors, errors)
        check("no browser pop-ups", not dialogs, dialogs)
        browser.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
