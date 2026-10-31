"""X8b (v105) tests for Minifolio: the Mentor answer engine's additions, and their data file mentor-data.js.

Runs tests/mentor_upgrade_check.js in Node: the data file's shape and words,
extra keywords for recipes and basing tips, synonyms (in questions, in entries, and so the colour path is not fooled), rare words counting
more, the phrase bank, the quick lead (strong match only, 'Also see' only if it fits, starters), the none answer with the data on the
page (the unknown-word rule at full strength only in an index with enough different words), leads made as before when the data
has no quick or starter answers (built with --no-quick), the same answer shape, and speed with about 800 entries and their phrase bank. Most checks use small made-up entries and hand in
their own data, so they test the engine and not the content.
One page check: the data file loads in the app and the engine uses it. No page errors, no browser pop-ups.
Run all tests with `python3 tests/run_all.py`, or serve the repo folder and run this file on its own."""
import json, os, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("MINIFOLIO_ROOT") or (os.path.realpath(os.path.join(HERE, "..")) if os.path.exists(os.path.join(HERE, "..", "app.js")) else os.path.realpath(os.path.join(HERE, "..", "..")))
PORT = os.environ.get("SOG_PORT", "8000")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def main():
    print("--- 1. The engine and its data, in Node ---")
    run = subprocess.run(["node", os.path.join(HERE, "mentor_upgrade_check.js")], capture_output=True, text=True, cwd=ROOT,
                         env=dict(os.environ, MINIFOLIO_ROOT=ROOT))
    try:
        data = json.loads(run.stdout)
    except ValueError:
        check("the Node checks ran", False, (run.stdout + run.stderr)[-800:])
        data = {"out": []}
    for c in data["out"]:
        check(c["name"], c["ok"], c["detail"][:500])
    if data.get("speed"):
        print("SPEED (ms, this machine): " + json.dumps({k: round(v, 3) for k, v in data["speed"].items()}))

    print("\n--- 2. In the browser ---")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.goto(f"http://localhost:{PORT}/index.html")
        page.wait_for_function("() => typeof settings === 'object'")
        r = page.evaluate("""() => {
            const has = typeof MENTOR_DATA === 'object' && !!MENTOR_DATA.phrases;
            const index = knowledgeIndex();
            const a = MinifolioMentor.mentorAnswer('how do I paint fangs', { index, paints: [] });
            const b = MinifolioMentor.mentorAnswer('how do I paint fangs', { index, paints: [], data: null });
            const teeth = (x) => x.sources.some((s) => s.type === 'recipe' && s.key === 'teeth');
            return { has, kind: a.kind, with: teeth(a), without: teeth(b), sources: a.sources.map((s) => s.key) }; }""")
        # X8b: the real app also has the knowledge base's guides, so "fangs" finds the teeth guide first either way. What the data adds
        # is the Teeth recipe (its extra keyword "fangs"), so the check is that the recipe is among the sources only with the data.
        check("the data is on the page and the engine uses it (fangs also finds the Teeth recipe; with data: null it does not)",
              r["has"] and r["kind"] == "answer" and r["with"] and not r["without"], r)
        check("no page errors and no browser pop-ups", not errors, errors)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
