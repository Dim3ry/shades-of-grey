"""Page-writing safety guard for Minifolio. No browser needed; it just reads the code files.

WHY THIS EXISTS
Typed or imported text (unit names, notes, pasted recipes, backup files, label-scanner results)
must only ever be shown as plain text. The safe way is textContent or createElement. The risky way
is building HTML text and handing it to innerHTML / insertAdjacentHTML, because any <script>-like
text inside a name would then be treated as page code. Today the app only uses those risky calls
for clearing a box, fixed wording, or numbers it works out itself (checked by hand on 17 Oct 2026).
This test keeps it that way as the code grows.

WHAT IT CHECKS
1. Banned outright, in every code file: setting outerHTML, document.write, eval(), new Function(),
   and onclick-style attributes written with setAttribute("on...").
2. Every innerHTML = ... and insertAdjacentHTML(...) in the code is one of:
   - clearing a box (innerHTML = ""),
   - fixed wording only (no variables inside it), or
   - on the REVIEWED list below (a person looked at it and it only inserts numbers or fixed words).
   Anything else FAILS, and the test prints the line so you can fix it.
3. The checker itself still works: a made-up bad line is caught and made-up good lines pass.

IF THIS TEST FAILS ON NEW CODE
Best fix: build the element with createElement and put the text in with textContent.
Only if the new line truly inserts numbers or fixed words: run this file, copy the code it prints
for that line into REVIEWED, and write a short note beside it saying what it inserts.

Run all tests with `python3 tests/run_all.py`, or run this file on its own."""
import hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CODE_FILES = ["app.js", "colour.js", "schemes.js", "detail-recipes.js", "basing-tips.js",
              "early.js", "sw.js", "ocr/ocr-worker.js"]
results = []

# Statements a person has looked at: each only inserts numbers, dates the app works out itself,
# or fixed wording. The code is the first 12 characters of a fingerprint of the statement with
# spaces tidied, so changing the statement means looking at it again.
REVIEWED = {
    # Dashboard graph pop-up: only the Added and Painted counts (numbers) and a percentage.
    "c5c7bd411009": "graph tooltip: two counts and a percentage",
    # Dashboard history table: rows built from counts and dates the app works out itself.
    "c996b8dc0922": "history table: counts, percentages and dates",
    # Paste recipes: a choice between two fixed sentences.
    "3ba0f487a0f3": "paste notice: one of two fixed sentences",
}


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))


SINK = re.compile(r"(\.innerHTML\s*\+?=|\.insertAdjacentHTML\s*\()")


def statement(src, start):
    """The text from `start` to the ';' that ends the statement (skipping ';' inside quotes)."""
    i, n, depth, quote = start, len(src), 0, None
    while i < n:
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if quote == "`" and c == "$" and src[i + 1:i + 2] == "{":
                depth += 1
                i += 2
                continue
            if quote == "`" and c == "}" and depth:
                depth -= 1
                i += 1
                continue
            if c == quote and not depth:
                quote = None
        else:
            if c in "'\"`":
                quote = c
            elif c == ";":
                return src[start:i + 1]
        i += 1
    return src[start:]


def strip_fixed_text(text):
    """Remove quoted text that has no ${...} in it. Anything left over is a variable or a call."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            quote, j, has_hole = c, i + 1, False
            while j < n and text[j] != quote:
                if text[j] == "\\":
                    j += 2
                    continue
                if quote == "`" and text[j] == "$" and text[j + 1:j + 2] == "{":
                    has_hole = True
                j += 1
            out.append(" VARIABLE " if has_hole else " ")
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def fingerprint(statement_text):
    return hashlib.sha1(" ".join(statement_text.split()).encode("utf-8")).hexdigest()[:12]


def judge(src):
    """Look at every risky page-writing statement in `src`. Returns (problems, reviewed_count)."""
    problems, reviewed = [], 0
    for m in SINK.finditer(src):
        text = statement(src, m.start())
        rest = text[len(m.group(0)):]
        if re.match(r"""\s*(""|'')\s*;$""", rest):
            continue                                  # clearing a box
        if re.fullmatch(r"[\s+(),;]*", strip_fixed_text(rest)):
            continue                                  # fixed wording only
        code = fingerprint(text)
        if code in REVIEWED:
            reviewed += 1
            continue
        problems.append((code, " ".join(text.split())[:240]))
    return problems, reviewed


BANNED = [
    (re.compile(r"\.outerHTML\s*="), "sets outerHTML"),
    (re.compile(r"document\.write\s*\("), "uses document.write"),
    (re.compile(r"(?<![\w.])eval\s*\("), "uses eval()"),
    (re.compile(r"new\s+Function\s*\("), "uses new Function()"),
    (re.compile(r"""setAttribute\(\s*["']on"""), "writes an onclick-style attribute"),
]


def main():
    print("--- checker self-test ---")
    bad, _ = judge('box.innerHTML = `<b>${unit.name}</b>`;')
    check("a line putting a name into innerHTML is caught", len(bad) == 1, bad)
    bad, _ = judge('box.insertAdjacentHTML("beforeend", "<i>" + note + "</i>");')
    check("a line joining text onto insertAdjacentHTML is caught", len(bad) == 1, bad)
    bad, _ = judge('box.innerHTML = "";\nbox.innerHTML = \'<p class="hint">Nothing here yet.</p>\';\n'
                   'box.insertAdjacentHTML("beforeend", `<p>Fixed words</p>`);')
    check("clearing a box and fixed wording pass", not bad, bad)

    print("--- the real code ---")
    seen_reviewed = set()
    for name in CODE_FILES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        for pattern, what in BANNED:
            hits = [src.count("\n", 0, m.start()) + 1 for m in pattern.finditer(src)]
            check(f"{name}: no code that {what}", not hits, f"line(s) {hits[:5]}")
        problems, _ = judge(src)
        check(f"{name}: every innerHTML / insertAdjacentHTML is a clear, fixed wording, or reviewed",
              not problems,
              "\n     " + "\n     ".join(f"[{c}] {t}" for c, t in problems[:6]) +
              "\n     Use createElement + textContent, or review the line and add its code to REVIEWED.")
        for m in SINK.finditer(src):
            seen_reviewed.add(fingerprint(statement(src, m.start())))
    stale = [c for c in REVIEWED if c not in seen_reviewed]
    check("every REVIEWED entry still matches a line in the code (remove ones that changed)",
          not stale, f"no longer found: {stale}")

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
