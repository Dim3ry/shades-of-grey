"""Page-writing safety guard for Minifolio. No browser needed; it just reads the code files.

WHY THIS EXISTS
Typed or imported text (unit names, notes, pasted recipes, backup files, label-scanner results)
must only ever be shown as plain text. The safe way is textContent or createElement. The risky way
is building HTML text and handing it to innerHTML / insertAdjacentHTML, because any <script>-like
text inside a name would then be treated as page code. Today the app only uses those risky calls
for clearing a box, fixed wording, or numbers it works out itself (checked by hand on 17 Oct 2026).
This test keeps it that way as the code grows.

WHAT IT CHECKS
0. Which files: every script the pages load (the <script src> tags in each .html file), every script
   those name in turn (the offline helper sw.js, the label reader's worker), and any other .js file in
   the app folder or ocr/. Nothing is listed by hand, so a new file is scanned from the start (SEC1).
   The vendored label-reader engine (ocr/tesseract-core-*) is someone else's code and is left out.
1. Banned outright, in every code file: setting outerHTML (= or +=), "innerHTML" or "outerHTML" written
   as text (el["innerHTML"], Object.assign(el, {innerHTML: ...}), Reflect.set), srcdoc, setHTMLUnsafe,
   createContextualFragment, DOMParser / parseFromString, document.write and writeln, eval() (also
   window.eval), Function() with or without new, setTimeout or setInterval given text instead of a
   function, and onclick-style attributes written with setAttribute in any mix of capitals.
2. Every innerHTML = ..., innerHTML += ... and insertAdjacentHTML(...) in the code is one of:
   - clearing a box (innerHTML = ""),
   - fixed wording only (no variables inside it), or
   - on the REVIEWED list below (a person looked at it and it only inserts numbers or fixed words).
   Anything else FAILS, and the test prints the line so you can fix it.
3. Every link or picture address set from code (.href =, .src =, .action =, setAttribute("href" or "src"),
   and setAttribute with an attribute name that isn't written out) is fixed text or on REVIEWED_URLS.
4. The checker itself still works: made-up bad lines (the ones the 2 Nov security test slipped past the
   older version of this file) are caught, and made-up good lines pass.

IF THIS TEST FAILS ON NEW CODE
Best fix: build the element with createElement and put the text in with textContent.
Only if the new line truly inserts numbers or fixed words: run this file, copy the code it prints
for that line into REVIEWED, and write a short note beside it saying what it inserts. For a link or
picture address, the same goes for REVIEWED_URLS: say where the address comes from.

Run all tests with `python3 tests/run_all.py`, or run this file on its own."""
import glob, hashlib, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
VENDORED = re.compile(r"^ocr/tesseract-core-")   # the label reader's engine, copied in unchanged (see ocr/README.md)
results = []


def page_scripts():
    """The scripts each .html page loads, as paths from the app folder ("app.js", not "app.js?v=122")."""
    found = {}
    for page in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        html = open(page, encoding="utf-8").read()
        for src in re.findall(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"'?#]+)""", html, re.I):
            found.setdefault(src.lstrip("./"), os.path.basename(page))
    return found


def code_files():
    """Every script to scan: the pages' scripts, any .js file those name (sw.js, the OCR worker), and any other
    .js file in the app folder or ocr/. Returns (files, from_pages)."""
    from_pages = page_scripts()
    todo, files = list(from_pages), []
    while todo:
        name = todo.pop(0)
        path = os.path.join(ROOT, name)
        if name in files or VENDORED.match(name) or not os.path.isfile(path):
            continue
        files.append(name)
        src = open(path, encoding="utf-8").read()
        base = os.path.dirname(name)
        for ref in re.findall(r"""["'`]([\w./-]+\.js)["'`]""", src):
            for cand in (ref.lstrip("./"), os.path.normpath(os.path.join(base, ref)).replace(os.sep, "/")):
                if os.path.isfile(os.path.join(ROOT, cand)) and cand not in files:
                    todo.append(cand)
    for path in sorted(glob.glob(os.path.join(ROOT, "*.js")) + glob.glob(os.path.join(ROOT, "ocr", "*.js"))):
        name = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if name not in files and not VENDORED.match(name):
            files.append(name)
    return files, from_pages

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
    # U6b: the Mentor orb (early.js, minifolioLook.svg): one of James's fixed drawings from mentor-looks.js, chosen by a look and a state the
    # app checks against MENTOR_LOOKS first. Never anything typed or imported.
    "353f8092eea1": "Mentor orb: a fixed drawing from MENTOR_LOOKS",
}


