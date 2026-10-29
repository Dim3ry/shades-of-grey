"""T4 test for the test runner itself: the time limits follow the speed of the machine, without hiding real growth.

No browser. It calls run_all.check_budget with made-up timings:
1. On the machine the budget was recorded on (factor 1), a file or run within its limits passes and a much slower one fails.
2. On a machine twice as slow (factor 2), every file taking twice its recorded time still passes, and the whole run too.
3. On that slow machine a file at 6 times its recorded time still gets a warning (it is growing, not just the machine), and one over
   twice the 180 s fail line still fails.
4. The factor is the measured speed over the recorded reference, kept between 0.8 and 3; SOG_TIME_FACTOR overrides it.
5. The default number of files at once follows the number of cores, between 2 and 8."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_all

results = []

def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))

BUDGET = {"files": {"test_a.py": 40, "test_b.py": 100, "test_c.py": 20}, "fail_overrides": {"test_b.py": 240},
          "total_warn_minutes": 12, "total_fail_minutes": 16, "calibration_seconds": 0.30, "calibration_jobs": 6, "calibration_cores": 4}
JOBS = run_all.DEFAULT_JOBS

def run(times, minutes, factor, total_factor=None):
    return run_all.check_budget(BUDGET, times, {}, minutes * 60, JOBS, factor, total_factor)

warns, fails = run({"test_a.py": 42, "test_b.py": 105, "test_c.py": 21}, 9.9, 1.0)
check("at the recorded speed, files near their recorded time and a 9.9 minute run pass without a failure", not fails, fails)
warns, fails = run({"test_a.py": 190, "test_b.py": 105, "test_c.py": 21}, 9.9, 1.0)
check("at the recorded speed, a file over 180 s fails", any("test_a.py" in x for x in fails), fails)
warns, fails = run({"test_a.py": 42, "test_b.py": 105, "test_c.py": 21}, 17, 1.0)
check("at the recorded speed, a 17 minute run fails", any("whole run" in x for x in fails), fails)

warns, fails = run({"test_a.py": 80, "test_b.py": 210, "test_c.py": 40}, 19, 2.0)
check("on a machine twice as slow, every file at twice its recorded time and a 19 minute run pass", not fails, fails)
warns, fails = run({"test_a.py": 240, "test_b.py": 210, "test_c.py": 40}, 19, 2.0)
check("on a machine twice as slow, a file at 6 times its recorded time still gets a warning", any("test_a.py" in x for x in warns), warns)
warns, fails = run({"test_a.py": 400, "test_b.py": 210, "test_c.py": 40}, 19, 2.0)
check("on a machine twice as slow, a file over 2 x 180 s fails", any("test_a.py" in x for x in fails), fails)
warns, fails = run({"test_a.py": 80, "test_b.py": 210, "test_c.py": 40}, 33, 2.0)
check("on a machine twice as slow, a run of 33 minutes (over 2 x 16) still fails", any("whole run" in x for x in fails), fails)

b = dict(BUDGET)
check("the factor is the measured speed over the reference", abs(run_all.time_factor(b, 0.60) - 2.0) < 1e-9)
check("the factor never goes under 0.8 or over 3", run_all.time_factor(b, 0.01) == 0.8 and run_all.time_factor(b, 30) == 3.0)
check("without a recorded reference the factor is 1", run_all.time_factor({}, 0.5) == 1.0)
os.environ["SOG_TIME_FACTOR"] = "1.7"
check("SOG_TIME_FACTOR overrides the measurement", run_all.time_factor(b, 0.30) == 1.7)
del os.environ["SOG_TIME_FACTOR"]
check("the default number of files at once is between 2 and 8", 2 <= run_all.default_jobs() <= 8, run_all.default_jobs())
check("the speed check itself takes a positive time with several copies at once", run_all.calibrate(3) > 0)

print(f"\n{sum(results)} of {len(results)} checks passed")
sys.exit(0 if all(results) else 1)
