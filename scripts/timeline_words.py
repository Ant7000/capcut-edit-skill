"""Every word heard on the CapCut timeline, at its time in the edit, read from the project as it is now.

  python3 timeline_words.py "project" OUT.json [OUT.md]

For each main-track clip with sound it takes that file's word transcript (transcribing it if it hasn't been)
and maps the words inside the clip onto the timeline, allowing for speed changes. So it stays right after
hand edits. OUT.json is {"words": [{"word", "start", "end"}]} in timeline seconds: what time_graphics.py
uses to find where each graphic's words are said. OUT.md is a readable copy with timecodes.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
from transcribe import transcribe  # noqa: E402


def timeline_words(project):
    d = common.load_draft(common.find_project(project))
    mats = {m["id"]: m for m in d["materials"].get("videos", [])}
    out = []
    for g in d["tracks"][0]["segments"] if d["tracks"] else []:
        m = mats.get(g["material_id"])
        if not m or m.get("type") == "photo" or not m.get("has_audio", True) or g.get("volume", 1) == 0:
            continue
        path = m.get("path", "")
        if not Path(path).exists():
            print(f"skipped (file missing): {path}", file=sys.stderr)
            continue
        tt, st = g["target_timerange"], g["source_timerange"]
        speed = st["duration"] / tt["duration"] if tt["duration"] else 1.0
        a, b = st["start"] / 1e6, (st["start"] + st["duration"]) / 1e6
        t0 = tt["start"] / 1e6
        for w in transcribe(path):
            mid = (w["start"] + w["end"]) / 2
            if a <= mid < b:
                out.append({"word": w["word"], "start": round(t0 + (max(w["start"], a) - a) / speed, 3),
                            "end": round(t0 + (min(w["end"], b) - a) / speed, 3)})
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    words = timeline_words(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps({"project": sys.argv[1], "words": words}, indent=1))
    if len(sys.argv) > 3:
        # one sentence a line, with the time it starts
        lines, cur, start = [], [], None
        for w in words:
            start = w["start"] if start is None else start
            cur.append(w["word"])
            if w["word"].endswith((".", "?", "!")):
                lines.append(f"`{common.tc(start)}` {' '.join(cur)}")
                cur, start = [], None
        if cur:
            lines.append(f"`{common.tc(start)}` {' '.join(cur)}")
        Path(sys.argv[3]).write_text("\n\n".join(lines) + "\n")
    print(f"{len(words)} words on the timeline")