# Link and picture addresses a person has looked at (SEC1, 2 Nov 2026). Same fingerprint as REVIEWED, but taken from
# the start of the line, so two lines that both read ".src = src;" are told apart.
REVIEWED_URLS = {
    # Shop links: a fixed shop address from the SHOPS table with the paint name passed through encodeURIComponent.
    "78f75cb744d0": "shop link (shopping list)",
    "11baaa6a3e70": "shop link (paint panel)",
    # Drawing helpers: attribute names written out in the code that calls them (chart and icon shapes), never typed text.
    # (U6b + LR1: the two helpers that drew the old Mentor orb and the old loading ring are gone, so their entries went too.)
    "7feb5ff72527": "svgEl helper",
    "908c1092b7d3": "status mark icon: a fixed list of attributes",
    "e39d72799718": "status mark icon: attributes from the fixed STATUS_MARKS table",
    "87341ffd62a8": "colour wheel shape helper",
    "7e563734f760": "search box: a fixed list of attributes",
    # Photos: blob: addresses the app makes itself from the photo store, or an old-style photo that cleanModels only
    # keeps when it is a JPEG, PNG or WebP picture written as text (SEC1).
    "592ec4ead56f": "unit card thumbnail",
    "a0a4deece7c0": "old-style photo, checked by cleanModels",
    "3b6f6659f370": "photo strip thumbnail",
    "a8880073b701": "loadImage: a blob: address made from the file",
    "190c3064d1f4": "photo viewer, full size",
    "88d0d3010977": "photo viewer, thumbnail first",
    "bf355a695163": "photo viewer, full size once read",
    # Credits: built-in data only, and only an https address (safeHttpsUrl / safeCreditUrl).
    "04e94676ddcd": "Mentor tip credit",
    "98148e6a2669": "Guides credit",
    # Fixed addresses.
    "dacfe45902fa": "download link: a blob: address the app makes",
    "9991c7aaa301": "feedback form: fixed address plus the app version",
    "e69efefb6805": "feedback form: fixed address plus the app version",
    "26f6ac013b0c": "visit counter: fixed address, everything after it encoded",
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
    (re.compile(r"\.outerHTML\s*\+?="), "sets outerHTML"),
    (re.compile(r"""["'`](?:inner|outer)HTML["'`]"""), "writes innerHTML or outerHTML as text (el[\"innerHTML\"], Reflect.set)"),
    (re.compile(r"\b(?:innerHTML|outerHTML)\s*:"), "hands innerHTML or outerHTML over in an object (Object.assign)"),
    (re.compile(r"srcdoc", re.I), "uses srcdoc (a whole page written as text)"),
    (re.compile(r"HTMLUnsafe\s*\("), "uses setHTMLUnsafe or parseHTMLUnsafe"),
    (re.compile(r"createContextualFragment\s*\("), "uses createContextualFragment"),
    (re.compile(r"\bDOMParser\b|parseFromString\s*\("), "uses DOMParser"),
    (re.compile(r"document\s*\.\s*write(?:ln)?\s*\("), "uses document.write or writeln"),
    (re.compile(r"\beval\s*\("), "uses eval()"),
    (re.compile(r"(?<![\w$])Function\s*\("), "uses Function() (with or without new)"),
    (re.compile(r"""\bset(?:Timeout|Interval)\s*\(\s*["'`]"""), "gives setTimeout or setInterval text to run"),
    (re.compile(r"""\.setAttribute\(\s*["'`]\s*on""", re.I), "writes an onclick-style attribute"),
    (re.compile(r"""\.setAttributeNS\(\s*[^,]*,\s*["'`]\s*on""", re.I), "writes an onclick-style attribute"),
]
TIMER = re.compile(r"\bset(?:Timeout|Interval)\s*\(\s*([A-Za-z_$][\w$]*)\s*[,)]")


