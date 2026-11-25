"""Shared paths, settings and safety checks for the capcut-edit scripts.

Everything a user sets lives in one visible folder, ~/Movies/CapCut Edit/:
  settings.json    numbers the scripts read (gap lengths, punch-in size, loudness, graphics look ...)
  style-guide.md   how this person likes their videos cut and how their graphics look (Claude reads it)
  lessons.md       corrections the person has made, so the same mistake isn't made twice
  .env             DEEPGRAM_API_KEY=... (never printed, never sent anywhere but Deepgram)
  backups/         a full copy of a CapCut project before every write
  import/          copies of media from outside ~/Movies, so CapCut can open them

It sits inside ~/Movies because CapCut (sandboxed on a Mac) can always read ~/Movies.
"""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HOME = Path(os.environ.get("CAPCUT_EDIT_HOME", Path.home() / "Movies" / "CapCut Edit"))
SETTINGS_FILE = HOME / "settings.json"
DEFAULT_PROJECTS = Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft"

DEFAULTS = {
    "capcut_projects": str(DEFAULT_PROJECTS),
    "transcriber": "deepgram",
    "edit": {
        "max_pause": 0.45,          # a silence inside a clip longer than this is closed ...
        "keep_pause": 0.3,          # ... down to this
        "edge": 0.15,               # most quiet left at the head or tail of a clip
        "prefer_later_take": True,  # on a near tie, the later attempt at a line wins
        "keep_adlibs": True,
        "asides": ["okay", "ok", "hang", "alright", "whatever", "blah"],
        "aside_phrases": ["here we go", "let's go", "go again", "one more time", "start again", "from the top"],
        "voice_volume": 1.0,        # CapCut clip volume for the main voice (1.0 = as recorded)
    },
    "joins": {"cover": "punch-in", "punch_in_scale": 1.08},
    "graphics": {
        "full_frame_tracks": ["Full screen"],
        "overlay_tracks": ["Overlays"],
        "min_gap": 1.5,             # less than this of the speaker between two full-screen graphics reads as a flash
        "tail": 2.0,                # every rendered graphic has this much held at the end, so it can be stretched
        "early": 0.2,               # a graphic may land this much before its word
        "per_minute": [4, 8],
        "max_bare": 20.0,           # longest run with no graphic before the checker flags it
    },
    "loudness": {"target_lufs": -14.0, "true_peak": -1.0},
    "subtitles": {"max_chars": 42, "max_seconds": 6.0, "min_seconds": 1.0},
    "quit_capcut_for_me": False,    # true: Claude may quit and reopen CapCut around a change without asking
    "look": None,                   # the person's graphics look, set by the interview (see style-guide.md)
}


def merge(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        out[k] = merge(base[k], v) if isinstance(base.get(k), dict) and isinstance(v, dict) else v
    return out


def settings():
    s = DEFAULTS
    if SETTINGS_FILE.exists():
        try:
            s = merge(DEFAULTS, json.loads(SETTINGS_FILE.read_text()))
        except json.JSONDecodeError as e:
            sys.exit(f"{SETTINGS_FILE} isn't valid JSON ({e}). Fix it or ask Claude to.")
    return s


def projects_dir():
    return Path(os.path.expanduser(settings()["capcut_projects"]))


def find_project(name):
    """A CapCut project folder by its name in CapCut or its folder name. Backups are never matched.
    Stops if there isn't exactly one match, so a write can never land in the wrong project."""
    root = projects_dir()
    if not root.exists():
        sys.exit(f"CapCut's projects folder isn't at {root}. Run the setup check.")
    hits = []
    for meta in root.glob("*/draft_meta_info.json"):
        folder = meta.parent
        if "backup" in folder.name.lower():
            continue
        try:
            draft_name = json.loads(meta.read_text()).get("draft_name", "")
        except Exception:
            draft_name = ""
        if name.lower() in (draft_name.lower(), folder.name.lower()):
            hits.append(folder)
    if len(hits) != 1:
        names = sorted(p.name for p in root.iterdir() if (p / "draft_meta_info.json").exists()
                       and "backup" not in p.name.lower())
        sys.exit(f"Found {len(hits)} CapCut projects called {name!r}. Projects here: {', '.join(names) or 'none'}")
    return hits[0]


def capcut_running():
    return subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0


def require_closed():
    if capcut_running():
        sys.exit("STOPPED: CapCut is still open, so nothing was written.\n"
                 "CapCut has to be fully quit before Claude changes a project: while it's open it saves over the "
                 "files. Closing the window isn't enough. Quit it with Command Q (or say yes when Claude offers "
                 "to quit it for you: capcut_app.py quit), then run this again.")


def warn_if_open():
    """For dry runs: say early that the real run will need CapCut quit."""
    if capcut_running():
        print("NOTE: CapCut is open right now. It must be fully quit (Command Q) before the real run.")


def load_draft(project_dir):
    return json.loads((project_dir / "draft_info.json").read_text())


def backup(project_dir):
    """Copy the whole project folder into ~/Movies/CapCut Edit/backups/ (outside CapCut's own folder,
    so CapCut never lists it and no script can mistake it for the real project)."""
    base = HOME / "backups" / f"{project_dir.name} {time.strftime('%Y%m%d-%H%M%S')}"
    dest, n = base, 1
    while dest.exists():
        n += 1
        dest = base.with_name(f"{base.name}-{n}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(project_dir, dest)
    return dest


def restore(project_dir, backup_dir):
    """Put a backup back. The current state is backed up first, so a restore can be undone too."""
    require_closed()
    safety = backup(project_dir)
    shutil.rmtree(project_dir)
    shutil.copytree(backup_dir, project_dir)
    return safety


def fps(draft):
    return float(draft.get("fps") or 30.0)


def frame(t, rate):
    """Round seconds to a whole frame."""
    return round(round(t * rate) / rate, 6)


def env_key(name="DEEPGRAM_API_KEY"):
    """Read a key from .env in this folder (or a parent), else ~/Movies/CapCut Edit/.env. Never printed."""
    if os.environ.get(name):
        return os.environ[name]
    places = [p / ".env" for p in [Path.cwd(), *Path.cwd().parents]] + [HOME / ".env"]
    for f in places:
        if f.is_file():
            for line in f.read_text().splitlines():
                m = re.match(rf"\s*(?:export\s+)?{name}\s*=\s*['\"]?([^'\"\s#]+)", line)
                if m:
                    return m.group(1)
    return None


def transcripts_dir():
    """Word files are kept next to the video's other files, in ./transcripts/."""
    d = Path.cwd() / "transcripts"
    return d


def tc(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"
