# capcut-edit

A free skill for Claude Code that edits your videos in CapCut. Not a rendered video: your real CapCut project, with the cut, the graphics and the levels sitting on the timeline as if you'd done it yourself, so you can keep editing by hand.

No cost, no school, no sign-ups.

> **The one thing to remember: quit CapCut before Claude changes anything.** Press Command Q in CapCut. Closing the window isn't enough, because CapCut keeps running and saves over Claude's changes. Claude checks every time, tells you if CapCut is still open, and can quit and reopen it for you if you say yes.

## What it does

- **Sets itself up.** Ask Claude to set up CapCut editing and it walks you through it: Python, FFmpeg, finding your CapCut projects, your Deepgram key and a one-clip test.
- **Learns your style.** A short interview about how you like your videos cut (how tight, what to do with retakes, ad-libs and jump cuts) and, if you want graphics, your look: your colours, fonts and logo. It saves both as a style guide you can change any time.
- **Cuts your takes.** It matches every line of your script to your takes, keeps the cleanest take of each, cuts in the quiet between words, closes the waits, then listens to its own cut again to catch doubled and clipped words.
- **Builds it in CapCut**, safely: CapCut quit, a backup every time, a dry run first, and it never rebuilds over your hand edits.
- **Covers jump cuts** with punch-ins, and **makes and places graphics** in your look on the exact words you say (or places the ones you made).
- **Finishes:** loudness for YouTube and subtitles timed to your final file.

## What you need

- A Mac. I've only tested it on a Mac so far. Windows is next.
- The CapCut desktop app. The free version works. Tested on 9.5.
- Claude Code (it comes with a paid Claude plan), in the desktop app or the terminal.
- A Deepgram account for word-by-word transcripts. It gives free credit when you sign up.
- Python and FFmpeg. Claude checks for them and helps you install what's missing.

## Install

1. Download this folder (Code, then Download ZIP) and unzip it.
2. Open Claude Code and ask: "Install the capcut-edit skill from my Downloads folder." It goes in `~/.claude/skills/capcut-edit/`.
3. Make a folder for your video inside Movies, open Claude Code in it, and ask: "Set up CapCut editing."

## The prompt

Once it's set up, put your script and your takes in your video's folder, make an empty CapCut project, quit CapCut (Command Q), and ask:

> Cut my footage into the CapCut project "NAME". Follow the script and the style guide in this folder. Use the word timings. Keep the cleanest take of every line. Place every card, screen and overlay on the line it belongs to. CapCut is closed. Back up first, show me a dry run, then build it.

## What's in the folder

- `SKILL.md`: what Claude reads first, including the four safety rules
- `references/`: setup, the style interview, the workflow, CapCut's file map, cutting, graphics, finishing, the fixes for every mistake I've hit, and checklists
- `scripts/`: the tools Claude runs
- `templates/`: your style guide and lessons file

Your own settings, style guide, key and backups live in `~/Movies/CapCut Edit/`, not in this folder, so updating the skill never touches them.

## Your key stays yours

Your Deepgram key goes in a file on your Mac (`~/Movies/CapCut Edit/.env`), never in the chat. The scripts read it themselves, only ever send it to Deepgram, and never show it on screen.

## Stuck?

Tell me what went wrong. That's how I'll know what to fix.

CapCut is a trademark of its owner. This skill isn't made by or connected with CapCut.

MIT licence: see LICENSE.
