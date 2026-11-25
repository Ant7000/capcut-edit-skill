"""Punch-ins: hide jump cuts by scaling the clip after a join up a little, so it reads as a new angle.

  python3 capcut_punchins.py "project" [--scale 1.08] [--dry-run]

Plans from the live timeline. Walking the main track, every join that no full-screen graphic covers swaps
between 100% and the punch-in scale; a join under a full-screen graphic resets to 100% (the cutaway hides the
jump). Full-screen tracks and the scale come from settings.json ("graphics": "full_frame_tracks",
"joins": "punch_in_scale"). Re-run it after any change to the cut or the graphics.

Clips you've scaled or moved by hand (any scale other than 100% or the punch-in, or a moved position) are left
exactly as they are.

Refuses while CapCut is open; backs up the project first.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import capcut_project as rc  # noqa: E402

EPS = 1e-6


def plan(d, k, full_names):
    segs = d["tracks"][0]["segments"]
    full = [(g["target_timerange"]["start"], g["target_timerange"]["start"] + g["target_timerange"]["duration"])
            for t in d["tracks"][1:] if t.get("type") == "video" and t.get("name") in full_names
            for g in t["segments"]]
    want, cur = {}, 1.0
    for i, g in enumerate(segs):
        if i == 0:
            cur = 1.0
        else:
            at = g["target_timerange"]["start"]
            covered = any(a - 1000 <= at <= b + 1000 for a, b in full)
            cur = 1.0 if covered else (k if abs(cur - 1.0) < EPS else 1.0)
        want[i] = cur
    return want


def main():
    s = common.settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--scale", type=float, default=s["joins"]["punch_in_scale"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pdir = common.find_project(a.project)
    d = common.load_draft(pdir)
    k = a.scale
    want = plan(d, k, set(s["graphics"]["full_frame_tracks"]))
    changed, kept, punched = 0, [], 0
    for i, g in enumerate(d["tracks"][0]["segments"]):
        c = g["clip"]
        moved = abs(c["transform"]["x"]) > EPS or abs(c["transform"]["y"]) > EPS
        sx = c["scale"]["x"]
        if moved or (abs(sx - 1) > EPS and abs(sx - k) > EPS):
            kept.append(i)
            continue
        if abs(want[i] - 1) > EPS:
            punched += 1
        if abs(sx - want[i]) > EPS:
            c["scale"] = {"x": want[i], "y": want[i]}
            changed += 1
    print(f"{punched} clips punched in to {k:.0%}; {changed} clips change; "
          f"left alone (set by hand): {kept or 'none'}")
    if a.dry_run:
        print("Dry run, nothing written.")
        return
    common.require_closed()
    bk = common.backup(pdir)
    rc.write_project(pdir, d)
    print(f"Written. Backup: {bk}")


if __name__ == "__main__":
    main()
