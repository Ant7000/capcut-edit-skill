# The style interview

The interview turns how this person likes their videos into two files in `~/Movies/CapCut Edit/`:
- `style-guide.md`: their style in plain words, which I read before every edit
- `settings.json`: the numbers the scripts use (`"edit"`, `"joins"`, `"graphics"`, `"subtitles"`, `"loudness"`, `"names"`, `"look"`)

Without it I make a reasonable edit. With it, the edit looks like theirs.

## How to run it

- One question at a time, each with a suggested answer they can just accept ("Most people pick B. Happy with that?"). Use a question tool with options if one is available.
- Plain words. If they don't know, use the default and say they can change it any time.
- If they have a video whose edit they love (theirs or someone else's), ask what they like about it. That often answers several questions at once.
- Part A (editing) takes about five minutes. Part B (graphics) is optional and takes about five more.
- At the end, read back a short summary, write both files, and tell them they can say "change my style guide" whenever they like. Re-running the interview updates the files; it never starts from zero.

## Part A: editing

| # | Ask | Writes |
|---|---|---|
| 1 | What do you make, and where does it go? (talking to camera, tutorials, interviews; YouTube, LinkedIn, short vertical clips) | style guide: About my videos |
| 2 | What frame rate does your camera record? (25 or 50 in Australia, the UK and Europe; 30 or 60 in the US. I can read it from one of your files.) | style guide; they match it in each new CapCut project |
| 3 | Do you read from a script or teleprompter? (yes: I match your takes to it; no: I cut from what you said) | style guide |
| 4 | How tight do you like it? Tight (every pause cut), natural (small breaths left in), or relaxed | `edit.max_pause` / `keep_pause`: tight 0.35 / 0.2, natural 0.45 / 0.3, relaxed 0.7 / 0.45 |
| 5 | When you say a line again, is the later one usually the keeper? | `edit.prefer_later_take` |
| 6 | Keep the things you add off-script when they land? And what do you say when you reset ("okay", "again", "from the top")? | `edit.keep_adlibs`, `edit.asides`, `edit.aside_phrases` |
| 7 | Ums and ahs: cut them all, or leave a few so it sounds natural? | style guide (the assembler drops leading ones; I handle the rest by hand) |
| 8 | When a line's delivery is only average, keep it in (you'll re-record it later) or drop it? | style guide |
| 9 | Jump cuts between takes: cover them with a small zoom (punch-in), with graphics or B-roll, or leave them as jump cuts? If zoom: subtle (105%), standard (108%) or strong (115%)? | `joins.cover`, `joins.punch_in_scale` |
| 10 | Names I might mishear: your name, your business, products, tools you mention | `names` (sent to the transcriber as hints) |
| 11 | Loudness: YouTube and most video sites play at -14 LUFS. Use that? (Podcasts often use -16.) | `loudness.target_lufs` |
| 12 | Subtitles: do you want an SRT file? Landscape videos fit 42 characters a line; vertical ones about 32 | `subtitles.max_chars` |
| 13 | Anything you always want, or never want? ("no zooms on my face", "always end on the logo") | style guide: Always and never |

## Part B: graphics

First ask: **do you want me to make graphics, or will you make your own** (Canva, Keynote, Claude Design, a designer) **and have me place them on the right words?** If they make their own, skip to question 9 and set `"look"` to null.

Their look comes only from them. Never suggest a look from anywhere else, and never copy a style they haven't given you. If they have a brand guide, a website or a logo file, offer to read the colours and fonts from it, then confirm each one with them.

| # | Ask | Writes (`look` in settings.json) |
|---|---|---|
| 1 | Your colours: text, background for full-screen graphics, and an accent if you use one (hex codes, or I can pick them from your logo or website) | `text_colour`, `background`, `accent` |
| 2 | Your fonts: one for headlines, one for smaller text. They need to be installed on this Mac, or give me the font files. Use fonts you're licensed to use. | `font_bold`, `font` (a name or a file path) |
| 3 | A logo on title cards? Which file, and which corner? | `logo`, `logo_position`, `logo_size` |
| 4 | Capitals: as written, or ALL CAPS for headlines? | `case` |
| 5 | Centred or left-aligned? | `align` |
| 6 | Text over your video: where (lower left, lower centre, upper left...), and with a box behind it (colour and how see-through)? | `overlay_position`, `overlay_box` (#RRGGBBAA) |
| 7 | How things appear: a straight cut, a quick fade, or a small rise? | `animation`, `anim_seconds` |
| 8 | Size: big and bold, or quieter? | `word_size`, `title_size`, `subtitle_size`, `overlay_size` (share of frame height; defaults 0.085, 0.075, 0.04, 0.042) |
| 9 | How busy: about how many graphics a minute (calm 2 to 4, standard 4 to 8, busy 8 to 12)? | `graphics.per_minute` |
| 10 | Which kinds do you want: full-screen words for key lines, title or section cards, text over your video? | style guide: Graphics |

Then make a sample: write a three-item plan (one of each kind they want, with sample words from their own world), run `make_graphics.py PLAN OUT --stills`, look at the contact sheet yourself, then show them. Adjust until they're happy. Save the look with `"name": "<their brand> look"`.

## Writing the files

- `settings.json`: change only the keys the answers set; keep everything else. Check it's valid JSON afterwards.
- `style-guide.md`: fill in the template's sections in their words, first person ("I like it tight"). Replace the NOT SET UP YET line with the date. Add a line to its change log.
- Tell them where both files are, and that "change my style guide" or "show me my style guide" works any time.