def timer_problems(src):
    """setTimeout(name, ...) is only safe if `name` is a function. A name the file never defines as one could be text."""
    out = []
    for m in TIMER.finditer(src):
        name = re.escape(m.group(1))
        is_function = re.search(rf"function\s*\*?\s*{name}\s*\(|\b{name}\s*=\s*(?:async\s+)?(?:function\b|\([^()]*\)\s*=>|[\w$]+\s*=>)", src)
        if not is_function:
            out.append(src.count("\n", 0, m.start()) + 1)
    return out


URL_SINK = re.compile(r"""\.(?:href|src|action|formAction)\s*=(?!=)|\.setAttribute\(\s*["'`](?:href|src|xlink:href|action|formaction)["'`]|\.setAttribute\(\s*(?!["'`])|\.setAttributeNS\(""", re.I)


def judge_urls(src):
    """Every address set from code: fixed text, or reviewed. Returns (problems, fingerprints seen)."""
    problems, seen = [], set()
    for m in URL_SINK.finditer(src):
        text = statement(src, m.start())
        rest = text[len(m.group(0)):]
        if re.fullmatch(r"[\s+(),;]*", strip_fixed_text(rest)):
            continue                                  # fixed text
        line_start = src.rfind("\n", 0, m.start()) + 1
        code = fingerprint(src[line_start:m.start()] + text)
        seen.add(code)
        if code not in REVIEWED_URLS:
            problems.append((code, src.count("\n", 0, m.start()) + 1, " ".join((src[line_start:m.start()] + text).split())[:200]))
    return problems, seen


def banned_hits(src):
    hits = [(what, src.count("\n", 0, m.start()) + 1) for pattern, what in BANNED for m in pattern.finditer(src)]
    return hits + [("gives setTimeout or setInterval something that may be text", n) for n in timer_problems(src)]


# SEC1: the lines the 2 Nov security test added to a copy of the app, which the older version of this file passed.
BYPASSES = [
    'function a(box, name) { box.innerHTML = "<b>" + name + "</b>"; }',
    'function a(el, name) { el["innerHTML"] = name; }',
    'function a(el, name) { Object.assign(el, { innerHTML: name }); }',
    'function a(el, name) { el.outerHTML += name; }',
    'function a(el, name) { el.setAttribute("ONCLICK", name); }',
    'function a(el, name) { el.setHTMLUnsafe(name); }',
    'function a(name) { return document.createRange().createContextualFragment(name); }',
    'function a(name) { return new DOMParser().parseFromString(name, "text/html"); }',
    'function a(a, url) { a.href = url; }',
    'function a(a, url) { a.setAttribute("href", url); }',
    'function a(f, name) { f.srcdoc = name; }',
    'function a(name) { window.eval(name); }',
    'function a(name) { setTimeout(name, 0); }',
    'function a(name) { setTimeout("go(" + name + ")", 0); }',
    'function a(name) { document.writeln(name); }',
    'function a(name) { return Function("return " + name)(); }',
]


def caught(line):
    bad, _ = judge(line)
    urls, _ = judge_urls(line)
    return bool(bad or urls or banned_hits(line))


