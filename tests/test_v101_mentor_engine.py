"""X6a: the Mentor answer engine (mentor-engine.js), no screen yet.

Runs tests/mentor_engine_check.js in Node: a table of 50 example questions with the entry each should lead to (guides, recipes, basing tips,
Mentor tips, starter questions, the colour path, owned paints first, the no-answer path), repeatable answers, the words it may say, no
storage or network, and speed. The entries come from the app's own loader and data files plus a small test-only fixture
(tests/mentor_engine_fixture.json, built from knowledge-base/samples). One page check: the script loads in the app without errors."""
import json, os, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, ".."))
PORT = os.environ.get("SOG_PORT", "8000")
results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

def main():
    print("--- 1. The engine, in Node ---")
    run = subprocess.run(["node", os.path.join(HERE, "mentor_engine_check.js")], capture_output=True, text=True, cwd=ROOT)
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
        page.goto(f"http://localhost:{PORT}/index.html")
        page.wait_for_function("() => typeof settings === 'object'")
        r = page.evaluate("""() => { const a = MinifolioMentor.mentorAnswer('what goes with blue', { index: { entries: [] }, paints: [] });
            return { kind: a.kind, src: a.sources.map(s => s.type) }; }""")
        check("the engine is on the page and answers a colour question", r["kind"] == "colour" and r["src"] == ["colour-lab"], r)
        check("no page errors", not errors, errors)
        browser.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

main()
