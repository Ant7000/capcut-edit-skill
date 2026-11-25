"""Edit a CapCut project's main track as it is right now, keeping every change you made by hand.

  python3 capcut_maintrack.py show "project"                      list the main-track clips with their numbers
  python3 capcut_maintrack.py build "project" EDITLIST.json [--dry-run]
                                                                  first cut into an EMPTY project
  python3 capcut_maintrack.py apply "project" EDITS.json [--dry-run]
                                                                  insert, delete or trim clips

build: puts every clip of an edit list (from assemble_takes.py and tighten_gaps.py) on the main track, in order,
at the voice volume in settings.json. It adds the files to the media bin first. It refuses if the main track
already has clips: rebuilding over a project would throw away hand edits, so later changes go through apply.

apply: EDITS.json is a list of operations, applied in order. Indexes are the numbers `show` prints, and each
operation sees the result of the ones before it. Each names the file it expects at that index ("file"), and the
script stops if the project doesn't match, so an old plan can't hit the wrong clip.

  {"op": "insert", "index": 3, "path": "/Users/you/Movies/.../clip.mov", "src_start": 1.0, "duration": 2.0}
      a new clip before clip 3 (index = number of clips adds it at the end). Optional "volume" (linear gain,
      1.0 = as recorded). The file must be under ~/Movies (capcut_import.py copies it there).
  {"op": "delete", "index": 5, "file": "clip.mov"}
  {"op": "trim", "index": 2, "file": "clip.mov", "src_start": 1.6, "duration": 0.8}
      new source in-point and length. Refuses clips with a speed change or ramp: those were set by hand,
      so trim them in CapCut.

Ripple: everything after the change moves with it, on every track, so graphics stay on their words. Anything on
another track that crosses the change point moves with whichever side holds most of it, and the report says so.

Safety: refuses while CapCut is open; backs up the whole project folder before writing.
"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import capcut_project as rc  # noqa: E402

PHOTO = rc.PHOTO
SUPPORT = rc.SUPPORT


def has_main(d):
    return bool(d["tracks"]) and d["tracks"][0].get("type") == "video" and d["tracks"][0].get("flag", 0) == 0


def load(project_dir, create=False):
    d = json.loads((project_dir / "draft_info.json").read_text())
    mats = {m["id"]: (k, m) for k, lst in d["materials"].items() if isinstance(lst, list)
            for m in lst if isinstance(m, dict) and "id" in m}
    if not has_main(d):
        if not create:
            sys.exit("This project has no main track yet. Build the first cut with: capcut_maintrack.py build")
        d["tracks"].insert(0, {"attribute": 0, "flag": 0, "id": rc.uid(), "is_default_name": True,
                               "name": "", "segments": [], "type": "video"})
    return d, mats


def fname(seg, mats):
    k, m = mats.get(seg["material_id"], ("?", {}))
    return Path(m.get("path", "")).name or m.get("name", "") or k


def speed_note(seg, mats):
    for r in seg.get("extra_material_refs", []):
        k, m = mats.get(r, ("", {}))
        if k == "speeds":
            if m.get("curve_speed") or m.get("mode", 0) != 0:
                return "speed ramp"
            if abs(float(m.get("speed", 1.0)) - 1.0) > 1e-6:
                return f"speed {m['speed']}x"
    if abs(float(seg.get("speed", 1.0)) - 1.0) > 1e-6:
        return f"speed {seg['speed']}x"
    return ""


def show(d, mats):
    for i, s in enumerate(d["tracks"][0]["segments"]):
        tt, st = s["target_timerange"], s.get("source_timerange") or {}
        note = speed_note(s, mats)
        print(f"  {i:3}  {tt['start']/1e6:8.3f}s  {tt['duration']/1e6:6.3f}s  from {st.get('start', 0)/1e6:7.3f}s  "
              f"{fname(s, mats)}{'  [' + note + ']' if note else ''}")
    for ti, t in enumerate(d["tracks"][1:], 1):
        print(f"  track {ti} ({t['type']}{', ' + t['name'] if t.get('name') else ''}): {len(t['segments'])} clips")
    print(f"  length {d['duration']/1e6:.3f}s")


_HELD = set()   # segments ripple leaves alone (full-length adjustment layers, reset afterwards)


def ripple(d, at_us, delta_us, log, skip=None):
    """Move everything on every track that starts at or after at_us by delta_us."""
    for ti, t in enumerate(d["tracks"]):
        for s in t["segments"]:
            if s is skip or id(s) in _HELD:
                continue
            tt = s["target_timerange"]
            if tt["start"] >= at_us:
                tt["start"] += delta_us
            elif ti and tt["start"] + tt["duration"] > at_us:
                # Crosses the change point, like a wipe that starts just before its card.
                # It belongs with whichever side holds most of it.
                after = tt["start"] + tt["duration"] - at_us
                if after * 2 > tt["duration"]:
                    tt["start"] += delta_us
                    log.append(f"  note: track {ti} clip crossing the change point moved with what follows "
                               f"(now {tt['start']/1e6:.3f}s)")
                else:
                    log.append(f"  note: track {ti} clip at {tt['start']/1e6:.3f}s crosses the change point; "
                               "most of it is before, so it stays")


def check(seg, op, mats, i):
    want = op.get("file")
    if want and fname(seg, mats) != want:
        sys.exit(f"Clip {i} is {fname(seg, mats)}, not {want}. The project has changed: run show and redo the plan.")


def apply(d, mats, ops, log):
    main = d["tracks"][0]["segments"]
    # Adjustment layers (colour) that span the whole edit should still span it afterwards: a ripple drags them.
    whole = [s for t in d["tracks"] if t.get("type") == "adjust" for s in t["segments"]
             if s["target_timerange"]["start"] == 0 and s["target_timerange"]["duration"] >= d.get("duration", 0) - 2000]
    _HELD.update(id(s) for s in whole)
    for op in ops:
        kind = op["op"]
        if kind == "insert":
            i = op["index"]
            if not 0 <= i <= len(main):
                sys.exit(f"insert: index {i} is out of range (0 to {len(main)})")
            at = main[i]["target_timerange"]["start"] if i < len(main) else max(
                (s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in main), default=0)
            path = op["path"]
            if not Path(path).exists():
                sys.exit(f"insert: {path} doesn't exist")
            if Path.home() / "Movies" not in Path(path).absolute().parents and not op.get("_dry_copy"):
                sys.exit(f"insert: {Path(path).name} is outside ~/Movies, so CapCut can't read it. "
                         "Add it with capcut_import.py and use the copied path.")
            dur, src = rc.us(op["duration"]), rc.us(op.get("src_start", 0))
            mat = next((m for k, m in mats.values() if k == "videos" and m.get("path") == path), None)
            if mat is None:
                mat = rc.new_video_material(path)
                d["materials"].setdefault("videos", []).append(mat)
                mats[mat["id"]] = ("videos", mat)
            if mat.get("type") == "photo":
                src = 0
            if mat.get("type") != "photo" and src + dur > mat.get("duration", 0) + 2000:
                sys.exit(f"insert: {Path(path).name} is only {mat['duration']/1e6:.2f}s long")
            extras = rc.support_materials(d["materials"])
            for obj, key in zip(extras, SUPPORT):
                mats[obj["id"]] = (key, obj)
            seg = rc.segment(mat["id"], at, dur, src, dur, volume=float(op.get("volume", common.settings()["edit"]["voice_volume"])), extra_material_refs=[o["id"] for o in extras])
            ripple(d, at, dur, log)
            main.insert(i, seg)
            log.append(f"  insert  {i:3}  {at/1e6:8.3f}s  {dur/1e6:6.3f}s  {Path(path).name}; later clips move +{dur/1e6:.3f}s")
        elif kind == "delete":
            i = op["index"]
            seg = main[i]
            check(seg, op, mats, i)
            tt = seg["target_timerange"]
            main.pop(i)
            end = tt["start"] + tt["duration"]
            for t in d["tracks"][1:]:
                for s in t["segments"]:
                    if id(s) not in _HELD and tt["start"] <= s["target_timerange"]["start"] < end:
                        log.append(f"  note: {fname(s, mats)} sat over the deleted clip; left at "
                                   f"{s['target_timerange']['start']/1e6:.3f}s")
            ripple(d, end, -tt["duration"], log)
            log.append(f"  delete  {i:3}  {tt['start']/1e6:8.3f}s  {tt['duration']/1e6:6.3f}s  {fname(seg, mats)}; "
                       f"later clips move -{tt['duration']/1e6:.3f}s")
        elif kind == "trim":
            i = op["index"]
            seg = main[i]
            check(seg, op, mats, i)
            note = speed_note(seg, mats)
            if note:
                sys.exit(f"trim: clip {i} ({fname(seg, mats)}) has a {note}, set by hand. Trim it in CapCut.")
            tt, st = seg["target_timerange"], seg["source_timerange"]
            new_dur = rc.us(op["duration"])
            new_src = rc.us(op["src_start"]) if "src_start" in op else st["start"]
            k, m = mats[seg["material_id"]]
            if m.get("type") != "photo" and new_src + new_dur > m.get("duration", 0) + 2000:
                sys.exit(f"trim: {fname(seg, mats)} is only {m['duration']/1e6:.2f}s long")
            delta = new_dur - tt["duration"]
            end = tt["start"] + tt["duration"]
            ripple(d, end, delta, log, skip=seg)
            tt["duration"] = new_dur
            seg["source_timerange"] = {"start": new_src, "duration": new_dur}
            log.append(f"  trim    {i:3}  {fname(seg, mats)} now from {new_src/1e6:.3f}s for {new_dur/1e6:.3f}s; "
                       f"later clips move {delta/1e6:+.3f}s")
        else:
            sys.exit(f"Unknown op {kind!r}")
    for ti, t in enumerate(d["tracks"]):
        t["segments"].sort(key=lambda s: s["target_timerange"]["start"])
        for s in t["segments"]:
            s["track_render_index"] = ti
    for a, b in zip(main, main[1:]):
        if a["target_timerange"]["start"] + a["target_timerange"]["duration"] > b["target_timerange"]["start"] + 2000:
            sys.exit("Main-track clips would overlap. Nothing written.")
    main_end = max((s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in main), default=0)
    for s in whole:
        s["target_timerange"].update(start=0, duration=main_end)
        if s.get("source_timerange"):
            s["source_timerange"].update(start=0, duration=main_end)
        log.append(f"  adjustment layer kept at full length ({main_end/1e6:.3f}s)")
    d["duration"] = max((s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                         for t in d["tracks"] for s in t["segments"]), default=0)


def build_ops(project_name, editlist, dry):
    """Insert operations for every clip of an edit list, after adding the files to the media bin."""
    import capcut_import
    clips = [c for c in json.loads(Path(editlist).read_text())["clips"] if not c.get("missing")]
    files = list(dict.fromkeys(c["path"] for c in clips))
    paths = dict(zip(files, capcut_import.import_files(project_name, files, dry=dry)))
    ops = []
    for n, c in enumerate(clips):
        p = paths[c["path"]]
        op = {"op": "insert", "index": n, "path": p, "src_start": c["src_in"],
              "duration": round(c["src_out"] - c["src_in"], 6)}
        if dry and not Path(p).exists():      # the copy into ~/Movies only happens on the real run
            op.update(path=c["path"], _dry_copy=True)
        ops.append(op)
    return ops


def snap_ops(ops, rate):
    """Keep clip lengths and in-points on whole frames, so CapCut doesn't open with hairline gaps."""
    for op in ops:
        if op["op"] in ("insert", "trim"):
            op["duration"] = max(1 / rate, common.frame(op["duration"], rate))
            if "src_start" in op:
                op["src_start"] = common.frame(op["src_start"], rate)
    return ops


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) < 2 or args[0] not in ("show", "apply", "build"):
        sys.exit(__doc__)
    project_dir = common.find_project(args[1])
    if args[0] == "show":
        d, mats = load(project_dir)
        show(d, mats)
        return
    if len(args) < 3:
        sys.exit(__doc__)
    if not dry:
        common.require_closed()
    else:
        common.warn_if_open()
    if args[0] == "build":
        d, mats = load(project_dir, create=True)
        if d["tracks"][0]["segments"]:
            sys.exit("The main track already has clips. To keep your hand edits, change it with apply, not build.")
        ops = build_ops(args[1], args[2], dry)
        d, mats = load(project_dir, create=True)   # re-read: the import may have written the media bin
    else:
        d, mats = load(project_dir)
        ops = json.loads(Path(args[2]).read_text())
    snap_ops(ops, common.fps(d))
    log = []
    apply(d, mats, ops, log)
    print("\n".join(log[:60] + ([f"  ... and {len(log) - 60} more"] if len(log) > 60 else [])))
    print("Result:")
    show(d, mats)
    if dry:
        print("Dry run, nothing written.")
        return
    bk = common.backup(project_dir)
    rc.write_project(project_dir, d)
    print(f"Written. Backup: {bk}")


if __name__ == "__main__":
    main()
