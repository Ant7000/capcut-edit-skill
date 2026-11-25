"""Word-by-word transcripts with Deepgram, so Claude can cut on exact words.

  python3 transcribe.py FILE [FILE ...]          transcribe, print each word with its start and end
  python3 transcribe.py --quiet FILE [FILE ...]  transcribe only

Each file's words are saved in ./transcripts/<file name>.words.json (word, start, end, confidence, in seconds
from the start of the file) and reused while the file hasn't changed, so nothing is paid for twice.

The key is DEEPGRAM_API_KEY in a .env file (this folder, a folder above it, or ~/Movies/CapCut Edit/.env).
It's sent only to Deepgram and never printed. Only a small mono copy of the audio is uploaded.
Names Deepgram might mishear (your name, brand, product names) go in settings.json under "names".
"""
import hashlib, json, os, re, subprocess, sys, tempfile, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

MODEL = "nova-3"
URL = "https://api.deepgram.com/v1/listen"


def fingerprint(path):
    st = os.stat(path)
    return hashlib.md5(f"{Path(path).name}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()


def silences(path):
    """(start, end) of every stretch of silence."""
    err = subprocess.run(["ffmpeg", "-i", str(path), "-vn", "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends + [float("inf")] * (len(starts) - len(ends))))


def tighten(words, quiet):
    """Deepgram's word edges can sit up to 0.3s inside a silence. Move them out to where the sound is."""
    for w in words:
        for s, e in quiet:
            if s <= w["start"] < e < w["end"]:
                w["start"] = round(e, 3)
            if w["start"] < s < w["end"] <= e:
                w["end"] = round(s, 3)
    return words


def deepgram(wav_bytes, key, names):
    q = [("model", MODEL), ("smart_format", "true"), ("filler_words", "true")] + [("keyterm", n) for n in names]
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(q)}", data=wav_bytes, method="POST",
                                 headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit("Deepgram didn't accept the key. Check the DEEPGRAM_API_KEY line in your .env file.")
        if e.code == 402:
            sys.exit("Deepgram says the account is out of credit.")
        sys.exit(f"Deepgram returned an error ({e.code}). Try again in a minute.")
    except urllib.error.URLError as e:
        sys.exit(f"Couldn't reach Deepgram ({e.reason}). Check the internet connection.")


_MEMO = {}


def transcribe(path):
    """Words for one file, from the saved copy when the file hasn't changed. Each copy is a fresh list."""
    key = str(Path(path).absolute())
    if key not in _MEMO:
        _MEMO[key] = _transcribe(Path(path))
    return [dict(w) for w in _MEMO[key]]


def _transcribe(path):
    cache = common.transcripts_dir() / f"{path.stem}.words.json"
    fp = fingerprint(path)
    if cache.exists():
        data = json.loads(cache.read_text())
        if data.get("fingerprint") == fp:
            return tighten(data["words"], silences(path))
    key = common.env_key()
    if not key:
        sys.exit("No Deepgram key found. Put a line DEEPGRAM_API_KEY=... in ~/Movies/CapCut Edit/.env "
                 "(the setup check does this with you).")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"   # mono 16 kHz: a small upload, and all the model needs
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       check=True, stdin=subprocess.DEVNULL)
        r = deepgram(wav.read_bytes(), key, common.settings().get("names", []))
    alt = r["results"]["channels"][0]["alternatives"][0]
    words = [{"word": w.get("punctuated_word") or w["word"], "start": round(w["start"], 3),
              "end": round(w["end"], 3), "confidence": round(w.get("confidence", 0), 3)} for w in alt.get("words", [])]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"file": str(path), "fingerprint": fp, "model": MODEL,
                                 "request_id": r.get("metadata", {}).get("request_id"), "words": words}, indent=1))
    return tighten(words, silences(path))


def load_words(path):
    """Saved words for a file (transcribing it if needed)."""
    return transcribe(path)


if __name__ == "__main__":
    args = sys.argv[1:]
    quiet = "--quiet" in args
    args = [a for a in args if a != "--quiet"]
    if not args:
        sys.exit(__doc__)
    for f in args:
        words = transcribe(f)
        print(f"{Path(f).name}: {len(words)} words")
        if not quiet:
            for w in words:
                print(f"  {w['start']:7.3f} {w['end']:7.3f}  {w['confidence']:.2f}  {w['word']}")
