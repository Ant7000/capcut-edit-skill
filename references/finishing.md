# Finishing: levels, loudness, subtitles

## Levels in CapCut

- Raise the voice only as far as its peaks allow: `capcut_levels.py "NAME" --voice-gain-db N --dry-run`. It scales every voice clip by the same amount, so the balance between clips is kept. CapCut alone usually can't reach -14 LUFS without clipping; the mastering step does the rest.
- Music is their choice and their pass. When they've placed it, set the bed under speech: measure both (`ffmpeg -nostats -i FILE -vn -af ebur128 -f null -`) and work out how far under the voice the music sits at a given volume (music loudness + 20 x log10(volume), against the voice's loudness). Beds set by ear while editing are often louder than they sound later. Make short A/B excerpts at two or three levels and let them choose before writing: `capcut_levels.py "NAME" --music NAME --music-volume V`.

## Export

They export from CapCut. Ask for the highest quality they're happy to upload.

## Loudness

```
$S/master_loudness.sh EXPORT.mp4 EXPORT_master.mp4 [TARGET] [TRUE_PEAK]
```
Defaults: -14 LUFS integrated, true peak -1 dB (what YouTube plays at). The picture is copied untouched; only the sound changes. It measures the result: check the loudness lands within about 0.5 of the target and the peak is at or under the true-peak limit. If the peak is over, run it again from the original with a lower limit (for example -1.5). A plain loudness filter often can't reach the target with close-mic speech because the voice's peaks sit far above its average; this script compresses gently and limits first, so it can.

## Subtitles

Make them from the exact file that will be uploaded, never from the takes, so the timing matches:
```
$PY $S/transcribe.py --quiet EXPORT_master.mp4
$PY $S/make_srt.py transcripts/EXPORT_master.words.json EXPORT_master.srt [fixes.json]
```
Read the SRT for mishears: names, brands, numbers, technical words. Put the fixes in `fixes.json` (the script's help shows the format) and run it again. Add names that keep getting misheard to `"names"` in settings.json for next time. Upload the SRT with that exact version of the video.

## Before upload

`checklists.md`, "Before upload".
