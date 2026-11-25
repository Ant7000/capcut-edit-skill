"""Is CapCut running? Quit it properly, wait for it, or open it again.

  python3 capcut_app.py status        says whether CapCut is running
  python3 capcut_app.py quit          asks CapCut to quit, the same as Command Q, and waits until it has
  python3 capcut_app.py wait [MINS]   waits (default 5 minutes) for the person to quit it themselves
  python3 capcut_app.py open          opens CapCut again after a change

Why this matters: while CapCut is open it keeps the project in memory and saves over the files whenever it
likes, so anything written while it's open is lost. Closing the window isn't enough; the app has to quit.

Only quit CapCut for someone after they've said yes (or set "quit_capcut_for_me": true in settings.json).
The first time, macOS may ask whether Claude may control CapCut: they click OK.
CapCut saves as it goes, but if it shows a "save?" box, the quit waits for them to answer it.
"""
import subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402


def wait_closed(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if not common.capcut_running():
            return True
        time.sleep(1)
    return not common.capcut_running()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "status":
        print("CapCut is running." if common.capcut_running() else "CapCut is not running.")
    elif cmd == "quit":
        if not common.capcut_running():
            print("CapCut is not running.")
            return
        # A CapCut that's still starting up, or a first-time permission box, can refuse the request: retry.
        for _ in range(20):
            r = subprocess.run(["osascript", "-e", 'tell application "CapCut" to quit'], capture_output=True, text=True)
            if r.returncode == 0:
                break
            time.sleep(1.5)
        else:
            sys.exit("macOS didn't let me quit CapCut. If a box asked whether Claude may control CapCut, click OK "
                     "and ask me again; or quit it yourself with Command Q.")
        if wait_closed(30):
            print("CapCut has quit.")
        else:
            sys.exit("CapCut is still open, perhaps waiting on a question on screen. Answer it, or quit with Command Q.")
    elif cmd == "wait":
        mins = float(sys.argv[2]) if len(sys.argv) > 2 else 5
        print("Waiting for CapCut to quit (Command Q in CapCut)...", flush=True)
        if wait_closed(mins * 60):
            print("CapCut has quit.")
        else:
            sys.exit(f"CapCut is still running after {mins:g} minutes.")
    elif cmd == "open":
        subprocess.run(["open", "-a", "CapCut"])
        print("Opening CapCut.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
