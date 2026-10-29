"""Runs every test file in this folder and fails loudly if any check fails.

How to run it (from the repo folder):
    python3 tests/run_all.py              # everything, several test files at a time (cores + 2, at most 8; this is the full run before a merge)
    python3 tests/run_all.py --jobs 1     # one at a time, the old way
    python3 tests/run_all.py --jobs 4     # a different number at once (the whole-run time limits are only checked at the default)
    python3 tests/run_all.py --quick      # only the newest three versions plus a short always-run list
    python3 tests/run_all.py --update-budget   # after a clean full run: rewrite tests/time_budget.json on purpose
    python3 tests/run_all.py --rerun-failed    # after the run, rerun each failed file alone to tell a busy-machine failure from a real one

What it does:
1. Finds a free port on this computer, so it never clashes with another server.
2. Starts a small local web server (one that can answer several tests at once) that serves the repo folder.
3. Runs the tests/test_*.py files, several at a time, telling each which port to use. Each test gets its own
   screenshots folder and its own Content Security Policy log, so tests running side by side never overwrite
   each other. Each test's output is printed in one piece when that test finishes.
4. Prints a summary, the 15 slowest test files and the total time, and exits with code 1 if any file failed
   (0 if all passed). The times are also kept in tests/screenshots/timings.json (git-ignored).
5. (v21.2) Watches every test's browser for Content Security Policy errors (see csp_watch/), and
   counts any as a failure, even if that test's own checks all passed.
6. The growth guard (full runs only): compares each test file's time, and the whole run, with tests/time_budget.json.
   A warning prints a "TIME WARNINGS" block and still exits 0; a failure exits 1 and names the file. See check_budget().
7. A cheap source lint: a test file that is not in the budget's "version_words_ok" list may not mention APP_VERSION,
   sw.js, ?v=, CHANGELOG, DATA_VERSION or git diff. Those checks live only in tests/test_version_plumbing.py (which uses
   tests/version_helpers.py).
8. (T5) --rerun-failed: after the normal run, each failed file is run again alone, one at a time, and reported as "failed in the run,
   passed alone", "time only" (no failed check, just over its time limit) or "still failing". Exit 0 only if every failure passed alone.
   The reruns never count toward the time budget. SOG_TESTS_DIR (a folder path) makes the runner use that folder's test_*.py files
   instead of this one's, which is how tests/test_runner_rerun.py tries it on fake files.
"""
import argparse, json, math, os, re, socket, subprocess, sys, time, glob
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCREENSHOTS = os.path.join(HERE, "screenshots")  # the tests save pictures here; it is git-ignored
TIMINGS = os.path.join(SCREENSHOTS, "timings.json")
BUDGET = os.path.join(HERE, "time_budget.json")  # kept in the repo; only --update-budget rewrites it
TESTS = os.environ.get("SOG_TESTS_DIR") or HERE   # the folder whose test_*.py files are run (only a test of the runner changes it)
PLUMBING_FILES = ("test_version_plumbing.py", "version_helpers.py")  # the only files allowed to check the version
# T4: the tests mostly wait for the browser, so more files at once than cores is faster; too many starves the machine and makes timing
# checks wobble. JOBS_EXTRA files more than the number of cores, never more than MAX_JOBS and never fewer than 2.
JOBS_EXTRA, MAX_JOBS = 2, 8

def default_jobs():
    return max(2, min(MAX_JOBS, (os.cpu_count() or 4) + JOBS_EXTRA))

DEFAULT_JOBS = default_jobs()
VERSION_WORDS = re.compile(r"APP_VERSION|sw\.js|\?v=|CHANGELOG|DATA_VERSION|git diff")

# Test files that cannot share the machine with others. They run one at a time after the parallel ones.
# (None found: tests only use their own browser, their own port-less files and their own screenshots folder.)
RUN_ALONE = []

# Failures that also happen on main (see CLAUDE.md). --rerun-failed names them but never counts them as cleared.
KNOWN_FAILURES = ("test_colour_engine.py", "test_v21_7.py")

# --quick always runs these, besides the newest three versions:
#  - test_version_plumbing, the one test that checks the version number, the script tags, sw.js and the Updates entry,
#    so a forgotten part of a version bump is caught
#  - test_html_safety, a fast scan of every source file for unsafe HTML
ALWAYS = ["test_html_safety", "test_version_plumbing"]

