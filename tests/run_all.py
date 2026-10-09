"""Runs every test file in this folder, one after another, and fails loudly if any check fails.

How to run it (from the repo folder):
    python3 tests/run_all.py

What it does:
1. Finds a free port on this computer, so it never clashes with another server.
2. Starts a small local web server that serves the repo folder.
3. Runs each tests/test_*.py file, telling it which port to use.
4. Prints a summary and exits with code 1 if any file failed (0 if all passed).
"""
import os, socket, subprocess, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCREENSHOTS = os.path.join(HERE, "screenshots")  # the tests save pictures here; it is git-ignored


def free_port():
    # Asks the system for a free port by binding to port 0, then releases it.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    port = free_port()
    os.makedirs(SCREENSHOTS, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                              cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)  # give the server a moment to start
    env = dict(os.environ, SOG_PORT=str(port))
    failed = []
    try:
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            name = os.path.basename(path)
            print(f"\n===== {name} (port {port}) =====", flush=True)
            try:
                run = subprocess.run([sys.executable, path, SCREENSHOTS], env=env, cwd=REPO,
                                     timeout=900)
                if run.returncode != 0:
                    failed.append(f"{name} (exit code {run.returncode})")
            except subprocess.TimeoutExpired:
                failed.append(f"{name} (took longer than 15 minutes)")
    finally:
        server.terminate()

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
