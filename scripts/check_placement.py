"""Check where the graphics sit in a CapCut project. Reads the live project and changes nothing.

  python3 check_placement.py "project"

Full-screen tracks hide the speaker; every other named video track is an overlay. Which tracks are which, and
the limits below, come from settings.json ("graphics"). Reports, with timecodes:
  FLASH   the speaker on screen for less than min_gap seconds between two full-screen graphics
  CLASH   two graphics on screen at once
  BARE    a join between clips with no full-screen graphic over it and no punch-in change (a visible jump cut)
  SLIVER  a main-track clip under 0.5s (often a leftover trim)
  NEAR    a graphic starting or ending within 1s of a cut without landing on it
  LONG    more than max_bare seconds with no graphic at all
and a summary: graphics a minute and the share of time under full-screen graphics.
Which word a graphic belongs to isn't visible in the project; the graphics plan carries that.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

G = common.settings()["graphics"]
FLASH, SLIVER, NEAR, LONG, EPS = G["min_gap"], 0.5, 1.0, G["max_bare"], 0.041


def tc(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--ignore", default="", help="track names to leave out, comma separated (transitions)")
    a = ap.parse_args()
    d = common.load_draft(common.find_project(a.project))
    if not d["tracks"] or not d["tracks"][0]["segments"]:
        sys.exit("The project's main track is empty.")
    full_names = set(G["full_frame_tracks"]); ignore = set(x for x in a.ignore.split(",") if x)
    mats = {m["id"]: m for m in d["materials"].get("videos", [])}
    end = d["duration"] / 1e6
    main_t = d["tracks"][0]["segments"]
    clips = [(g["target_timerange"]["start"] / 1e6, (g["target_timerange"]["start"] + g["target_timerange"]["duration"]) / 1e6,
              g["clip"]["scale"]["x"]) for g in main_t]
    gfx = []
    for t in d["tracks"][1:]:
        if t.get("type") != "video":
            continue                      # adjustment layers etc. aren't graphics
        name = t.get("name", "")
        if name in ignore:
            continue
        for g in t["segments"]:
            s = g["target_timerange"]["start"] / 1e6
            gfx.append({"a": s, "b": s + g["target_timerange"]["duration"] / 1e6, "track": name, "full": name in full_names,
                        "name": Path(mats.get(g["material_id"], {}).get("path", "?")).stem})
    gfx.sort(key=lambda g: g["a"])
    issues = []
    full = [g for g in gfx if g["full"]]
    # FLASH and LONG: gaps between full-frame graphics (merged)
    merged = []
    for g in full:
        if merged and g["a"] <= merged[-1][1] + 1e-3:
            merged[-1][1] = max(merged[-1][1], g["b"]); merged[-1][2] = g["name"]
        else:
            merged.append([g["a"], g["b"], g["name"]])
    for (a0, b0, n0), (a1, b1, n1) in zip(merged, merged[1:]):
        gap = a1 - b0
        if EPS < gap < FLASH:          # butted graphics (gap 0) are fine
            issues.append((b0, "FLASH", f"{gap:.2f}s of the speaker between {n0} and the next graphic"))
    # LONG counts every graphic, overlays too
    allm = []
    for g in sorted(gfx, key=lambda g: g["a"]):
        if allm and g["a"] <= allm[-1][1] + 1e-3:
            allm[-1][1] = max(allm[-1][1], g["b"])
        else:
            allm.append([g["a"], g["b"]])
    edges = [0.0] + [x for m in allm for x in (m[0], m[1])] + [end]
    bare = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 1, 2)]
    for s, e in bare:
        if e - s > LONG:
            issues.append((s, "LONG", f"{e - s:.0f}s of the speaker with no graphic (to {tc(e)})"))
    # CLASH: any two graphics overlapping
    for i, g in enumerate(gfx):
        for h in gfx[i + 1:]:
            if h["a"] >= g["b"] - EPS:
                break
            if h["track"] != g["track"]:
                issues.append((h["a"], "CLASH", f"{g['name']} ({g['track']}) and {h['name']} ({h['track']}) overlap {g['b'] - h['a']:.2f}s"))
    # BARE joins and SLIVERs
    for (s0, e0, k0), (s1, e1, k1) in zip(clips, clips[1:]):
        covered = any(g["a"] - EPS <= s1 <= g["b"] + EPS for g in full)
        if not covered and abs(k0 - k1) < 1e-6:
            issues.append((s1, "BARE", "join with no full-frame graphic and no punch-in change"))
    for s, e, k in clips:
        if e - s < SLIVER:
            issues.append((s, "SLIVER", f"main-track clip only {e - s:.2f}s"))
    # NEAR: graphic edges just off a main-track cut
    cuts = [c[0] for c in clips[1:]]
    for g in gfx:
        for edge, which in ((g["a"], "starts"), (g["b"], "ends")):
            near = min(cuts, key=lambda c: abs(c - edge)) if cuts else None
            if near is not None and EPS < abs(near - edge) < NEAR:
                issues.append((edge, "NEAR", f"{g['name']} {which} {abs(near - edge):.2f}s {'before' if edge < near else 'after'} a cut"))
    issues.sort()
    for t, kind, msg in issues:
        print(f"{tc(t):>8}  {kind:<6} {msg}")
    covered_s = sum(m[1] - m[0] for m in merged)
    counts = {}
    for _, k, _ in issues:
        counts[k] = counts.get(k, 0) + 1
    lo, hi = G["per_minute"]
    print(f"\n{len(gfx)} graphics, {len(gfx) / (end / 60):.1f} a minute (your range {lo} to {hi}); "
          f"full-screen covers {covered_s / end * 100:.0f}% of {tc(end)}")
    print("issues: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))


if __name__ == "__main__":
    main()
