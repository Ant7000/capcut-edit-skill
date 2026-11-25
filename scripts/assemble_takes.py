"""First cut from your takes: match every script sentence to what you said, keep the best take of each line,
and cut in the quiet between words.

  python3 assemble_takes.py SCRIPT.txt OUT_EDITLIST.json TAKE.mov [TAKE.mov ...]

SCRIPT.txt is the script as plain text, one paragraph per thought (a teleprompter file works). Lines in
[square brackets] are stage notes and are skipped. Optional voice-over: put [VO Name] where a voice-over
section plays, and after the on-camera script add a line "===== VOICE-OVER =====" followed by
"== Name ==" blocks with one line per sentence. Those lines are pulled into place.

Takes are transcribed first if they haven't been (transcribe.py). For each sentence the script scores every
stretch of every take (difflib), keeps the best and, on a near tie, the later attempt (you usually get it right
on the retry; turn off with "prefer_later_take": false in settings.json). Restarts inside a line are removed
("so I can get so I can still get" keeps the second). Repeats inside a number or name ("four four four four")
are kept. Cuts move to the quietest 10ms near each word edge, because transcript timings can be 0.2s out.

Ad-libs: unscripted words said straight after a kept line, in the same breath (no gap over 0.8s, at most 8
words, finishing as a phrase, not a restart), stay in. Asides ("okay", "hang on", "here we go", and any you add
under "asides" in settings.json) stay out. Every ad-lib kept or left out is listed with its time to check.

Writes an edit list: one clip per kept stretch (path, src_in, src_out, start, duration, text, said, score).
Clips scoring under 0.8 are marked "check". Sentences not found anywhere are marked "missing".
Then run tighten_gaps.py and selfcheck_cut.py.
"""
import json, os, re, subprocess, sys, difflib
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

S = common.settings()["edit"]
ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def say_number(t):
    """Digits as words, so "14" in a transcript matches "fourteen" in a script (up to 99)."""
    n = int(t)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    return t


def norm(s):
    s = s.lower().replace("’", "'").replace("-", " ")
    toks = re.findall(r"[a-z0-9']+", s)
    out = []
    for t in toks:
        if t.isdigit():
            t = say_number(t)
        out += t.split()
    return out