SERVER = ("import sys; from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler as H; "
          "ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()")


def free_port():
    # Asks the system for a free port by binding to port 0, then releases it.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def version_key(name):
    # test_v21_7.py -> (21, 7); test_v37b.py -> (37,); files with no version (test_html_safety) -> None
    m = re.match(r"test_v(\d+(?:_\d+)*)", name)
    return tuple(int(n) for n in m.group(1).split("_")) if m else None


def pick_quick(paths):
    names = [os.path.basename(p)[:-3] for p in paths]
    keys = sorted({version_key(n) for n in names if version_key(n)}, reverse=True)[:3]
    return [p for p, n in zip(paths, names) if version_key(n) in keys or n in ALWAYS]


_CAL_JOB = ("import time\nt = time.perf_counter()\nx = 0\nfor i in range(2_000_000):\n    x += (i * i) % 7\nprint(time.perf_counter() - t)")


def calibrate(jobs):
    """T4: how fast would a test file run on this machine right now? Starts `jobs` copies of a small fixed CPU job at the same moment (as
    many as there are test files running at once, so it feels the cores being shared and any other work on the machine), and takes the
    middle time of the copies. Done three times, fastest round kept. It is about 0.15 s on the machine the budget was recorded on.
    The time limits are scaled by how much slower than the recorded reference this is (see time_factor)."""
    best = float("inf")
    for _ in range(3):
        procs = [subprocess.Popen([sys.executable, "-c", _CAL_JOB], stdout=subprocess.PIPE, text=True) for _ in range(max(1, jobs))]
        times = sorted(float(p.communicate()[0]) for p in procs)
        best = min(best, times[len(times) // 2])
    return best


FACTOR_MIN, FACTOR_MAX = 0.8, 3.0   # a very fast machine is not allowed to tighten the limits by more than 20%, a very slow one loosens them by 3x at most


def time_factor(budget, measured):
    """Speed of this machine relative to the one the budget was recorded on, kept between FACTOR_MIN and FACTOR_MAX. SOG_TIME_FACTOR
    (a number) overrides it for a probe. Without a recorded reference in the budget file the factor is 1."""
    forced = os.environ.get("SOG_TIME_FACTOR")
    if forced:
        return max(FACTOR_MIN, min(FACTOR_MAX, float(forced)))
    ref = budget.get("calibration_seconds")
    if not ref or not measured:
        return 1.0
    return max(FACTOR_MIN, min(FACTOR_MAX, measured / ref))


def load_budget():
    try:
        with open(BUDGET, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"files": {}, "total_warn_minutes": 15, "total_fail_minutes": 20, "version_words_ok": []}


def lint_sources(budget):
    """Fail a test file that is new (not in version_words_ok) and checks the version, sw.js, script tags, the Updates
    list, DATA_VERSION or a git diff itself. Returns a list of failure lines."""
    ok = set(budget.get("version_words_ok", [])) | set(PLUMBING_FILES)
    bad = []
    for path in sorted(glob.glob(os.path.join(TESTS, "test_*.py"))):
        name = os.path.basename(path)
        if name in ok:
            continue
        with open(path, encoding="utf-8") as f:
            hits = sorted(set(VERSION_WORDS.findall(f.read())))
        if hits:
            bad.append(f"{name} (SOURCE LINT: mentions {', '.join(hits)}; version checks belong in test_version_plumbing.py "
                       f"and tests/version_helpers.py only)")
    return bad


def check_budget(budget, times, checks, total_seconds, jobs, factor=1.0, total_factor=None):
    """The growth guard. Returns (warnings, failures), two lists of plain sentences."""
    warns, fails = [], []
    known = budget.get("files", {})
    for name in sorted(times):
        took = times[name]
        if name in known:
            was = known[name]
            limit = budget.get("fail_overrides", {}).get(name, 180) * factor   # a longer allowance, named in the budget file, for a file that is slow because the app is
            if took > limit:
                fails.append(f"{name} took {took:.0f} s, over the {limit:.0f} s limit (recorded {was:.0f} s)")
            elif took > was * 1.25 * factor or took > 120 * factor:
                why = f"over its recorded {was:.0f} s plus 25%" if took > was * 1.25 * factor else f"over {120 * factor:.0f} s"
                warns.append(f"{name} took {took:.0f} s, {why}")
        else:
            if took > 45 * factor:
                fails.append(f"{name} is a new test file and took {took:.0f} s, over the {45 * factor:.0f} s limit")
            elif took > 30 * factor:
                warns.append(f"{name} is a new test file and took {took:.0f} s, over {30 * factor:.0f} s")
            if checks.get(name, 0) > 60:
                warns.append(f"{name} is a new test file with {checks[name]} checks, over 60")
    if jobs == DEFAULT_JOBS:  # the total limits were set with the default number of files at a time, so they mean nothing for other settings
        minutes = total_seconds / 60
        tf = factor if total_factor is None else total_factor
        fail_at, warn_at = budget.get("total_fail_minutes", 20) * tf, budget.get("total_warn_minutes", 15) * tf
        if minutes > fail_at:
            fails.append(f"the whole run took {minutes:.1f} minutes, over the {fail_at:.1f} minute limit")
        elif minutes > warn_at:
            warns.append(f"the whole run took {minutes:.1f} minutes, over {warn_at:.1f}")
    return warns, fails


def update_budget(budget, times, calibration, jobs):
    budget["files"] = {n: math.ceil(t) for n, t in sorted(times.items())}
    # T4: the reference the time limits are scaled against: how long the fixed CPU job took on this machine, and how many cores it has
    budget["calibration_seconds"] = round(calibration, 3)
    budget["calibration_jobs"] = jobs
    budget["calibration_cores"] = os.cpu_count() or 4
    with open(BUDGET, "w", encoding="utf-8") as f:
        json.dump(budget, f, indent=1)
        f.write("\n")
    print(f"Wrote {BUDGET} ({len(times)} files).")


def run_one(path, port):
    name = os.path.basename(path)
    shots = os.path.join(SCREENSHOTS, name[:-3])
    os.makedirs(shots, exist_ok=True)
    csp_log = os.path.join(shots, "csp-errors.log")
    open(csp_log, "w").close()
    watch = os.path.join(HERE, "csp_watch")
    env = dict(os.environ, SOG_PORT=str(port), SOG_CSP_LOG=csp_log,
               PYTHONPATH=watch + os.pathsep + os.environ.get("PYTHONPATH", ""))
    started = time.time()
    problems = []
    try:
        run = subprocess.run([sys.executable, path, shots], env=env, cwd=REPO, timeout=900,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace")
        out = run.stdout
        if run.returncode != 0:
            problems.append(f"{name} (exit code {run.returncode})")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
        problems.append(f"{name} (took longer than 15 minutes)")
    blocked = [line for line in open(csp_log, encoding="utf-8").read().splitlines() if line.strip()]
    if blocked:
        out += f"CSP: the browser blocked {len(blocked)} thing(s) during {name}:\n"
        for line in blocked[:10]:
            out += "  " + line[:300] + "\n"
        problems.append(f"{name} (Content Security Policy errors)")
    took = time.time() - started
    checks = len(re.findall(r"^(?:PASS|FAIL) ", out, re.M))
    # one block per test, printed in one piece so parallel tests never interleave
    print(f"\n===== {name} (port {port}, {took:.0f}s, {checks} checks) =====\n{out}", flush=True)
    return name, took, problems, checks


def rerun_alone(run_problems, time_only, port, budget, factor):
    """T5: runs each failed file again by itself, one at a time. run_problems is {file: problems} for files that failed a check or
    crashed; time_only is {file: sentence} for files that only went over a time limit. Returns {file: (cleared, plain sentence)}.
    The times of these reruns are not kept anywhere, so they never reach the budget."""
    out = {}
    print("\n===== RERUNNING FAILED FILES ALONE =====", flush=True)
    for name in sorted(set(run_problems) | set(time_only)):
        _, took, problems, count = run_one(os.path.join(TESTS, name), port)
        if problems:
            known = " (a known failure on main)" if name in KNOWN_FAILURES else ""
            out[name] = (False, f"{name}: still failing{known}: {'; '.join(problems)}")
        elif name in time_only:
            _, slow = check_budget(budget, {name: took}, {name: count}, took, -1, factor)
            if slow:
                out[name] = (False, f"{name}: time only, and still too slow alone: {slow[0]}")
            else:
                out[name] = (True, f"{name}: time only. {time_only[name]}. Alone it took {took:.0f} s, inside the limit.")
        else:
            out[name] = (True, f"{name}: failed in the run, passed alone ({took:.0f} s alone).")
    return out


def main():
    ap = argparse.ArgumentParser(description="Run the Minifolio tests.")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help=f"how many test files to run at once (default {DEFAULT_JOBS})")
    ap.add_argument("--quick", action="store_true",
                    help="only the newest three versions plus the always-run list (not for before a merge)")
    ap.add_argument("--update-budget", action="store_true",
                    help="after a clean full run, rewrite tests/time_budget.json with this run's times (on purpose, never automatic)")
    ap.add_argument("--rerun-failed", action="store_true",
                    help="after the run, rerun each failed file alone and say whether it passed alone; exit 0 only if every failure did")
    args = ap.parse_args()
    if args.update_budget and args.quick:
        sys.exit("--update-budget needs a full run, not --quick.")
    budget = load_budget()
    lint = lint_sources(budget)
    measured = calibrate(args.jobs)   # before any test starts, so the tests do not slow it down
    factor = time_factor(budget, measured)
    total_factor = factor   # the speed check already includes how many cores share the jobs
    print(f"Speed check: {measured:.2f} s with {args.jobs} at once (reference {budget.get('calibration_seconds', 'not recorded')}), "
          f"{os.cpu_count()} cores. Time limits x{factor:.2f}.", flush=True)

    port = free_port()
    os.makedirs(SCREENSHOTS, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-c", SERVER, str(port)],
                              cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)  # give the server a moment to start
    paths = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
    if args.quick:
        paths = pick_quick(paths)
        print("QUICK MODE: " + str(len(paths)) + " test files. Run without --quick before any merge.", flush=True)
    together = [p for p in paths if os.path.basename(p)[:-3] not in RUN_ALONE]
    alone = [p for p in paths if os.path.basename(p)[:-3] in RUN_ALONE]
    failed, times, checks = list(lint), {}, {}
    started = time.time()
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(pool.map(lambda p: run_one(p, port), together))
        results += [run_one(p, port) for p in alone]
    finally:
        server.terminate()
    for name, took, problems, count in results:
        times[name] = round(took, 1)
        checks[name] = count
        failed += problems
    total = time.time() - started
    with open(TIMINGS, "w", encoding="utf-8") as f:
        json.dump({"jobs": args.jobs, "quick": args.quick, "total_seconds": round(total, 1), "tests": times, "checks": checks}, f, indent=1)

    print("\n===== SLOWEST 15 TEST FILES =====")
    for name, took in sorted(times.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {took:7.1f}s  {name}")
    print(f"Total: {total / 60:.1f} minutes for {len(times)} test files, {sum(checks.values())} checks ({args.jobs} at a time).")

    warns, fails = ([], []) if args.quick else check_budget(budget, times, checks, total, args.jobs, factor, total_factor)
    failed += [f"TIME: {x}" for x in fails]
    if warns:
        print("\n===== TIME WARNINGS =====")
        for w in warns:
            print("  - " + w)
        print("These do not fail the run. Look for a slow loop that can be sampled (see CLAUDE.md).")
    if args.rerun_failed and failed:
        run_problems = {n: p for n, _, p, _ in results if p}
        time_only = {}
        for sentence in fails:
            name = sentence.split()[0]
            if name in times and name not in run_problems:
                time_only[name] = sentence
        if run_problems or time_only:
            port = free_port()
            server = subprocess.Popen([sys.executable, "-c", SERVER, str(port)],
                                      cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            try:
                again = rerun_alone(run_problems, time_only, port, budget, factor)
            finally:
                server.terminate()
            cleared = {n for n, (ok, _) in again.items() if ok}
            print("\n===== RERUN RESULT =====")
            for _, (_, line) in sorted(again.items()):
                print("  " + line)
            failed = [f for f in failed if (re.search(r"test_\w+\.py", f) or [None])[0] not in cleared]
            if not failed:
                print("Every failure passed alone.")
    if args.update_budget:
        if failed:
            print("\nNot updating the budget: the run had failures.")
        else:
            update_budget(budget, times, measured, args.jobs)

    print("\n===== SUMMARY =====")
    if failed:
        print("FAILED:")
        for f in failed:
            print("  - " + f)
        print("\nSome checks failed. Scroll up to the FAIL lines above.")
        sys.exit(1)
    print("All test files passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
