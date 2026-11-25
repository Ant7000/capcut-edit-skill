# Graphics: plan, make, place

Graphics either come from the person (made in Canva, Keynote, Claude Design or by a designer) or are made by `make_graphics.py` in **their** look from `settings.json`. There is no built-in look. If `"look"` is empty and they want me to make graphics, run Part B of the interview first. The `--placeholder` look (plain white on black, labelled PLACEHOLDER) is only for trying the pipeline, and only when they ask.

## 1. Plan at the script stage

Graphics placed after the fact look random. Plan them while the script is being written, or straight after the first cut, anchored to exact words. Write `graphics-plan.json`:

```json
{"graphics": [
  {"id": "g01", "kind": "title", "text": "Part one", "subtitle": "The setup", "anchor": "let's start with the setup"},
  {"id": "g02", "kind": "word", "text": "Twelve minutes", "anchor": "twelve minutes", "length": 2.5},
  {"id": "g03", "kind": "overlay", "text": "CapCut 9.5, free version", "anchor": "the free version works", "until": "on a Mac"},
  {"id": "g04", "kind": "file", "file": "/Users/you/Movies/CapCut Edit/my video/chart.mov", "full_screen": true,
   "anchor": "here's what happened", "until": "and that's the point"}
]}
```

- `word`: a few words full screen, for the lines that matter most. Use them sparingly.
- `title`: a title or section card.
- `overlay`: text over the video (a name, a product, a setting).
- `file`: anything they made. Images and video both work; video needs a see-through background if it sits over the footage (see below).
- `anchor` is where it starts (the words as said). `"start_after": true` starts it when those words finish. `until` ends it when those words finish; otherwise `length` (seconds), or the default for its kind.

Rules that make graphics look edited, not stuck on (defaults; their style guide wins):
- **Only words they said**, exactly as said. Numbers must match what they said and be true.
- **One at a time.** Never two graphics on screen at once.
- **No flashes.** Less than about 1.5 seconds of the speaker between two full-screen graphics reads as a flicker: hold the first one longer, or drop one.
- **Land on the word.** A graphic may arrive a touch early (0.2s), never late.
- **Voice under every full-screen graphic.** Nothing full screen while nobody is talking.
- **About the density in their style guide** (often 4 to 8 a minute), and nothing for longer than about 20 seconds on a talking head.
- **End on a cut** where you can; a graphic that pops off just before a cut looks messy.
- **Overlays sit in one place** (their look sets it), not wherever there's room.

## 2. Time it to the cut

After the cut is in CapCut (and after any change to it):
```
$PY $S/timeline_words.py "NAME" words.json words.md
$PY $S/time_graphics.py graphics-plan.json words.json graphics-timed.json
```
Fix any anchor it can't find (check `words.md` for how it was actually said).

## 3. Make them: stills first

```
$PY $S/make_graphics.py graphics-timed.json gfx --stills --project "NAME" --behind FRAME.png
```
(`FRAME.png` is a frame from their footage: `ffmpeg -ss 10 -i TAKE -frames:v 1 FRAME.png`.) Look at `gfx/contact_sheet.png` yourself first: wrong words, text too big or crammed, anything off the frame, low contrast. Then show them. Only when they're happy:
```
$PY $S/make_graphics.py graphics-timed.json gfx --video --project "NAME"
```
This writes `gfx/OUT_PLAN.json` with every made file filled in. Every file has a held tail (`"tail"` in settings.json) so it can be stretched in CapCut.

## 4. Place them

```
$PY $S/place_graphics.py "NAME" gfx/OUT_PLAN.json --dry-run
$PY $S/place_graphics.py "NAME" gfx/OUT_PLAN.json
$PY $S/capcut_punchins.py "NAME"
$PY $S/check_placement.py "NAME"
```
Before calling it ready: no FLASH, CLASH or LONG; every NEAR either fixed or explained; slivers explained. Then they watch it.

## Their own graphics

- **Over the footage:** it needs a see-through background. Ask for **ProRes 4444 with alpha** (a .mov format that carries transparency, and CapCut reads it) or a PNG. Green screen leaves fuzzy edges.
- **Premultiplied.** CapCut treats ProRes 4444 colour as premultiplied. A file exported "straight" can show light or dark fringes and glows as blobs. If edges look wrong, re-export premultiplied (most apps call it "premultiplied" or "matted with black").
- **Full screen:** any format; H.264 .mp4 is fine.
- **Name files so they sort**, by the order they appear (`g01_...`, `g02_...`).
- Match the project's frame size and frame rate.
