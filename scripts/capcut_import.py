"""Add media files to a CapCut project's media bin, without opening CapCut.

  python3 capcut_import.py "project name" FILE [FILE ...] [--dry-run]

CapCut keeps the media bin in draft_meta_info.json (draft_materials, group type 0). This adds one entry per
file and doesn't touch the timeline. Files already in the bin are skipped.

CapCut on a Mac can always read ~/Movies. Anywhere else it only opens files picked through its own Import
dialog, and shows "Link media" for the rest. So a file outside ~/Movies is copied into
~/Movies/CapCut Edit/import/<project>/ first, and the copy is what goes in the bin.

Refuses while CapCut is open. Backs up the project first.
"""
import json, shutil, sys, time, uuid
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

PHOTO = {".png", ".jpg", ".jpeg", ".webp"}
MUSIC = {".mp3", ".wav", ".aac", ".m4a"}
GIF = {".gif"}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    dur = float(j.get("format", {}).get("duration") or 0)
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    return dur, v.get("width", 0), v.get("height", 0)


def entry(path):
    ext = path.suffix.lower()
    dur, w, h = probe(path)
    if ext in PHOTO:
        # CapCut rounds still sizes up to even numbers; an odd size left the file unlinked
        kind, dur_us, rough = "photo", 5_000_000, {"duration": -1, "start": -1}
        w, h = w + w % 2, h + h % 2
    elif ext in MUSIC:
        kind, w, h = "music", 0, 0
        dur_us = int(round(dur * 1e6)); rough = {"duration": dur_us, "start": 0}
    else:
        kind = "gif" if ext in GIF else "video"
        dur_us = int(round(dur * 1e6)); rough = {"duration": dur_us, "start": 0}
    now = time.time()
    born = int(path.stat().st_birthtime)  # CapCut stores the file's creation date here
    return {"ai_group_type": "", "create_time": born, "duration": dur_us, "enter_from": 0,
            "extra_info": path.name, "file_Path": str(path), "height": h,
            "id": str(uuid.uuid4()), "import_time": int(now), "import_time_ms": int(now * 1e6),
            "item_source": 1, "material_color_tag": "", "md5": "", "metetype": kind,
            "roughcut_time_range": rough, "sub_time_range": {"duration": -1, "start": -1},
            "type": 0, "width": w}


def readable_path(p, project, dry):
    """The path CapCut can open: the file itself if it's under ~/Movies, else a copy in the import folder."""
    movies = Path.home() / "Movies"
    if movies in p.parents:
        return p, None
    dest = common.HOME / "import" / project / p.name
    if not dry:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(p, dest)
    return dest, f"COPY     {p.name} -> {dest.parent} (CapCut can only open files under ~/Movies)"


def import_files(project, files, dry=False, quiet=False):
    """Add files to the bin. Returns the paths CapCut will use, in the same order as files."""
    pdir = common.find_project(project)
    if not dry:
        common.require_closed()
    meta_path = pdir / "draft_meta_info.json"
    m = json.loads(meta_path.read_text())
    groups = m.setdefault("draft_materials", [])
    g0 = next((g for g in groups if g.get("type") == 0), None)
    if g0 is None:
        g0 = {"type": 0, "value": []}
        groups.insert(0, g0)
    have = {v.get("file_Path") for v in g0["value"]}
    added, paths, log = [], [], []
    for f in files:
        p = Path(f).expanduser().absolute()
        if not p.exists():
            sys.exit(f"MISSING  {p}")
        p2, note = readable_path(p, pdir.name, dry)
        if note:
            log.append(note)
        paths.append(str(p2))
        if str(p2) in have:
            log.append(f"SKIP     {p2.name} (already in the bin)")
            continue
        e = entry(p2 if p2.exists() else p)
        e["file_Path"] = str(p2)
        added.append(e)
        have.add(str(p2))
        log.append(f"ADD      {p2.name}: {e['metetype']}, {e['duration']/1e6:.2f}s, {e['width']}x{e['height']}")
    if dry or not added:
        log.append("Dry run, nothing written." if dry else "Nothing new to add.")
    else:
        bk = common.backup(pdir)
        g0["value"].extend(added)
        meta_path.write_text(json.dumps(m, ensure_ascii=False))
        log.append(f"Added {len(added)} files to the bin of {pdir.name}. Backup: {bk}")
    if not quiet:
        print("\n".join(log))
    return paths


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) < 2:
        sys.exit(__doc__)
    import_files(args[0], args[1:], dry="--dry-run" in sys.argv)


if __name__ == "__main__":
    main()
