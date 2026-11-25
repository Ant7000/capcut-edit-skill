"""Close long silences inside clips: waits for the teleprompter, lost places, long breaths.

  python3 tighten_gaps.py EDITLIST.json OUT.json [--max 0.45] [--keep 0.3]

Reads the waveform, not the transcript (which can miss sounds or invent gaps). Inside each clip, any stretch
quieter than 6% of the whole cut's speech level and longer than --max seconds is cut down to --keep seconds:
half after the last sound, half before the next. The clip is split in two there. The head and tail of each
clip are trimmed to "edge" seconds of quiet, so a join never stacks two pauses. One speech level is used for
the whole cut, because takes recorded at different times differ in level.

Defaults come from settings.json ("edit": max_pause, keep_pause, edge), which the style interview sets.
Run after assemble_takes.py and before selfcheck_cut.py.
"""
import json, sys, argparse
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import assemble_takes as A  # noqa: E402

S = common.settings()["edit"]
EDGE = S["edge"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("editlist"); ap.add_argument("out")
    ap.add_argument("--max", type=float, default=S["max_pause"]); ap.add_argument("--keep", type=float, default=S["keep_pause"])
    a = ap.parse_args()
    d = json.load(open(a.editlist))
    envs, out, n, saved = {}, [], 0, 0.0
    # one speech level for the whole cut (takes recorded at different times differ in level, and a clip's own
    # level misses breaths and room noise between lines); same test the self-check uses
    allseg = []
    for c in d["clips"]:
        if c.get("missing"): continue
        if c["path"] not in envs:
            envs[c["path"]] = A.envelope(c["path"])
        allseg.append(envs[c["path"]][int(c["src_in"] * 100):int(c["src_out"] * 100)])
    alle = np.concatenate(allseg)
    LOUD = np.median(alle[alle > np.percentile(alle, 60)])
    for c in d["clips"]:
        if c.get("missing"):
            out.append(c); continue
        if c["path"] not in envs:
            envs[c["path"]] = A.envelope(c["path"])
        i0, i1 = int(c["src_in"] * 100), int(c["src_out"] * 100)
        e = envs[c["path"]][i0:i1]
        quiet = e < LOUD * 0.06
        cuts, run = [], 0
        for i, v in enumerate(quiet):
            if v:
                run += 1
                continue
            if run >= a.max * 100 and i - run > 5:      # a gap with sound on both sides
                s, t = (i0 + i - run) / 100, (i0 + i) / 100
                cuts.append((round(s + a.keep / 2, 2), round(t - a.keep / 2, 2)))
            run = 0
        piece_in = c["src_in"]
        for k, (o, nxt) in enumerate(cuts):
            p = dict(c); p["src_in"], p["src_out"] = piece_in, o
            if k: p["text"] = ""
            out.append(p); piece_in = nxt; n += 1; saved += nxt - o
        last = dict(c); last["src_in"] = piece_in
        out_start = len(out)
        if cuts:
            last["text"] = ""; last.setdefault("notes", []).append(f"{len(cuts)} long pause(s) closed inside this clip")
        out.append(last)
    # head and tail: no more than EDGE seconds of quiet at either end of a clip, so joins don't stack two pauses
    for c in out:
        if c.get("missing"): continue
        e = envs[c["path"]]
        i0, i1 = int(c["src_in"] * 100), int(c["src_out"] * 100)
        seg = e[i0:i1]
        if not len(seg): continue
        q = seg < LOUD * 0.06
        h = 0
        while h < len(q) and q[h]: h += 1
        tl = 0
        while tl < len(q) and q[len(q) - 1 - tl]: tl += 1
        if h < len(q):
            if h / 100 > EDGE: c["src_in"] = round(c["src_in"] + h / 100 - EDGE, 2); saved += h / 100 - EDGE
            if tl / 100 > EDGE: c["src_out"] = round(c["src_out"] - tl / 100 + EDGE, 2); saved += tl / 100 - EDGE
    t = 0.0
    for c in out:
        if c.get("missing"): continue
        c["duration"] = round(c["src_out"] - c["src_in"], 2); c["start"] = round(t, 2); t += c["duration"]
    d["clips"] = out; d["length"] = round(t, 2)
    json.dump(d, open(a.out, "w"), indent=1)
    print(f"closed {n} pauses, saved {saved:.1f}s; cut is now {int(t // 60)}:{t % 60:04.1f} in {sum(1 for c in out if not c.get('missing'))} clips")


if __name__ == "__main__":
    main()
