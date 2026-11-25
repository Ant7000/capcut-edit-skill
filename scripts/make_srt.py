"""Subtitles (SRT) from a word-timed transcript of the exact file you'll upload.

  python3 make_srt.py WORDS.json OUT.srt [FIXES.json]

WORDS.json  from transcribe.py, run on the final export (never on the takes: the timing must match the upload).
FIXES.json  optional: {"replace": [[["dot","e","n","v"], [".env"]], ...],  word runs -> new words (case and
                                                                       trailing punctuation ignored when matching)
                       "cues": [[start, end, "text"], ...],              hand-made cues; words inside are dropped
                       "drop_before": seconds}                           ignore words before this time
A replacement keeps the first word's start and the last word's end; replacing with [] drops the words.

Cues: one sentence where it fits, at most two balanced lines of max_chars, min_seconds to max_seconds long, broken
at sentence ends, then commas, then the longest pause. Each cue ends 0.25s after its last word or just before the
next cue. Filler words (um, uh) are dropped. Limits come from settings.json ("subtitles").
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

_S = common.settings()["subtitles"]
MAXL, MAXDUR, MINDUR, TAIL, GAP = _S["max_chars"], _S["max_seconds"], _S["min_seconds"], 0.25, 0.04
FILLERS = {"um", "uh", "mm", "hmm", "mhmm"}


def norm(w):
    return re.sub(r"[^\w']", "", w.lower())


def apply_replacements(words, reps):
    for old, new in reps:
        o = [norm(x) for x in old]
        i, out = 0, []
        while i < len(words):
            if [norm(w["word"]) for w in words[i:i + len(o)]] == o:
                run = words[i:i + len(o)]
                tail = re.search(r"[.,?!;:]+$", run[-1]["word"])
                for k, nw in enumerate(new):
                    t = {"word": nw, "start": run[0]["start"], "end": run[-1]["end"]}
                    if k == len(new) - 1 and tail and not re.search(r"[.,?!;:]$", nw):
                        t["word"] += tail.group(0)
                    out.append(t)
                i += len(o)
            else:
                out.append(words[i]); i += 1
        words = out
    return words


def two_lines(text):
    if len(text) <= MAXL:
        return text
    ws = text.split()
    best = None
    for k in range(1, len(ws)):
        a, b = " ".join(ws[:k]), " ".join(ws[k:])
        if len(a) <= MAXL and len(b) <= MAXL:
            score = abs(len(a) - len(b)) - (8 if a.endswith(",") else 0)
            if best is None or score < best[0]:
                best = (score, a + "\n" + b)
    return best[1] if best else None


def split_run(run):
    """Split a run of words into cue-sized pieces."""
    text = " ".join(w["word"] for w in run)
    if two_lines(text) and run[-1]["end"] - run[0]["start"] <= MAXDUR:
        return [run]
    # best break: after a sentence end, else a comma, else the longest pause; keep both halves sensible
    best = None
    for k in range(1, len(run)):
        w = run[k - 1]["word"]
        gap = run[k]["start"] - run[k - 1]["end"]
        score = gap + (3 if re.search(r"[.?!]$", w) else 1.5 if re.search(r"[,;:]$", w) else 0)
        left = len(" ".join(x["word"] for x in run[:k])); right = len(" ".join(x["word"] for x in run[k:]))
        score -= abs(left - right) / 80
        if min(left, right) < 12:
            score -= 2
        if best is None or score > best[0]:
            best = (score, k)
    k = best[1]
    return split_run(run[:k]) + split_run(run[k:])


def tc(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    words_f, out_f = sys.argv[1:3]
    fx = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
    words = json.load(open(words_f))
    words = words["words"] if isinstance(words, dict) else words
    hand = [(float(a), float(b), t) for a, b, t in fx.get("cues", [])]
    words = [w for w in words if w["start"] >= fx.get("drop_before", 0)
             and not any(a - 0.05 <= w["start"] < b for a, b, _ in hand)
             and norm(w["word"]) not in FILLERS]
    words = apply_replacements(words, fx.get("replace", []))
    words = [w for w in words if w["word"].strip()]
    # sentences
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.?!]$", w["word"]) or w["word"].endswith("..."):
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    cues = [(r[0]["start"], r[-1]["end"], " ".join(w["word"] for w in r)) for s in sents for r in split_run(s)]
    cues += hand
    cues.sort()
    # merge a cue too short to read (under 0.8s on screen) into its neighbour when the pair still fits
    merged = True
    while merged:
        merged = False
        for i, (s, e, t) in enumerate(cues):
            nxt = cues[i + 1][0] if i + 1 < len(cues) else e + 10
            if min(max(e + TAIL, s + MINDUR), nxt - GAP) - s >= 0.8:
                continue
            for j in (i + 1, i - 1):
                if 0 <= j < len(cues):
                    a, b = sorted((i, j))
                    txt = cues[a][2].replace("\n", " ") + " " + cues[b][2].replace("\n", " ")
                    if two_lines(txt) and cues[b][1] - cues[a][0] <= MAXDUR + 1:
                        cues[a:b + 1] = [(cues[a][0], cues[b][1], txt)]
                        merged = True
                        break
            if merged:
                break
    out, n = [], 0
    for i, (s, e, t) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else e + 10
        end = min(max(e + TAIL, s + MINDUR), nxt - GAP)
        end = max(end, e) if e < nxt else nxt - GAP
        body = two_lines(t) or t
        n += 1
        out.append(f"{n}\n{tc(s)} --> {tc(end)}\n{body}\n")
    open(out_f, "w").write("\n".join(out))
    long = [c for c in cues if len(c[2]) > 2 * MAXL]
    print(f"{n} cues written to {out_f}; {len(long)} over two lines")


if __name__ == "__main__":
    main()
