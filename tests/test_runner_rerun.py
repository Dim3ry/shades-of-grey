"""Tries the runner's --rerun-failed option on made-up test files. No browser needed.
Fake files: one that always passes, one that always fails, one that fails the first time and passes when run again (a flaky one).
SOG_TESTS_DIR points the runner at the folder of fake files."""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_all

bad = 0


def check(label, ok, detail=""):
    global bad
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + detail))
    bad += 0 if ok else 1


OK = "print('PASS fake ok')\n"
FAIL = "print('FAIL fake always fails')\nraise SystemExit(1)\n"
FLAKY = ("import os, sys\nmark = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seen.txt')\n"
         "if os.path.exists(mark):\n    print('PASS fake flaky, second time')\nelse:\n    open(mark, 'w').close()\n"
         "    print('FAIL fake flaky, first time')\n    raise SystemExit(1)\n")


def runner(files, *args):
    with tempfile.TemporaryDirectory() as d:
        for name, body in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(body)
        run = subprocess.run([sys.executable, os.path.join(HERE, "run_all.py"), "--jobs", "2", *args],
                             env=dict(os.environ, SOG_TESTS_DIR=d), capture_output=True, text=True, timeout=120)
        return run.returncode, run.stdout


code, out = runner({"test_fake_ok.py": OK, "test_fake_flaky.py": FLAKY}, "--rerun-failed")
check("a flaky file that passes alone gives exit 0", code == 0, f"exit {code}")
check("it says failed in the run, passed alone", "test_fake_flaky.py: failed in the run, passed alone" in out)
check("the passing file is not rerun", "test_fake_ok.py: " not in out.split("RERUN RESULT")[-1])

code, out = runner({"test_fake_ok.py": OK, "test_fake_flaky.py": FLAKY, "test_fake_bad.py": FAIL}, "--rerun-failed")
check("a file that still fails gives exit 1", code == 1, f"exit {code}")
check("it says still failing for the bad file", "test_fake_bad.py: still failing" in out)
check("the flaky file is still reported as passed alone", "test_fake_flaky.py: failed in the run, passed alone" in out)

code, out = runner({"test_fake_ok.py": OK, "test_fake_flaky.py": FLAKY})
check("without the option the flaky file fails the run, no rerun", code == 1 and "RERUN" not in out, f"exit {code}")

# a file that only went over its time limit is reported as time only, and is cleared when it fits the limit alone
fake_run = lambda path, port: (os.path.basename(path), 5.0, [], 3)
real, run_all.run_one = run_all.run_one, fake_run
try:
    sentence = "test_fake_slow.py took 200 s, over the 180 s limit (recorded 100 s)"
    got = run_all.rerun_alone({}, {"test_fake_slow.py": sentence}, 0, {"files": {"test_fake_slow.py": 100}}, 1.0)
finally:
    run_all.run_one = real
ok, line = got["test_fake_slow.py"]
check("a time-only file that is fast alone is cleared and labelled time only", ok and "time only" in line and "200 s" in line and "180 s" in line, line)

sys.exit(1 if bad else 0)
