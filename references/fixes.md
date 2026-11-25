# Fixes: things that went wrong, and what fixed them

Every one of these happened in real edits. The scripts already guard against most of them; the rest are habits.

## Writing to CapCut

- **Changes vanished when CapCut opened.** CapCut was still running (the window was closed, not the app), and it saved over the files. Fix: quit with Command Q; the scripts check first.
- **The write went into a backup.** A backup carries the same project name inside it, and the script found the backup first. Fix: backups now live outside CapCut's folder, names with "backup" are skipped, and a name matching more than one project stops the script.
- **Hand edits wiped.** A rebuild from the original edit list threw away speed ramps added by hand. Fix: after the first build, only change the project as it is now (`apply`), never rebuild.
- **"Link media" in CapCut.** The file was outside ~/Movies, which CapCut can't open by itself. Fix: keep video folders in ~/Movies; `capcut_import.py` copies anything else in.
- **One clip per layer.** All shots belong on the main track, one after another. If each clip sits on its own layer, the project was broken: restore the backup.
- **A clip ran past the end of its file** after a trim. The scripts now check every insert and trim against the file's real length.
- **A ripple dragged a graphic** that started just before a change. The report now says which way each crossing graphic went; re-time graphics after any change to the cut.
- **The colour layer stopped short** after clips were inserted. Full-length adjustment layers are now kept at full length.
- **The edit opened with hairline gaps.** Clip lengths weren't on whole frames. The scripts now snap to the project's frame rate.

## Sound and takes

- **The main mic was off** for some files, and the camera mic was used without anyone noticing until the cut. Fix: profile every file's sound before cutting.
- **A take recorded with the mic moved** was noticeably duller. EQ didn't make it match. Fix: flag it and ask before using it at all.
- **Missing lines filled from another day's takes.** Different light and framing. Fix: only the takes named; ask first.
- **Clipped words.** Transcript timings can be a fifth of a second out; cutting exactly on them loses the end of a word. Fix: cut in the quietest moment near the word edge, read from the waveform.
- **Doubled words.** Two takes overlapped at a join ("the AI" said twice). Fix: when there's no clean gap, drop a small word instead. Nobody notices a missing "the"; everybody notices one said twice.
- **Restarts the transcript missed.** Fix: render the cut and transcribe it again (`selfcheck_cut.py`).
- **"4444" became "44".** The restart filter collapsed a repeated number. Fix: repeats inside numbers and names are kept.
- **Ad-libs disappeared.** Fix: finished ad-libs in the same breath are kept, and every one kept or dropped is listed.
- **Long teleprompter waits inside clips.** Fix: always run `tighten_gaps.py`, which uses one speech level for the whole cut.
- **A word built from pieces of other words** sounded wrong, though the transcript read it right. Fix: whole words or phrases only, A/B first, else a pickup.
- **Weak lines dropped.** Fix: keep them unless the style guide says otherwise; offer pickups.
- **A pickup's picture didn't match.** Recorded later, different light. Fix: cover every frame of it with a full-screen graphic.

## Graphics

- **Graphics placed after the fact looked random.** Fix: plan at the script stage, anchored to words.
- **Graphics popped off just before cuts, and flashed between each other.** Fix: held tails on every file, ends moved onto cuts, flashes closed.
- **Words on screen that were never said**, and a wrong number. Fix: only their exact words; numbers checked.
- **Too many full-screen word graphics** felt like shouting. Fix: keep them for the lines that matter.
- **Fuzzy edges from green screen.** Fix: ProRes 4444 with alpha.
- **Light or dark fringes around soft edges** in CapCut. CapCut reads ProRes 4444 colour as premultiplied. Fix: write it premultiplied (`make_graphics.py` does).
- **A graphic matched the wrong place** because the phrase was said twice. Fix: anchors are searched in order, each after the last.
- **Rendered video before anyone saw a still.** Fix: stills first, always.

## Picture

- **iPhone footage looked washed out** when frames were pulled out with ffmpeg. It was HDR (HLG). CapCut handles it on its own timeline; anything made outside CapCut from that footage needs tone mapping to standard range first. Check: `ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of default=nw=1 FILE` (`arib-std-b67` means HLG).

## Tools

- **ffmpeg in a loop ate the loop's input** and skipped files. Fix: feed it `</dev/null`.
- **zsh stops a command on an unmatched wildcard.** Quote paths, or check the files exist first.
- **Screen recordings' file names** have an invisible narrow space before "am/pm". Use a wildcard rather than typing the name.
