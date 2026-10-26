"""Runs every test file in this folder and fails loudly if any check fails.

How to run it (from the repo folder):
    python3 tests/run_all.py              # everything, 4 test files at a time (this is the full run before a merge)
    python3 tests/run_all.py --jobs 1     # one at a time, the old way
    python3 tests/run_all.py --quick      # only the newest three versions plus a short always-run list

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
"""
import argparse, json, os, re, socket, subprocess, sys, time, glob
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCREENSHOTS = os.path.join(HERE, "screenshots")  # the tests save pictures here; it is git-ignored
TIMINGS = os.path.join(SCREENSHOTS, "timings.json")

# Test files that cannot share the machine with others. They run one at a time after the parallel ones.
# (None found: tests only use their own browser, their own port-less files and their own screenshots folder.)
RUN_ALONE = []

# --quick always runs these, besides the newest three versions:
#  - the tests whose version lists must be extended on every version bump (test_v39 to v42, v51 to v53, v49), so a
#    forgotten bump is caught
#  - test_v54, which reads the newest Updates entry itself
#  - test_html_safety, a fast scan of every source file for unsafe HTML
ALWAYS = ["test_html_safety", "test_v39", "test_v40", "test_v41", "test_v42", "test_v49", "test_v51", "test_v52",
          "test_v53", "test_v54"]

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
    # one block per test, printed in one piece so parallel tests never interleave
    print(f"\n===== {name} (port {port}, {took:.0f}s) =====\n{out}", flush=True)
    return name, took, problems


def main():
    ap = argparse.ArgumentParser(description="Run the Minifolio tests.")
    ap.add_argument("--jobs", type=int, default=4, help="how many test files to run at once (default 4)")
    ap.add_argument("--quick", action="store_true",
                    help="only the newest three versions plus the always-run list (not for before a merge)")
    args = ap.parse_args()

    port = free_port()
    os.makedirs(SCREENSHOTS, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-c", SERVER, str(port)],
                              cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)  # give the server a moment to start
    paths = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if args.quick:
        paths = pick_quick(paths)
        print("QUICK MODE: " + str(len(paths)) + " test files. Run without --quick before any merge.", flush=True)
    together = [p for p in paths if os.path.basename(p)[:-3] not in RUN_ALONE]
    alone = [p for p in paths if os.path.basename(p)[:-3] in RUN_ALONE]
    failed, times = [], {}
    started = time.time()
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(pool.map(lambda p: run_one(p, port), together))
        results += [run_one(p, port) for p in alone]
    finally:
        server.terminate()
    for name, took, problems in results:
        times[name] = round(took, 1)
        failed += problems
    total = time.time() - started
    with open(TIMINGS, "w", encoding="utf-8") as f:
        json.dump({"jobs": args.jobs, "quick": args.quick, "total_seconds": round(total, 1), "tests": times}, f, indent=1)

    print("\n===== SLOWEST 15 TEST FILES =====")
    for name, took in sorted(times.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {took:7.1f}s  {name}")
    print(f"Total: {total / 60:.1f} minutes for {len(times)} test files ({args.jobs} at a time).")

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
