# Setup: talking someone through it

Most people setting this up aren't technical. Go one step at a time, say what each thing is for in a sentence, do the work yourself where you can, and tell them exactly what to click or paste where you can't. Never ask for a password or for the Deepgram key in the chat.

Run `python3 "$SKILL/scripts/setup_check.py"` first and only do the steps that come back NO. Run it again at the end.

## What they need (tell them up front)

- A Mac. Windows isn't supported yet.
- The CapCut desktop app (the free version works). Tested on version 9.5.
- Claude Code, which comes with a paid Claude plan.
- A Deepgram account for word-by-word transcripts. It gives free credit on sign-up.
- Python and FFmpeg, two free tools the scripts use. Usually I can sort these out.

## 1. The skill itself

If they've just downloaded the folder: copy it to `~/.claude/skills/capcut-edit/` (make the folders if needed), keeping `SKILL.md` at the top. Tell them it's installed and loads in new Claude Code sessions. If they cloned it with git, the same place works.

## 2. Python

- `python3 --version`. On a fresh Mac this may open a box asking to install the "command line developer tools". Tell them to click Install and wait for it to finish (a few minutes), then carry on.
- Make the Python the scripts use, in their CapCut Edit folder (step 4 makes the folder; do that first if needed):
  ```
  python3 -m venv "$HOME/Movies/CapCut Edit/.venv"
  "$HOME/Movies/CapCut Edit/.venv/bin/pip" install -r "$SKILL/requirements.txt"
  ```
  From now on run scripts with that Python (`PY` in SKILL.md).

## 3. FFmpeg

`ffmpeg -version`. If it's missing:
- If Homebrew is installed (`brew --version`), ask before installing, then run `brew install ffmpeg`.
- If not, Homebrew's install needs their Mac password, which I can't type. Give them the one line from https://brew.sh to paste into Terminal, explain it will ask for their Mac password (the one they log in with) and that nothing shows while they type it, and wait. Then `brew install ffmpeg`.

## 4. Their CapCut Edit folder

`$PY "$SKILL/scripts/setup_check.py" --init` makes `~/Movies/CapCut Edit/` with:
- `settings.json`: the numbers the scripts use (the interview sets them)
- `style-guide.md` and `lessons.md`: from the templates
- `.env`: an empty line for the Deepgram key
- `backups/` and `import/`

It lives in Movies because CapCut can always open files in Movies. Suggest they keep each video's folder in there too (`~/Movies/CapCut Edit/<video name>/`).

## 5. CapCut's projects folder

The check looks in `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/`. If it isn't there: ask them to open CapCut and make any project, then check again. If CapCut keeps projects elsewhere (CapCut's settings show the location), put that path in `settings.json` as `"capcut_projects"`.

## 6. The Deepgram key

1. They sign up at https://deepgram.com and create an API key in the console (Deepgram's own steps change, so let them follow the site; help if they get stuck).
2. Open the `.env` file for them: `open -e "$HOME/Movies/CapCut Edit/.env"`. They paste the key after `DEEPGRAM_API_KEY=` with no spaces, save and close.
3. `$PY "$SKILL/scripts/setup_check.py" --test-key` sends one second of silence to prove it works. It never shows the key.

Explain why it's in a file and not the chat: a key is like a password for their Deepgram account, and anything pasted into a chat is kept in the conversation.

## 7. Quitting CapCut (teach this now)

Tell them the one habit that matters most, in these words or close: "Before I change a CapCut project, CapCut has to be fully quit, with Command Q. If it's open, it saves over my changes and they disappear. Closing the window isn't enough. I'll always check first and tell you if it's still open."

Then ask: "Do you want me to quit and reopen CapCut for you when I need to, or would you rather do it yourself?" If they want me to, set `"quit_capcut_for_me": true` in settings.json and try it once now (`capcut_app.py quit`, then `capcut_app.py open`). The first time, macOS may ask whether Claude can control CapCut: they click OK. Either way I still say when I'm quitting it, so it's never a surprise.

## 8. The style interview

Run `references/interview.md`. It takes about ten minutes, and the edits look like theirs from the first cut.

## 9. The one-clip test

1. They open CapCut, make a new empty project, name it (something like `Test`), set the frame rate to match their camera, and quit CapCut with Command Q (or I quit it for them). This is the first real practice of the habit.
2. Ask for one short clip (any recording from their camera). `$PY "$SKILL/scripts/setup_check.py" --one-clip "Test" CLIP --dry-run`, then without `--dry-run`.
3. They open the project in CapCut. If the clip is sitting on the timeline and plays, they're set up. If CapCut shows "Link media", the file is outside Movies: see `fixes.md`.

Tell them how long setup took and what to do next: `references/workflow.md` explains a video from start to finish, and the prompt.
