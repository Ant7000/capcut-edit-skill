"""Check a cut by listening to it: render the cut's audio, transcribe it again, and list every join where what's
heard differs from what should be there (doubled words, clipped words, restarts the first transcript missed).

  python3 selfcheck_cut.py EDITLIST.json OUT.wav [SCRIPT.txt]

Also lists every silence over 0.5s anywhere in the cut. With SCRIPT.txt it lists every run of 3+ script words
that isn't in the cut, so a lost line shows up. Fix what it finds, then run it again until it's clean.

Extra lead-in words ("so", "and") show up as differences too; they're usually fine. Doubles, swaps and missing
words at a join are the ones to fix. A clean transcript isn't proof a join sounds right: listen to anything odd.
"""
import json, subprocess, sys, wave, difflib
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import assemble_takes as A  # noqa: E402
from transcribe import transcribe  # noqa: E402


def audio(path, cache={}):
    if path not in cache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, stdin=subprocess.DEVNULL).stdout
        cache[path] = np.frombuffer(raw, np.int16)
    return cache[path]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    el, out = sys.argv[1], sys.argv[2]
    clips = [c for c in json.load(open(el))["clips"] if not c.get("missing")]
    segs, joins, t = [], [], 0.0
    for c in clips:
        s = audio(c["path"])[int(c["src_in"] * 16000):int(c["src_out"] * 16000)]
        segs.append(s); t += len(s) / 16000; joins.append(t)
    o = wave.open(out, "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000)
    o.writeframes(np.concatenate(segs).tobytes()); o.close()
    got = [(tok, w["start"]) for w in transcribe(out) for tok in A.norm(w.get("punctuated_word", w["word"]))]
    # expected words: from each take's own word file, every word whose middle falls inside the clip
    tw = {}
    exp, jidx = [], []
    for c in clips:
        if c["path"] not in tw:
            tw[c["path"]] = transcribe(c["path"])
        for w in tw[c["path"]]:
            if c["src_in"] <= (w["start"] + w["end"]) / 2 < c["src_out"]:
                exp += A.norm(w.get("punctuated_word", w["word"]))
        jidx.append(len(exp))
    sm = difflib.SequenceMatcher(None, exp, [g[0] for g in got], autojunk=False)
    n = 0
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        near = [k for k, j in enumerate(jidx[:-1]) if a0 - 2 <= j <= a1 + 2]
        if not near:
            continue
        n += 1
        k = near[0]
        print(f"join {k:3}->{k + 1:3} at {int(joins[k] // 60)}:{joins[k] % 60:04.1f}  {op:7} expected '{' '.join(exp[max(0, a0 - 3):a1 + 3])}'"
              f"  heard '{' '.join(g[0] for g in got[max(0, b0 - 3):b1 + 3])}'")
    print(f"{n} differences at {len(clips) - 1} joins; cut is {int(t // 60)}:{t % 60:04.1f}")
    a = np.concatenate(segs).astype(np.float32)
    env = np.sqrt((a[:len(a) // 160 * 160].reshape(-1, 160) ** 2).mean(1))
    loud = np.median(env[env > np.percentile(env, 60)])
    run, gaps = 0, []
    for i, v in enumerate(env < loud * 0.06):
        if v:
            run += 1
            continue
        if run >= 50:
            gaps.append(((i - run) / 100, run / 100))
        run = 0
    if len(sys.argv) > 3:
        body, _ = A.split_script(Path(sys.argv[3]).read_text())
        script = [tok for s in A.sentences(body) if "text" in s for tok in A.norm(s["text"])]
        cut = [g[0] for g in got]
        sm2 = difflib.SequenceMatcher(None, script, cut, autojunk=False)
        lost = 0
        for op, a0, a1, b0, b1 in sm2.get_opcodes():
            if op in ("delete", "replace") and a1 - a0 >= 3:
                at = got[min(b0, len(got) - 1)][1]
                lost += 1
                gone = script[a0:a1]
                shown = " ".join(gone[:20]) + (f" ... ({len(gone)} words)" if len(gone) > 20 else "")
                print(f"script words not in the cut at {int(at // 60)}:{at % 60:04.1f}: '{shown}'"
                      + (f" (cut has '{' '.join(cut[b0:b1])}')" if b1 > b0 else ""))
        print(f"{lost} runs of script words missing (check whether they were said at all)")
    for s, L in gaps:
        print(f"gap {L:.1f}s at {int(s // 60)}:{s % 60:04.1f}")
    print(f"{len(gaps)} silences over 0.5s")


if __name__ == "__main__":
    main()