def sentences(text):
    """Script sentences, short ones (one or two words) joined to a neighbour."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    out = []
    for p in paras:
        if p.startswith("[") and p.endswith("]"):
            m = re.match(r"\[(?:SEQUENCE|VO) (\w+)", p)
            if m:
                out.append({"seq": m.group(1)})
            continue
        p = re.sub(r"\[[^\]]*\]", "", p)
        p = re.sub(r"\((say|said)[^)]*\)", "", p)
        parts = [x.strip() for x in re.split(r"(?<=[.?!…])\s+", p) if x.strip()]
        merged = []
        carry = ""
        for x in parts:
            if len(norm(x)) <= 2:
                if merged:
                    merged[-1] += " " + x
                else:
                    carry += x + " "
                continue
            merged.append(carry + x)
            carry = ""
        if carry:
            merged.append(carry.strip())
        out += [{"text": x} for x in merged if norm(x)]
    return out


def load_takes(paths):
    from transcribe import transcribe
    words = []
    for ti, p in enumerate(paths):
        for w in transcribe(p):
            for t in norm(w.get("punctuated_word", w["word"])) or [""]:
                pw = w.get("punctuated_word", w["word"])
                words.append({"take": ti, "tok": t, "start": w["start"], "end": w["end"],
                              "stop": pw.endswith((".", "?", "!")) and not pw.endswith("..."),
                              "abandon": pw.endswith(("...", "…"))})
    return words


def envelope(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, stdin=subprocess.DEVNULL).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)
    n = len(a) // 160
    return np.sqrt((a[:n * 160].reshape(n, 160) ** 2).mean(1))  # 10ms RMS


def quiet(env, lo, hi, prefer):
    """Quietest 10ms in [lo, hi]; on a near tie, the one closest to `prefer`.
    When the words run together (a gap under 0.1s), Deepgram's edges can't be trusted, so look 0.15s either side."""
    if hi - lo < 0.1:
        mid = (lo + hi) / 2
        lo, hi = mid - 0.15, mid + 0.15
    i0, i1 = max(0, int(lo * 100)), min(len(env) - 1, int(hi * 100))
    if i1 <= i0:
        return prefer
    seg = env[i0:i1 + 1]
    floor = seg.min()
    ok = np.where(seg <= floor * 1.5 + 20)[0] + i0
    best = ok[np.argmin(np.abs(ok / 100 - prefer))]
    return round(best / 100, 2)


def best_match(stoks, words):
    n = len(stoks)
    toks = [w["tok"] for w in words]
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(stoks)
    cands = []
    for L in range(max(1, int(n * 0.6)), n + 4):
        for i in range(0, len(toks) - L + 1):
            win = toks[i:i + L]
            if win[0] not in stoks[:3] and win[-1] not in stoks[-3:]:
                continue
            sm.set_seq1(win)
            if sm.real_quick_ratio() < 0.5 or sm.quick_ratio() < 0.5:
                continue
            cands.append((sm.ratio() + (PREFER_BONUS if words[i]["take"] == PREFER_TAKE or 0 <= PREFER_FROM <= words[i]["take"] else 0), i, L))
    if not cands:
        return None
    top = max(c[0] for c in cands)
    # near ties: the latest attempt wins (people fix a line by saying it again). Windows that start close
    # together are the same attempt; within it, the best window, earliest and longest on a tie.
    near = sorted(c for c in cands if c[0] >= top - 0.04)
    near.sort(key=lambda c: c[1])
    groups = [[near[0]]]
    for c in near[1:]:
        if c[1] - groups[-1][-1][1] <= max(3, n // 2):
            groups[-1].append(c)
        else:
            groups.append([c])
    r, i, L = max(groups[-1] if S["prefer_later_take"] else groups[0], key=lambda c: (round(c[0], 2), -c[1], c[2]))
    sm.set_seq1(toks[i:i + L])
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    a0 = i + blocks[0].a
    a1 = i + blocks[-1].a + blocks[-1].size - 1
    if words[a0]["take"] != words[a1]["take"]:
        a1 = max(k for k in range(a0, a1 + 1) if words[k]["take"] == words[a0]["take"])
    return {"i0": a0, "i1": a1, "score": round(r, 3)}


# PREFER_TAKE=N (env): give take N (0-based, in argument order) a head start, so the main read wins unless
# another take's line is clearly better. Fewer takes mixed means fewer jumps between takes.
PREFER_TAKE = int(os.environ.get("PREFER_TAKE", "-1"))
PREFER_FROM = int(os.environ.get("PREFER_FROM", "-1"))   # every take from this index on (one pass split over files)
PREFER_BONUS = float(os.environ.get("PREFER_BONUS", "0.1"))

ASIDE = set(S["asides"])
FILLER = {"uh", "um", "er", "erm"}
ASIDE_PHRASES = list(S["aside_phrases"])


def keep_adlibs(pieces, words):
    """Extend each kept piece over the unscripted words said straight after it (see the docstring)."""
    report = []
    if not S["keep_adlibs"]:
        return report
    real = [p for p in pieces if not p.get("missing")]
    for n, p in enumerate(real):
        nxt = real[n + 1] if n + 1 < len(real) else None
        tk = words[p["i1"]]["take"]
        k, run = p["i1"] + 1, []
        while (k < len(words) and words[k]["take"] == tk and words[k]["start"] - words[k - 1]["end"] < 0.8 and len(run) < 9
               and not (nxt and nxt["i0"] == k)):
            run.append(k); k += 1
        if not run or len(run) > 8:
            continue
        while run and words[run[0]]["tok"] in FILLER:      # trim a leading "uh"
            run = run[1:]
        if not run:
            continue
        toks = [words[j]["tok"] for j in run]
        text = " ".join(toks)
        at = words[run[0]]["start"]
        later = []
        for q in real[max(0, n - 1):n + 3]:          # the line before, this line and the next two
            later += norm(q.get("text") or "")
        reason = None
        if not words[run[-1]]["stop"]:
            reason = "doesn't finish as a phrase"
        elif any(words[j]["abandon"] for j in run):
            reason = "abandoned word"
        elif any(a == b or (len(a) > 2 and b.startswith(a)) for a, b in zip(toks, toks[1:])):
            reason = "stutter"
        elif later and len(toks) >= 2 and sum(1 for x in toks if x in later) / len(toks) >= 0.6:
            reason = "repeats a scripted line"
        if reason:
            report.append({"kept": False, "take": tk, "at": round(at, 2), "words": text, "why": reason}); continue
        if any(t in ASIDE for t in toks) or any(ph in text for ph in ASIDE_PHRASES):
            report.append({"kept": False, "take": tk, "at": round(at, 2), "words": text, "why": "aside or fluff"}); continue
        nxt_toks = [words[j]["tok"] for j in range(nxt["i0"], min(nxt["i0"] + 3, len(words)))] if nxt else []
        own = [words[j]["tok"] for j in range(max(p["i0"], p["i1"] - 8), p["i1"] + 1)]
        if (nxt_toks and toks[:2] == nxt_toks[:2]) or any(toks[:2] == own[i:i + 2] for i in range(len(own) - 1)):
            report.append({"kept": False, "take": tk, "at": round(at, 2), "words": text, "why": "restart"}); continue
        bridges = nxt is not None and k == nxt["i0"]
        if not bridges and k < len(words) and words[k]["take"] == tk and words[k]["start"] - words[k - 1]["end"] < 0.8:
            report.append({"kept": False, "take": tk, "at": round(at, 2), "words": text, "why": "runs on, unclear end"}); continue
        p["i1"] = run[-1]; p["adlib"] = (p.get("adlib", "") + " " + text).strip()
        report.append({"kept": True, "take": tk, "at": round(at, 2), "words": text})
    return report


KEEP_REPEATS = {"no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "very", "really"}


def drop_restarts(words, i0, i1):
    """Word ranges with restarts removed: a phrase said again straight after (any length), or a 3+ word
    phrase repeated within 10 words, keeps only its last saying."""
    keep = list(range(i0, i1 + 1))
    changed = True
    while changed:
        changed = False
        tk = [words[k]["tok"] for k in keep]
        for a in range(len(tk)):
            for k in range(min(6, (len(tk) - a) // 2), 0, -1):
                if tk[a:a + k] == tk[a + k:a + 2 * k] and not all(x in KEEP_REPEATS for x in tk[a:a + k]):
                    del keep[a:a + k]; changed = True; break
            if changed:
                break
            for b in range(a + 1, min(len(tk), a + 11)):
                k = 0
                while b + k < len(tk) and a + k < b and tk[a + k] == tk[b + k]:
                    k += 1
                if k >= 3 and not all(x in KEEP_REPEATS for x in tk[a:a + k]):
                    del keep[a:b]; changed = True; break
            if changed:
                break
    ranges = []
    for k in keep:
        if ranges and k == ranges[-1][1] + 1:
            ranges[-1][1] = k
        else:
            ranges.append([k, k])
    return ranges


def split_script(text):
    """(on-camera part, voice-over part). The voice-over part starts at a line of ===== ... ===== naming
    VOICE-OVER or PART 2; an optional "===== ... PART 1 ... =====" line before the script is dropped."""
    m = re.search(r"^=====[^\n]*(VOICE-OVER|PART 2)[^\n]*=====[^\n]*$", text, re.M)
    p1, p2 = (text[:m.start()], text[m.end():]) if m else (text, "")
    h = re.search(r"^=====[^\n]*PART 1[^\n]*=====[^\n]*$", p1, re.M)
    if h:
        p1 = p1[h.end():]
    return p1, p2


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    tp, out, takes = sys.argv[1], sys.argv[2], sys.argv[3:]
    p1, p2 = split_script(Path(tp).read_text())
    vo = {}
    parts = re.split(r"\n== (\w+)[^=\n]*==\n", "\n" + p2)   # headers may carry a length: "== TheCut (14 seconds) =="
    for name, body in zip(parts[1::2], parts[2::2]):
        vo[name] = [l.strip() for l in body.splitlines() if l.strip()]
    plan = []
    for s in sentences(p1):
        if "seq" in s:
            plan += [{"text": l, "seq": s["seq"]} for l in vo.get(s["seq"], [])]
        else:
            plan.append(s)
    words = load_takes(takes)
    envs = [envelope(tk) for tk in takes]
    pieces = []
    for s in plan:
        m = best_match(norm(s["text"]), words)
        if not m:
            pieces.append({"text": s["text"], "seq": s.get("seq"), "missing": True})
            continue
        # finish the sentence: up to two more words, in the same breath, to reach the full stop
        i1 = m["i1"]
        for k in range(i1 + 1, min(i1 + 3, len(words))):
            if words[i1]["stop"] or words[k]["take"] != words[i1]["take"] or words[k]["start"] - words[k - 1]["end"] > 0.4:
                break
            if words[k]["stop"]:
                i1 = k
                break
        m["i1"] = i1
        rs = drop_restarts(words, m["i0"], m["i1"])
        for n, (a, b) in enumerate(rs):
            pieces.append({"text": s["text"] if n == 0 else "", "seq": s.get("seq"), "i0": a, "i1": b,
                           "score": m["score"], "restarts_cut": len(rs) - 1})
    adlibs = keep_adlibs(pieces, words)
    merged = []
    for c in pieces:
        p = merged[-1] if merged else None
        if (p and not c.get("missing") and not p.get("missing") and c["i0"] == p["i1"] + 1
                and words[c["i0"]]["take"] == words[p["i1"]]["take"] and p.get("seq") == c.get("seq")):
            p["i1"] = c["i1"]; p["text"] = (p["text"] + " " + c["text"]).strip()
            p["score"] = min(p["score"], c["score"]); p["restarts_cut"] += c["restarts_cut"]
        else:
            merged.append(dict(c))
    for c in merged:
        if c.get("missing"):
            continue
        w0, w1 = words[c["i0"]], words[c["i1"]]
        tk = w0["take"]
        prev_end = words[c["i0"] - 1]["end"] if c["i0"] > 0 and words[c["i0"] - 1]["take"] == tk else w0["start"] - 0.5
        nxt = c["i1"] + 1
        next_start = words[nxt]["start"] if nxt < len(words) and words[nxt]["take"] == tk else w1["end"] + 0.5
        c["src_in"] = quiet(envs[tk], max(prev_end, w0["start"] - 0.35), w0["start"] - 0.02, w0["start"] - 0.08)
        c["src_out"] = quiet(envs[tk], w1["end"] + 0.02, max(w1["end"] + 0.03, min(next_start, w1["end"] + 0.35)), w1["end"] + 0.10)
        c.update({"take": tk, "path": str(Path(takes[tk]).absolute()),
                  "said": " ".join(words[k]["tok"] for k in range(c["i0"], c["i1"] + 1)), "check": c["score"] < 0.8})
    real = [c for c in merged if not c.get("missing")]
    for p, c in zip(real, real[1:]):
        if p["take"] == c["take"] and c["src_in"] < p["src_out"] and p["src_in"] < c["src_out"]:
            mid = round((words[p["i1"]]["end"] + words[c["i0"]]["start"]) / 2, 2)
            p["src_out"] = c["src_in"] = mid
    t = 0.0
    for c in merged:
        if c.get("missing"):
            continue
        c["duration"] = round(c["src_out"] - c["src_in"], 2)
        c["start"] = round(t, 2); t += c["duration"]
    Path(out).write_text(json.dumps({"teleprompter": tp, "takes": takes, "clips": merged, "length": round(t, 2),
                                     "adlibs": adlibs}, indent=1))
    for r in adlibs:
        print(("KEPT     " if r["kept"] else f"LEFT OUT ({r['why']}) ") + f"take {r['take']} @{r['at']:.1f}s: {r['words']}")
    print(f"{len(plan)} sentences -> {len(merged)} clips, {int(t // 60)}:{t % 60:04.1f}; "
          f"{sum(1 for c in merged if c.get('check'))} to check, {sum(1 for c in merged if c.get('missing'))} missing")


if __name__ == "__main__":
    main()
