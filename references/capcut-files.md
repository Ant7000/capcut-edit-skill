# CapCut's files, and writing to them safely

I edit CapCut desktop projects on a Mac by writing their files. The person opens the project and can change anything by hand. That's the point: a real project they own, not a rendered video that needs another render for every change.

## Where things are

- Projects: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/<folder>/` (or `"capcut_projects"` in settings.json). The name shown in CapCut is `draft_name` in the folder's `draft_meta_info.json`; it can differ from the folder name. Scripts accept either.
- In each project folder:
  - `draft_info.json`: the timeline. Its `id` is the project ID.
  - `template-2.tmp`: an identical copy.
  - `Timelines/<timeline id>/draft_info.json`: the copy CapCut actually reads. Its `id` is the timeline ID (`Timelines/project.json`, `main_timeline_id`).
  - `draft_meta_info.json`: the media bin (`draft_materials`, group type 0), the timeline's byte size (`draft_timeline_materials_size_`, must match `draft_info.json`) and a modified time in microseconds.
- All copies must match, or CapCut ignores the change or opens the wrong version. Always write through `capcut_project.write_project()`, which writes them all.
- Times are microseconds. Keep clip lengths on whole frames of the project's frame rate (`fps` in `draft_info.json`).
- CapCut on a Mac can only open media under `~/Movies` unless it was picked through its own Import dialog; anything else shows "Link media". `capcut_import.py` copies outside files into `~/Movies/CapCut Edit/import/<project>/`.

## The safety steps (every write)

1. CapCut is quit (`capcut_app.py status`). If it's running, tell them before anything else and offer to quit it (`capcut_app.py quit` after their yes) or wait while they press Command Q (`capcut_app.py wait`). Closing the window leaves it running.
2. Dry run (`--dry-run`) and read the report, especially notes about clips that cross the change point.
3. Their yes for big changes.
4. Write. The script backs up the whole project to `~/Movies/CapCut Edit/backups/<project> <date-time>` first and prints the name.
5. Check: `capcut_maintrack.py show` (clip count, the clips around the change, length) and `check_placement.py`.

To undo: they quit CapCut, then `capcut_restore.py "project"` lists the backups and `capcut_restore.py "project" "BACKUP NAME"` puts one back (after backing up the current state).

Backups live outside CapCut's projects folder on purpose: a backup carries the same project name inside it, and a script that went looking by name could write into the backup instead. The scripts also skip any folder with "backup" in its name, and stop if a name matches more than one project.

## Tracks

- `tracks[0]` is the main track: every shot of the person, one after another, never overlapping. If CapCut shows one clip per layer, something broke the project: restore the backup.
- Graphics and B-roll go on named video tracks (`"full_frame_tracks"` and `"overlay_tracks"` in settings.json). `place_graphics.py` replaces those tracks as a whole, so anything placed by hand belongs on other tracks.
- An adjustment layer (track type "adjust", for colour) that spans the whole timeline is kept at full length by `capcut_maintrack.py apply`. Check any shorter adjustment layers after a ripple.

## The scripts

| Script | Does |
|---|---|
| `capcut_maintrack.py show "project"` | lists main-track clips with their numbers, and the other tracks |
| `capcut_maintrack.py build "project" EDITLIST` | the first cut, into an empty main track |
| `capcut_maintrack.py apply "project" EDITS` | insert, delete, trim, with ripple (format in the script's help) |
| `capcut_import.py "project" FILE...` | adds files to the media bin |
| `capcut_project.py track SPEC` | writes one named track from a spec (B-roll, your own graphics, music) |
| `capcut_punchins.py "project"` | punch-ins over uncovered joins |
| `capcut_levels.py "project" --voice-gain-db N` | voice and music levels |
| `place_graphics.py "project" PLAN` | graphics from a timed plan |
| `check_placement.py "project"` | flashes, clashes, bare joins, slivers, long gaps |
| `timeline_words.py "project" OUT.json` | every word on the timeline, at its time in the edit |
| `capcut_restore.py "project" [BACKUP]` | list or restore backups |
| `capcut_app.py status / quit / wait / open` | is CapCut running; quit it (after a yes), wait for it, reopen it |

Every script prints its own help when run without arguments.

## Recipes

**Swap a clip for another file:** import the file, then one edits file with `delete i` then `insert i`. Check what the ripple did to graphics around it.

**Replace a phrase inside a clip:** `trim i` to end at the first cut, `insert i+1` the new phrase, `insert i+2` the rest of the original from the second cut. Match the volume.

**Graphics that cross a change.** A graphic that starts before a change and ends after it moves with whichever side holds most of it; the report says which. If a word moved, re-run `timeline_words.py`, `time_graphics.py` and `place_graphics.py` so every graphic lands on its word again.

**Little slivers** (clips under half a second) are usually leftover trims. Ask before removing them.

**Hand-set speed changes and ramps:** `trim` refuses those clips. Ask them to trim those in CapCut.

## Reading a project quickly

```python
import json, os
d = json.load(open(os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft/FOLDER/draft_info.json")))
m = {x["id"]: x for x in d["materials"]["videos"]}
for i, g in enumerate(d["tracks"][0]["segments"]):
    print(i, g["target_timerange"]["start"] / 1e6, g["target_timerange"]["duration"] / 1e6,
          g["source_timerange"]["start"] / 1e6, os.path.basename(m[g["material_id"]]["path"]), g.get("volume"))
```
