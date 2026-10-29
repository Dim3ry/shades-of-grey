"""Knowledge base checker test. No browser needed; it runs knowledge-base/check_knowledge.py on its own samples.

WHAT IT CHECKS (new behaviour only)
1. The checker passes the sample entries and the app's own three data files (so it reads the existing formats).
2. The checker fails the bad-examples file, and names each kind of problem in plain words.
3. A few made-up one-line mistakes are each caught (so a pass is not luck): a banned word, an em dash, an emoji, an angle
   bracket, a key that breaks the format, a missing key, a link to nothing, a keyword count outside 6 to 12.
4. The folder is not pulled into the app: index.html and app.js never mention it.

Run on its own: python3 tests/test_kb_checker.py"""
import copy, importlib.util, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
KB = os.path.join(ROOT, "knowledge-base")
CHECKER = os.path.join(KB, "check_knowledge.py")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   [{detail}]"))


def run(*args):
    p = subprocess.run([sys.executable, CHECKER, *args], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    return p.returncode, p.stdout


def main():
    sample = os.path.join(KB, "samples", "sample-entries.json")
    bad = os.path.join(KB, "samples", "bad-examples.json")
    code, out = run(sample)
    check("the sample entries pass the checker (exit 0)", code == 0, out[-300:])
    code, out = run(sample, "--final")
    check("--final rejects sample entries", code == 1 and "SAMPLE" in out, out[-200:])
    code, out = run(*[os.path.join(ROOT, f) for f in ("detail-recipes.js", "basing-tips.js", "mentor-tips.js")])
    check("the app's own three data files pass (the existing formats are read as they are)", code == 0, out[-300:])
    code, out = run(bad)
    check("the bad-examples file fails the checker (exit 1)", code == 1, out[-200:])
    for label, phrase in [("a banned word", "Games Workshop or faction word"), ("an em dash", "em dash"), ("an emoji", "emoji"),
                          ("an angle bracket", "angle bracket"), ("a key that breaks the format", "lower case words joined by dashes"),
                          ("a missing field", "is missing field"), ("a link to nothing", "does not exist"),
                          ("a keyword count outside 6 to 12", "must have 6 to 12"), ("an unknown category", "'category' must be one of"),
                          ("a repeated key", "already used"), ("a step that breaks the thinning rule", "must be thinned")]:
        check(f"the bad examples show {label}, in words", phrase in out, phrase)
    check("the report ends by saying how many problems", "NOT CLEAN" in out)

    spec = importlib.util.spec_from_file_location("check_knowledge", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    good = json.load(open(sample, encoding="utf-8"))

    def problems_for(change):
        data = copy.deepcopy(good)
        change(data)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            json.dump(data, open(p, "w", encoding="utf-8"))
            return mod.check_all([p])[0]

    check("a clean copy of the samples has no problems", problems_for(lambda d: None) == [])
    check("--partial turns a link to a missing entry into a note, not a problem",
          mod.check_all([sample], partial=True)[0] == [])
    check("a banned word in one paragraph is caught", bool(problems_for(lambda d: d["guides"][0]["body"].__setitem__(0, "Paint it like a Space Marine does."))))
    check("an em dash in a title is caught", bool(problems_for(lambda d: d["guides"][0].update(title="Warm — cool"))))
    check("an angle bracket in a summary is caught", bool(problems_for(lambda d: d["guides"][0].update(summary="Use a <b>thin</b> coat on the first pass."))))
    check("11 keywords pass and 13 fail", problems_for(lambda d: d["guides"][0].update(keywords=[f"word {i}" for i in range(11)])) == []
          and bool(problems_for(lambda d: d["guides"][0].update(keywords=[f"word {i}" for i in range(13)]))))
    check("a starter question pointing at nothing fails", bool(problems_for(lambda d: d["starters"][0].update(targets=["nope"]))))
    check("a key shared by a guide and a starter fails", bool(problems_for(lambda d: d["starters"][0].update(key=d["guides"][0]["key"]))))

    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    app = open(os.path.join(ROOT, "app.js"), encoding="utf-8").read()
    check("the app page and app code never mention the knowledge-base folder", "knowledge-base" not in idx and "knowledge-base" not in app)

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
