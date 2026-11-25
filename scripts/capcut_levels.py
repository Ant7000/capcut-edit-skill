"""Set audio levels in a CapCut project: raise or lower the voice (main track) and set the music bed.

  python3 capcut_levels.py "project" --voice-gain-db 6 [--music NAME --music-volume 0.06] [--dry-run]

--voice-gain-db  scales every main-track clip that has sound by the same amount, so the balance you set
                 between clips is kept.
--music NAME     audio-track clips whose file name contains NAME (case ignored) get --music-volume
                 (CapCut's linear volume: 1.0 = as recorded, 0.1 = -20 dB). Fades and keyframes are left alone.

CapCut's volume tops out at +20 dB (10.0); the script stops rather than go over. Raise the voice only as far
as its peaks allow; master_loudness.sh does the rest on the export.
Refuses while CapCut is open; backs up the project first.
"""
import argparse, json, math, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402
import capcut_project as rc  # noqa: E402


def db(v):
    return "-inf" if v <= 0 else f"{20 * math.log10(v):+.1f} dB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--voice-gain-db", type=float, default=0.0)
    ap.add_argument("--music")
    ap.add_argument("--music-volume", type=float)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    pdir = common.find_project(a.project)
    d = common.load_draft(pdir)
    k = 10 ** (a.voice_gain_db / 20)

    print(f"Voice: main track x{k:.4f} ({a.voice_gain_db:+.1f} dB)")
    changes = 0
    for i, g in enumerate(d["tracks"][0]["segments"]):
        v = g.get("volume", 1.0)
        if v > 0 and abs(k - 1) > 1e-9:
            nv = round(v * k, 6)
            if nv > 10.0:
                sys.exit(f"clip {i}: {nv:.2f} is over CapCut's +20 dB limit; stopping")
            g["volume"] = nv
            changes += 1
    vols = {}
    for g in d["tracks"][0]["segments"]:
        vols[round(g["volume"], 3)] = vols.get(round(g["volume"], 3), 0) + 1
    print(f"  {changes} clips changed; volumes now " + ", ".join(f"{v} ({db(v)}) x{n}" for v, n in sorted(vols.items())))

    if a.music:
        mats = {m["id"]: m for m in d["materials"].get("audios", [])}
        n = 0
        for ti, t in enumerate(d["tracks"]):
            if t["type"] != "audio":
                continue
            for g in t["segments"]:
                m = mats.get(g["material_id"], {})
                if a.music.lower() in os.path.basename(m.get("path", "")).lower():
                    old = g.get("volume", 1.0)
                    g["volume"] = a.music_volume
                    n += 1
                    s = g["target_timerange"]["start"] / 1e6
                    print(f"  music track {ti} at {s:7.2f}s: {old:.4f} ({db(old)}) -> {a.music_volume:.4f} ({db(a.music_volume)})")
        print(f"Music: {n} clips set")
        if not n:
            sys.exit("no music clips matched; stopping")

    if a.dry_run:
        print("dry run: nothing written")
        return
    common.require_closed()
    bk = common.backup(pdir)
    rc.write_project(pdir, d)
    print(f"backup: {bk}")
    print("written")


if __name__ == "__main__":
    main()