def main():
    print("--- checker self-test ---")
    bad, _ = judge('box.innerHTML = `<b>${unit.name}</b>`;')
    check("a line putting a name into innerHTML is caught", len(bad) == 1, bad)
    bad, _ = judge('box.insertAdjacentHTML("beforeend", "<i>" + note + "</i>");')
    check("a line joining text onto insertAdjacentHTML is caught", len(bad) == 1, bad)
    bad, _ = judge('box.innerHTML = "";\nbox.innerHTML = \'<p class="hint">Nothing here yet.</p>\';\n'
                   'box.insertAdjacentHTML("beforeend", `<p>Fixed words</p>`);')
    check("clearing a box and fixed wording pass", not bad, bad)
    missed = [b for b in BYPASSES if not caught(b)]
    check(f"all {len(BYPASSES)} lines the security test slipped past are caught", not missed, missed)
    good = ('function go() {}\nsetTimeout(go, 10); setTimeout(() => go(), 10);\nconst later = () => go(); setTimeout(later, 5);\n'
            'img.src = "icon-192.png"; a.href = "#help"; a.setAttribute("href", "#units"); el.setAttribute("aria-label", "Turn on");\n'
            'el.setAttribute("data-on", "1"); const text = "uses innerHTML safely";')
    check("ordinary safe lines (timers given functions, fixed addresses, other attributes) pass", not caught(good),
          [banned_hits(good), judge_urls(good)[0]])

    print("--- which files ---")
    files, from_pages = code_files()
    check("the pages' scripts were found from their <script> tags (index.html loads at least 5)",
          sum(1 for page in from_pages.values() if page == "index.html") >= 5, from_pages)
    missing = [name for name in from_pages if not os.path.isfile(os.path.join(ROOT, name))]
    check("every script a page loads exists", not missing, missing)
    need = ["sw.js", "ocr/ocr-worker.js"] + [n for n in from_pages if n.startswith("mentor") or n.startswith("guides")]
    check("the offline helper, the label reader's worker and every Mentor and Guides file are scanned",
          all(n in files for n in need) and len(need) >= 4, [n for n in need if n not in files])
    check("the vendored label-reader engine is left out", not any(VENDORED.match(n) for n in files), files)
    print("     scanning: " + ", ".join(files))

    print("--- the real code ---")
    seen_reviewed, seen_urls = set(), set()
    banned, html_problems, url_problems = [], [], []
    for name in files:
        src = open(os.path.join(ROOT, name), encoding="utf-8").read()
        banned += [f"{name}:{line} {what}" for what, line in banned_hits(src)]
        problems, _ = judge(src)
        html_problems += [f"{name} [{c}] {t}" for c, t in problems]
        for m in SINK.finditer(src):
            seen_reviewed.add(fingerprint(statement(src, m.start())))
        problems, seen = judge_urls(src)
        url_problems += [f"{name}:{line} [{c}] {t}" for c, line, t in problems]
        seen_urls |= seen
    check("no file uses a banned way of writing to the page", not banned, "\n     " + "\n     ".join(banned[:10]))
    check("every innerHTML / insertAdjacentHTML is a clear, fixed wording, or reviewed", not html_problems,
          "\n     " + "\n     ".join(html_problems[:6]) +
          "\n     Use createElement + textContent, or review the line and add its code to REVIEWED.")
    check("every link or picture address set from code is fixed text or reviewed", not url_problems,
          "\n     " + "\n     ".join(url_problems[:12]) +
          "\n     Check where the address comes from, then add its code to REVIEWED_URLS with a note.")
    stale = [c for c in REVIEWED if c not in seen_reviewed]
    check("every REVIEWED entry still matches a line in the code (remove ones that changed)",
          not stale, f"no longer found: {stale}")
    stale = [c for c in REVIEWED_URLS if c not in seen_urls]
    check("every REVIEWED_URLS entry still matches a line in the code (remove ones that changed)",
          not stale, f"no longer found: {stale}")

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
