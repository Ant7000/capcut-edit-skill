# Cutting

The defaults below are what work for most talking-to-camera videos. The person's style guide and `settings.json` override them.

## Check the sound first

Profile every file before cutting: channels, loudness, brightness. Files from the same mic and setup should match within about 1 dB.
```
ffprobe -v error -select_streams a:0 -show_entries stream=channels -of csv=p=0 FILE
ffmpeg -nostats -i FILE -vn -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -nostats -i FILE -vn -af "highpass=f=3000,ebur128" -f null - 2>&1 | grep -E "^\s+I:" | tail -1
```
Compare each file with a known-good one. Tell them before cutting if one differs:
- **The camera's own mic** (the main mic was off): usually stereo, several dB louder, much brighter, thin low end. Don't use it. EQ doesn't make it match.
- **The main mic in a different spot**: same channels, but noticeably duller or brighter up top. Ask before using it at all.

Feed loops of ffmpeg commands `</dev/null`, or ffmpeg eats the loop's input.

## The first cut (assemble_takes.py)

It matches every script sentence to every stretch of every take and keeps the best, preferring the later attempt on a near tie. It removes restarts, keeps repeats inside numbers and names ("four four four four"), keeps finished ad-libs said in the same breath, and cuts in the quietest 10ms near each word edge, because transcript timings can be a fifth of a second out. Read its KEPT / LEFT OUT list of ad-libs and check the odd ones.

Options for mixed takes (environment variables): `PREFER_TAKE=N` gives take N (0-based) a head start so fewer takes get mixed; `PREFER_FROM=N` does the same for every take from N on.

## Tighten (tighten_gaps.py)

Closes silences inside clips (teleprompter waits, lost places) down to the person's pause length, and trims the quiet at clip edges so two pauses never stack at a join. Always run it: a first cut with waits left in doesn't feel cut.

## Check by listening again (selfcheck_cut.py)

Renders the cut's sound, transcribes it again and compares. It finds doubled words, clipped words and restarts the first transcript missed, every silence over half a second, and with the script, every run of script words missing from the cut. Fix by hand and run again until clean. A clean transcript isn't proof a join sounds right: listen to anything that looks odd, and never trust a fix just because the transcriber heard the right word.

## Rules of thumb

- **Pace.** The first cut should already feel cut, line by line. No waits, no breaths longer than they need to be.
- **Lead-ins.** Keep the few words before a scripted line when they're the same breath ("And that's it.", "So...").
- **Throat clears and non-word sounds** are cut.
- **Average lines stay in** unless their style guide says otherwise. They can re-record them.
- **Never put back a line they cut by hand.** Compare the project with your plan before changing anything.

## Jump cuts

Takes never line up exactly: head position, energy and light change between them. Cover every join one of these ways (their style guide says which):
- a full-screen graphic over the join
- a punch-in: alternate 100% and their punch-in size on joins with nothing over them, back to 100% after each cutaway (`capcut_punchins.py` plans this from the live timeline and leaves clips they've scaled or moved by hand alone)
- B-roll
- or leave them, if jump cuts are their style.
Overlays (text over the video) don't hide a jump cut.

## Fixing a wrong word or number

1. Search every take from the same mic and setup for the **whole word or phrase** (`transcripts/*.words.json`; transcripts write numbers as digits).
2. Profile it against the clip it's going into: within about 1 dB and the same tone is fine. Match levels with clip volume.
3. Cut in the quiet between words. Swap the whole phrase when the rhythm differs, not just the one word.
4. Make an A/B (the original, a short pause, the fix) and let them listen before it goes in.
5. No clean read anywhere? Ask for a pickup. Never build a word from pieces of other words: it sounds wrong even when the transcript reads right.

In CapCut: `trim` the clip to end at the first cut, `insert` the replacement phrase after it, `insert` the rest of the original after that (`capcut-files.md`, "Recipes").

## Pickups

A pickup list: each line exactly as it should be said, why (wrong number, missing line, weak read), and the setup (same mic, same position, same framing; check the main mic is on). Lines that will sit under a full-screen graphic can be recorded anywhere with the main mic. One clean read is enough.

A pickup recorded later brings its own picture (different light and framing). Every frame of it must sit under a full-screen graphic, or be cut away from. The checker's BARE warning at the pickup's join is the sign.
