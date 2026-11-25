# A video from start to finish

Below, `S` is `"$SKILL/scripts"`. Run everything from the video's folder.

## The folder: five things

One folder per video, inside `~/Movies` (best: `~/Movies/CapCut Edit/<video name>/`), holding:
1. **The script** as plain text (`script.txt`), if they used one. It's the map: it tells me which line comes next, so I can tell a real take from "hang on, again".
2. **The footage**: every take, straight off the camera, untrimmed.
3. **The word timings**: made by `transcribe.py` into `transcripts/`. This is how I cut on the exact word.
4. **The style guide**: `~/Movies/CapCut Edit/style-guide.md` covers every video. Anything just for this video goes in a `notes.md` here.
5. **The graphics**: either theirs (images, or video with a see-through background) or made by me in their look.

## The prompt

This is the prompt people use. Any wording that asks for the same thing works.

> Cut my footage into the CapCut project "NAME". Follow the script and the style guide in this folder. Use the word timings. Keep the cleanest take of every line. Place every card, screen and overlay on the line it belongs to. CapCut is closed. Back up first, show me a dry run, then build it.

## 1. Check the takes

- The take list is exactly the files they name. Ask about anything else.
- Profile every file's sound before cutting (`editing.md`, "Check the sound first"). Flag anything odd before using it.

## 2. First cut

```
$PY $S/transcribe.py --quiet TAKE...
$PY $S/assemble_takes.py script.txt cut_v1.json TAKE...
$PY $S/tighten_gaps.py cut_v1.json cut_v2.json
$PY $S/selfcheck_cut.py cut_v2.json check_v2.wav script.txt
```
Fix what the self-check finds (doubled or clipped words at joins, missed restarts, long gaps) by editing the edit list's `src_in` / `src_out`, and run it again until it's clean. Then tell them, in a short list: lines missing from every take, lines that scored low, and anything said wrong (numbers especially). Offer pickups for those.

No script? Transcribe the takes, read the words, and build the edit list by hand from the best take of each thought, in the same format (`{"clips": [{"path", "src_in", "src_out"}]}`), then tighten and self-check it the same way.

## 3. Build it in CapCut

1. They make an empty CapCut project with the right frame rate and name, and quit CapCut with Command Q. (Or name an existing empty one.) Check with `capcut_app.py status`; if it's still running, say so and offer to quit it (SKILL.md, rule 1).
2. `$PY $S/capcut_maintrack.py build "NAME" cut_v2.json --dry-run`, tell them what it'll do, get the yes, then run it without `--dry-run`. It adds the files to CapCut's media bin and puts the cut on the main track.
3. They open it in CapCut and look. They'll often change things by hand. Before any later change, run `show` and say what they changed.

## 4. Joins

If their style covers jump cuts with punch-ins: `$PY $S/capcut_punchins.py "NAME" --dry-run`, then run it. Run it again after graphics are placed (a full-screen graphic over a join already hides it) and after any change to the cut.

## 5. Graphics

`graphics.md`: plan against the script, time the plan to the cut, stills, video, place, check.

## 6. Notes and fixes

They watch and give notes in CapCut, so CapCut is open again: before writing any fix, check it's quit (SKILL.md, rule 1). Log them, numbered, with timecodes, and answer only when they say they're done. Fix in a batch with `capcut_maintrack.py apply` (dry run first), re-run punch-ins and the checker, and write any new rule into `lessons.md` or the style guide.

## 7. Finish

`finishing.md`: their music pass, their export, loudness, subtitles.

## Keep a log

For anything longer than a quick fix, keep a `log.md` in the video folder: what changed in CapCut (clip numbers, times, files), the backup's name, check results, and what's waiting on them. A new session can pick up from it.
