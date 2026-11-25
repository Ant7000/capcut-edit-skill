"""Setup check for capcut-edit. Safe to run any time: it only reports, unless asked to create or test.

  python3 setup_check.py                 check everything and say what's missing
  python3 setup_check.py --init          create ~/Movies/CapCut Edit/ with settings, a style guide, a lessons
                                         file and an empty .env for the Deepgram key (never overwrites)
  python3 setup_check.py --test-key      send one second of silence to Deepgram to prove the key works
  python3 setup_check.py --one-clip "project" CLIP [--dry-run]
                                         the first real test: put the first 10 seconds of CLIP on the
                                         main track of an empty CapCut project
"""
import json, os, platform, plistlib, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

SKILL = Path(__file__).absolute().parent.parent
OK, NO, WARN = "OK  ", "NO  ", "NOTE"
TESTED_CAPCUT = ("9.5", "9.8")


def line(state, text):
    print(f"[{state}] {text}")


def capcut_version():
    for app in (Path("/Applications/CapCut.app"), Path.home() / "Applications/CapCut.app"):
        info = app / "Contents/Info.plist"
        if info.exists():
            with open(info, "rb") as f:
                return app, plistlib.load(f).get("CFBundleShortVersionString", "?")
    return None, None


def check():
    problems = 0
    if platform.system() != "Darwin":
        line(NO, f"This is {platform.system()}. The skill is only tested on a Mac so far.")
        problems += 1
    else:
        line(OK, f"Mac, macOS {platform.mac_ver()[0]}")
    v = sys.version_info
    if v < (3, 9):
        line(NO, f"Python {v.major}.{v.minor} is too old; 3.9 or newer is needed")
        problems += 1
    else:
        line(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            line(OK, f"{tool} found")
        else:
            line(NO, f"{tool} not found. Install FFmpeg (with Homebrew: brew install ffmpeg)")
            problems += 1
    for mod, pkg in (("numpy", "numpy"), ("PIL", "pillow")):
        try:
            __import__(mod)
            line(OK, f"Python package {pkg}")
        except ImportError:
            line(NO, f"Python package {pkg} missing (see references/setup.md, step 2)")
            problems += 1
    app, ver = capcut_version()
    if not app:
        line(NO, "CapCut desktop app not found in Applications")
        problems += 1
    else:
        same = ver.startswith(TESTED_CAPCUT)
        line(OK if same else WARN, f"CapCut {ver}" + ("" if same else
             f" (tested on {' and '.join(TESTED_CAPCUT)}; other versions may store projects differently: run the one-clip test)"))
    root = common.projects_dir()
    if root.exists():
        names = [p.name for p in root.iterdir() if (p / "draft_meta_info.json").exists()
                 and "backup" not in p.name.lower()]
        line(OK, f"CapCut projects folder: {root} ({len(names)} projects)")
    else:
        line(NO, f"CapCut projects folder not found at {root}. Open CapCut once and make a project, or set "
                 f"\"capcut_projects\" in {common.SETTINGS_FILE}")
        problems += 1
    if common.HOME.exists():
        line(OK, f"Your CapCut Edit folder: {common.HOME}")
        for f, what in (("settings.json", "settings"), ("style-guide.md", "style guide"), ("lessons.md", "lessons file")):
            if not (common.HOME / f).exists():
                line(NO, f"No {what} yet ({f}). Run --init")
                problems += 1
        sg = common.HOME / "style-guide.md"
        if sg.exists() and "NOT SET UP YET" in sg.read_text():
            line(WARN, "Style guide not filled in yet: Claude runs the style interview (references/interview.md)")
    else:
        line(NO, f"No CapCut Edit folder yet ({common.HOME}). Run --init")
        problems += 1
    key = common.env_key()
    if key:
        line(OK, "Deepgram key found (not shown). --test-key checks it works")
    else:
        line(NO, f"No Deepgram key. Put DEEPGRAM_API_KEY=your-key in {common.HOME / '.env'}")
        problems += 1
    running = common.capcut_running()
    line(WARN if running else OK, "CapCut is running: quit it (Command Q) before Claude writes to a project"
         if running else "CapCut isn't running")
    print(f"\n{problems} thing(s) to fix." if problems else "\nAll set. Next: the one-clip test.")
    return problems


def init():
    common.HOME.mkdir(parents=True, exist_ok=True)
    made = []
    if not common.SETTINGS_FILE.exists():
        common.SETTINGS_FILE.write_text(json.dumps(common.DEFAULTS, indent=2) + "\n")
        made.append("settings.json")
    for name in ("style-guide.md", "lessons.md"):
        dest = common.HOME / name
        if not dest.exists():
            shutil.copy(SKILL / "templates" / name, dest)
            made.append(name)
    env = common.HOME / ".env"
    if not env.exists():
        env.write_text("# Paste your Deepgram key after the = sign, save, and close. Keep this file private.\n"
                       "DEEPGRAM_API_KEY=\n")
        os.chmod(env, 0o600)
        made.append(".env")
    for sub in ("backups", "import"):
        (common.HOME / sub).mkdir(exist_ok=True)
    print(f"{common.HOME}: created {', '.join(made) if made else 'nothing (everything was already there)'}")


def test_key():
    from transcribe import deepgram
    key = common.env_key()
    if not key:
        sys.exit("No key to test yet.")
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "s.wav"
        with wave.open(str(w), "wb") as o:
            o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000); o.writeframes(b"\0\0" * 16000)
        deepgram(w.read_bytes(), key, [])
    print("Deepgram accepted the key.")


def one_clip(project, clip, dry):
    import capcut_maintrack
    rc = __import__("capcut_project")
    length = min(10.0, rc.probe_us(clip) / 1e6)
    with tempfile.TemporaryDirectory() as tmp:
        el = Path(tmp) / "one.json"
        el.write_text(json.dumps({"clips": [{"path": str(Path(clip).absolute()), "src_in": 0.0, "src_out": length}]}))
        sys.argv = ["capcut_maintrack.py", "build", project, str(el)] + (["--dry-run"] if dry else [])
        capcut_maintrack.main()
    if not dry:
        print("\nOpen CapCut and open the project. If the clip is on the timeline and plays, you're set up.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--init" in a:
        init()
    elif "--test-key" in a:
        test_key()
    elif "--one-clip" in a:
        rest = [x for x in a if x not in ("--one-clip", "--dry-run")]
        if len(rest) != 2:
            sys.exit(__doc__)
        one_clip(rest[0], rest[1], "--dry-run" in a)
    else:
        sys.exit(1 if check() else 0)
