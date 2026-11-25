"""Find where each graphic in a plan belongs in the edit, from the words you say.

  python3 time_graphics.py PLAN.json TIMELINE_WORDS.json OUT_PLAN.json

PLAN.json: {"graphics": [ITEM, ...]} in the order they appear. Each ITEM:
  "id"       a short name, e.g. "g07"
  "kind"     "word" (full-screen words), "title" (a title or section card), "overlay" (text over you),
             or "file" (a graphic you made elsewhere, in "file")
  "text", "subtitle"   what's on screen, for the kinds this skill makes. Only words you actually say.
  "file"     your own graphic (image or video), for kind "file"
  "full_screen"  true or false (defaults: word and title true, overlay false; say so for a "file")
  "anchor"   the words where it starts, as said, e.g. "the whole edit took"
  "start_after"  true to start when the anchor finishes rather than when it starts
  "until"    optional: the words where it ends (it ends as they finish)
  "length"   optional: seconds on screen, when there's no "until"

TIMELINE_WORDS.json comes from timeline_words.py. Each anchor is searched for after the one before it (most of
the words must match), so a phrase you say twice lands on the right one. Writes the plan with "at" (and "end")
in timeline seconds, and lists anything not found. Nothing in CapCut changes.
"""
import difflib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
from assemble_takes import norm  # noqa: E402


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    plan = json.loads(Path(sys.argv[1]).read_text())
    words = json.loads(Path(sys.argv[2]).read_text())["words"]
    flat = [(tok, w) for w in words for tok in norm(w["word"])]
    toks = [f[0] for f in flat]

    def find(phrase, after_t, end=False):
        p = norm(phrase)
        if not p:
            return None
        start_i = next((i for i, f in enumerate(flat) if f[1]["start"] >= after_t - 0.01), len(flat))
        for i in range(start_i, len(flat)):
            if toks[i] != p[0] and (len(p) < 2 or toks[i] not in p[:2]):
                continue
            if difflib.SequenceMatcher(None, p, toks[i:i + len(p)], autojunk=False).ratio() >= 0.75:
                w = flat[min(i + len(p) - 1, len(flat) - 1)][1] if end else flat[i][1]
                return round(w["end"] if end else w["start"], 3)
        return None

    last, missing = 0.0, []
    for g in plan["graphics"]:
        g.pop("at", None)
        g.pop("end", None)
        at = find(g.get("anchor", ""), last, end=g.get("start_after", False))
        if at is None:
            missing.append(f"{g.get('id')}: \"{g.get('anchor')}\"")
            continue
        g["at"] = at
        last = at
        if g.get("until"):
            e = find(g["until"], at, end=True)
            if e is None:
                missing.append(f"{g.get('id')} end: \"{g['until']}\"")
            else:
                g["end"] = e
        print(f"  {g.get('id', '?'):>6}  {common.tc(at)}" + (f" to {common.tc(g['end'])}" if "end" in g else "")
              + f"  {g.get('kind')}: {g.get('text') or Path(g.get('file', '')).name}")
    Path(sys.argv[3]).write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    print(f"{len(plan['graphics'])} graphics; not found: {', '.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
