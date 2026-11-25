"""Place a timed graphics plan in CapCut: one graphic at a time, no flashes, on whole frames.

  python3 place_graphics.py "project" PLAN.json [--dry-run]

PLAN.json is the output of time_graphics.py, with a "file" for every graphic (make_graphics.py fills it in for
the ones it makes). Each graphic starts at its "at" (moved up to "early" seconds before its word, from
settings.json) and runs to its "end", or for "length" seconds, or the look's default for its kind.

Full-screen graphics go on the first track in "full_frame_tracks", overlays on the first in "overlay_tracks"
(or a "track" you give an item). Then, on the full-screen track:
  1. one at a time: where two overlap, the earlier is cut back to meet the later;
  2. no flashes: a gap shorter than "min_gap" is closed by holding the earlier graphic longer, if its file has
     the frames (every made graphic has a held tail for this); otherwise it's listed as a FLASH to fix.
  3. an end that falls just short of a cut (within 0.6s) is moved onto the cut when the file allows.
Overlays are then cut around full-screen graphics, and pieces under 1s are dropped.

The tracks this writes are replaced as a whole, so keep anything you place by hand on other tracks.
Files are added to the media bin first. Refuses while CapCut is open; backs up the project first.
Run check_placement.py afterwards.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import capcut_project as rc  # noqa: E402
import capcut_import  # noqa: E402

DEFAULT_LENGTH = {"word": 2.5, "title": 3.0, "overlay": 4.0, "file": 3.0}


def file_len(path):
    return 10_800.0 if Path(path).suffix.lower() in rc.PHOTO else rc.probe_us(path) / 1e6


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) < 2:
        sys.exit(__doc__)
    s = common.settings()
    G = s["graphics"]
    look = s.get("look") or {}
    pdir = common.find_project(args[0])
    if dry:
        common.warn_if_open()
    d = common.load_draft(pdir)
    rate = common.fps(d)
    snap = lambda t: common.frame(t, rate)
    cuts = [g["target_timerange"]["start"] / 1e6 for g in d["tracks"][0]["segments"][1:]] if d["tracks"] else []
    plan = json.loads(Path(args[1]).read_text())["graphics"]
    report, full, over = [], [], []
    for g in plan:
        if "at" not in g:
            report.append(f"skipped {g.get('id')}: no time (anchor not found)")
            continue
        if not g.get("file") or not Path(g["file"]).exists():
            report.append(f"skipped {g.get('id')}: no file yet (make it, or add your own)")
            continue
        kind = g.get("kind", "file")
        is_full = g.get("full_screen", kind in ("word", "title"))
        a = snap(max(0.0, g["at"] - G["early"]))
        length = (g["end"] - a) if "end" in g else g.get("length") or look.get("lengths", {}).get(kind) \
            or DEFAULT_LENGTH.get(kind, 3.0)
        flen = file_len(g["file"])
        item = {"id": g.get("id", "?"), "path": g["file"], "a": a, "b": snap(a + min(length, flen)),
                "max": flen, "track": g.get("track")}
        (full if is_full else over).append(item)
    full.sort(key=lambda x: x["a"])
    for x, y in zip(full, full[1:]):
        if x["b"] > y["a"]:
            x["b"] = y["a"]
            if x["b"] - x["a"] < 1.0:
                report.append(f"SHORT  {x['id']} is only {x['b'] - x['a']:.2f}s before {y['id']} starts")
    for x, y in zip(full, full[1:]):
        gap = y["a"] - x["b"]
        if 0.001 < gap < G["min_gap"]:
            if x["a"] + x["max"] >= y["a"]:
                x["b"] = y["a"]
                report.append(f"closed a {gap:.2f}s flash after {x['id']} (held it longer)")
            else:
                report.append(f"FLASH  {gap:.2f}s between {x['id']} and {y['id']} at {common.tc(x['b'])}")
    for n, x in enumerate(full):
        nxt = full[n + 1]["a"] if n + 1 < len(full) else 1e9
        c = min(cuts, key=lambda t: abs(t - x["b"])) if cuts else None
        if c is not None and 0.001 < c - x["b"] <= 0.6 and c <= nxt and x["a"] + x["max"] >= c:
            x["b"] = snap(c)
    windows = [(x["a"], x["b"]) for x in full]
    opieces = []
    for o in sorted(over, key=lambda x: x["a"]):
        pieces = [(o["a"], o["b"])]
        for wa, wb in windows:
            new = []
            for p, q in pieces:
                if wb <= p or wa >= q:
                    new.append((p, q))
                    continue
                if wa > p:
                    new.append((p, wa))
                if wb < q:
                    new.append((wb, q))
            pieces = new
        kept = [(p, q) for p, q in pieces if q - p >= 1.0]
        if len(kept) < len(pieces):
            report.append(f"overlay {o['id']}: dropped {len(pieces) - len(kept)} piece(s) under 1s")
        opieces += [dict(o, a=p, b=q, src=round(p - o["a"], 3)) for p, q in kept]

    tracks = {}
    for x in full:
        tracks.setdefault(x["track"] or G["full_frame_tracks"][0], []).append(x)
    for x in opieces:
        tracks.setdefault(x["track"] or G["overlay_tracks"][0], []).append(x)
    files = sorted({x["path"] for xs in tracks.values() for x in xs})
    paths = dict(zip(files, capcut_import.import_files(args[0], files, dry=dry, quiet=True))) if files else {}
    if not dry:
        common.require_closed()
        d = common.load_draft(pdir)   # re-read after the import
    in_bin = rc.media_bin(pdir) | (set(paths.values()) if dry else set())
    for name, xs in tracks.items():
        clips = [{"path": paths[x["path"]], "start": x["a"], "duration": round(x["b"] - x["a"], 6),
                  "src_start": x.get("src", 0.0)} for x in xs]
        if dry:
            for c in clips:
                if not Path(c["path"]).exists():   # copy into ~/Movies happens on the real run
                    c["path"] = next(k for k, v in paths.items() if v == c["path"])
                    in_bin.add(c["path"])
        report += rc.set_track(d, name, clips, in_bin)
    print("\n".join(report) or "nothing to place")
    if dry:
        print("Dry run, nothing written.")
        return
    bk = common.backup(pdir)
    rc.write_project(pdir, d)
    print(f"Written. Backup: {bk}\nNow run: check_placement.py \"{args[0]}\"")


if __name__ == "__main__":
    main()
