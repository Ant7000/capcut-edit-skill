"""Make simple graphics in YOUR look: full-screen words, title cards and text overlays.

  python3 make_graphics.py PLAN.json OUTDIR --stills [--project "name"] [--behind FRAME.png]
  python3 make_graphics.py PLAN.json OUTDIR --video  [--project "name"] [--only g03,g07]
  python3 make_graphics.py --placeholder ...        use a plain, clearly-labelled black and white look

Makes the plan's items of kind "word", "title" and "overlay" (kind "file" is your own work and is left alone).
The look comes only from "look" in settings.json, which the style interview fills in from your brand: font
files, colours, sizes, position, logo, how things appear. Nothing about the look is built in. If you haven't set
a look, it stops and says so, unless you ask for --placeholder.

--stills   one PNG per graphic (how it looks once it has appeared) and contact_sheet.png. Always check these
           before making video. Overlays are shown over --behind (a frame from your footage) or grey.
--video    full-screen graphics as H.264 .mp4; overlays as ProRes 4444 .mov with a see-through background
           (premultiplied, which is how CapCut reads it, so soft edges don't show dark or light fringes).
           Each file is the time on screen plus "tail" seconds held still (settings.json), so it can be stretched.
           Writes OUT_PLAN.json next to the files with each item's "file" filled in, for place_graphics.py.
--project  read the frame rate and frame size from the CapCut project (else 30fps, 1920x1080).
"""
import argparse, json, subprocess, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

PLACEHOLDER = {
    "name": "Placeholder (not your look yet)",
    "font": "Helvetica", "font_bold": "Helvetica",
    "text_colour": "#FFFFFF", "background": "#000000",
    "overlay_box": "#000000B3", "accent": None,
    "word_size": 0.085, "title_size": 0.075, "subtitle_size": 0.04, "overlay_size": 0.042,
    "align": "center", "overlay_position": "lower-left", "margin": 0.07, "case": "as-written",
    "logo": None, "logo_position": "top-right", "logo_size": 0.08,
    "animation": "fade", "anim_seconds": 0.25,
    "lengths": {"word": 2.5, "title": 3.0, "overlay": 4.0},
}
FONT_DIRS = [Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"),
             Path.home() / "Library/Fonts"]


def colour(c):
    """#RRGGBB or #RRGGBBAA to an RGBA tuple."""
    c = c.lstrip("#")
    if len(c) == 6:
        c += "FF"
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4, 6))


def font_file(name):
    p = Path(str(name)).expanduser()
    if p.is_file():
        return str(p)
    want = str(name).lower().replace(" ", "").replace("-", "")
    best = None
    for d in FONT_DIRS:
        if d.exists():
            for f in d.rglob("*"):
                if f.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                    continue
                stem = f.stem.lower().replace(" ", "").replace("-", "")
                # an exact name beats one that starts with it, which beats one that only contains it;
                # then the shortest (so "Georgia Bold" doesn't pick "Georgia Bold Italic")
                rank = 0 if stem == want else 1 if stem.startswith(want) else 2 if want in stem else None
                if rank is not None and (best is None or (rank, len(stem)) < best[0]):
                    best = ((rank, len(stem)), str(f))
    if best and best[0][0] < 2:
        return best[1]
    sys.exit(f"Font {name!r} not found. Give the full path to the font file in settings.json (look.font).")


def styled(text, look):
    case = look.get("case", "as-written")
    return text.upper() if case == "upper" else text.lower() if case == "lower" else text


def wrap(draw, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, fontpath, size_px, width, max_lines):
    """The biggest size up to size_px at which the text wraps into max_lines lines."""
    size = size_px
    while True:
        f = ImageFont.truetype(fontpath, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines or size <= 12:
            return f, lines
        size = int(size * 0.92)


def text_layer(W, H, blocks, look, align, anchor_xy, box=None):
    """A transparent RGBA layer with text blocks [(text, font, line_gap)], placed around anchor_xy.
    Text is drawn as a coverage mask filled with solid colour, so edges never carry dark colour."""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    heights, widths, rows = [], [], []
    for lines, f, gap in blocks:
        asc, desc = f.getmetrics()
        lh = int((asc + desc) * gap)
        for ln in lines:
            rows.append((ln, f, lh))
            widths.append(d.textlength(ln, font=f))
            heights.append(lh)
    total_h, max_w = sum(heights), max(widths) if widths else 0
    ax, ay, how = anchor_xy
    y = ay - total_h / 2 if how in ("center", "left-middle") else ay - total_h if how.endswith("bottom") else ay
    x0 = ax - max_w / 2 if align == "center" else ax
    pad = int(H * 0.018)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if box:
        bx0 = (ax - max_w / 2 if align == "center" else ax) - pad * 1.6
        bimg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bimg).rounded_rectangle([bx0, y - pad, bx0 + max_w + pad * 3.2, y + total_h + pad],
                                               radius=pad, fill=colour(box))
        layer = Image.alpha_composite(layer, bimg)
    for (ln, f, lh), w in zip(rows, widths):
        x = ax - w / 2 if align == "center" else x0
        d.text((x, y), ln, font=f, fill=255)
        y += lh
    ink = Image.new("RGBA", (W, H), colour(look["text_colour"]))
    ink.putalpha(Image.eval(mask, lambda v: v * colour(look["text_colour"])[3] // 255))
    return Image.alpha_composite(layer, ink)


def logo_layer(W, H, look):
    if not look.get("logo"):
        return None
    lg = Image.open(Path(look["logo"]).expanduser()).convert("RGBA")
    h = int(H * look.get("logo_size", 0.08))
    lg = lg.resize((max(1, int(lg.width * h / lg.height)), h), Image.LANCZOS)
    m = int(H * look.get("margin", 0.07))
    pos = look.get("logo_position", "top-right")
    x = W - m - lg.width if "right" in pos else m
    y = H - m - lg.height if "bottom" in pos else m
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(lg, (x, y), lg)
    return out


def build(item, look, W, H):
    """(background RGBA or None for overlays, foreground RGBA layer)."""
    kind = item["kind"]
    m = look.get("margin", 0.07)
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    width = W * (1 - 2 * m)
    if kind in ("word", "title"):
        if look.get("background_image"):
            bg = Image.open(Path(look["background_image"]).expanduser()).convert("RGBA").resize((W, H), Image.LANCZOS)
        else:
            bg = Image.new("RGBA", (W, H), colour(look["background"]))
        blocks = []
        if kind == "word":
            f, lines = fit(probe, styled(item["text"], look), font_file(look["font_bold"] or look["font"]),
                           int(H * look["word_size"]), width, 3)
            blocks.append((lines, f, 1.1))
        else:
            f, lines = fit(probe, styled(item["text"], look), font_file(look["font_bold"] or look["font"]),
                           int(H * look["title_size"]), width, 2)
            blocks.append((lines, f, 1.1))
            if item.get("subtitle"):
                f2, l2 = fit(probe, item["subtitle"], font_file(look["font"]), int(H * look["subtitle_size"]), width, 2)
                blocks.append((l2, f2, 1.3))
        align = look.get("align", "center")
        anchor = (W / 2, H / 2, "center") if align == "center" else (W * m, H / 2, "left-middle")
        fg = text_layer(W, H, blocks, look, align, anchor)
        lg = logo_layer(W, H, look)
        if lg:
            fg = Image.alpha_composite(fg, lg)
        return bg, fg
    f, lines = fit(probe, item["text"], font_file(look["font"]), int(H * look["overlay_size"]), width * 0.6, 2)
    pos = look.get("overlay_position", "lower-left")
    x = W * m if "left" in pos else W / 2 if "cent" in pos else W * (1 - m) - width * 0.6
    y = H * (1 - m) if pos.startswith("lower") else H * m
    how = ("left-" if "left" in pos else "") + ("bottom" if pos.startswith("lower") else "top")
    align = "center" if "cent" in pos else "left"
    fg = text_layer(W, H, [(lines, f, 1.15)], look, align, (x, y, how), box=look.get("overlay_box"))
    return None, fg


def frame_at(bg, fg, t, look, H):
    """The frame t seconds after the graphic starts."""
    a = look.get("anim_seconds", 0.25)
    kind = look.get("animation", "cut")
    p = 1.0 if kind == "cut" or a <= 0 else min(1.0, t / a)
    p = 1 - (1 - p) ** 3                                   # ease out
    layer = fg
    if kind == "rise" and p < 1:
        shifted = Image.new("RGBA", fg.size, (0, 0, 0, 0))
        shifted.paste(fg, (0, int(H * 0.03 * (1 - p))))
        layer = shifted
    if p < 1:
        layer = layer.copy()
        layer.putalpha(Image.eval(layer.getchannel("A"), lambda v: int(v * p)))
    if bg is None:
        return layer
    return Image.alpha_composite(bg, layer)


def premultiply(img):
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    black = Image.new("RGB", img.size, (0, 0, 0))
    out = Image.composite(rgb, black, a)               # rgb * alpha
    out.putalpha(a)
    return out


def encode(frames, out, fps, W, H, alpha):
    if alpha:
        args = ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16"]
    else:
        args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "medium", "-movflags", "+faststart"]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", *args, str(out)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit(f"ffmpeg couldn't write {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("outdir")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--project")
    ap.add_argument("--behind")
    ap.add_argument("--only")
    ap.add_argument("--placeholder", action="store_true")
    a = ap.parse_args()
    if not (a.stills or a.video):
        sys.exit(__doc__)
    s = common.settings()
    look = s.get("look")
    if a.placeholder:
        look = PLACEHOLDER
    if not look:
        sys.exit("No graphics look set yet. Run the graphics part of the style interview, or use --placeholder "
                 "for a plain black and white stand-in.")
    look = {**PLACEHOLDER, **look} if a.placeholder else {**{k: v for k, v in PLACEHOLDER.items()
                                                              if k in ("anim_seconds", "lengths", "margin", "case")},
                                                           **look}
    missing = [k for k in ("font", "text_colour", "background", "word_size", "title_size", "subtitle_size",
                           "overlay_size") if k not in look]
    if missing:
        sys.exit(f"The look in settings.json is missing: {', '.join(missing)}. The interview sets these.")
    look.setdefault("font_bold", look["font"])
    fps, W, H = 30.0, 1920, 1080
    if a.project:
        d = common.load_draft(common.find_project(a.project))
        fps = common.fps(d)
        cc = d.get("canvas_config") or {}
        W, H = int(cc.get("width") or W), int(cc.get("height") or H)
    tail = s["graphics"]["tail"]
    plan = json.loads(Path(a.plan).read_text())
    only = set(a.only.split(",")) if a.only else None
    out = Path(a.outdir)
    (out / "stills").mkdir(parents=True, exist_ok=True)
    sheet = []
    for item in plan["graphics"]:
        if item.get("kind") not in ("word", "title", "overlay") or (only and item.get("id") not in only):
            continue
        if not item.get("text"):
            sys.exit(f"{item.get('id')}: no text")
        bg, fg = build(item, look, W, H)
        name = f"{item['id']}_{item['kind']}"
        if a.stills:
            still = frame_at(bg, fg, 60, look, H)
            if bg is None:
                base = (Image.open(a.behind).convert("RGBA").resize((W, H)) if a.behind
                        else Image.new("RGBA", (W, H), (128, 128, 128, 255)))
                still = Image.alpha_composite(base, still)
            if look is PLACEHOLDER or look.get("name", "").startswith("Placeholder"):
                ImageDraw.Draw(still).text((12, 8), "PLACEHOLDER LOOK", fill=(255, 80, 80, 255),
                                           font=ImageFont.truetype(font_file("Helvetica"), 22))
            p = out / "stills" / f"{name}.png"
            still.convert("RGB").save(p)
            sheet.append((item["id"], still.convert("RGB")))
        if a.video:
            on = (item["end"] - item["at"]) if "end" in item and "at" in item else item.get("length") \
                or look.get("lengths", {}).get(item["kind"], 3.0)
            n = int(round((on + tail) * fps))
            alpha = bg is None
            frames = (premultiply(frame_at(bg, fg, i / fps, look, H)) if alpha else
                      frame_at(bg, fg, i / fps, look, H).convert("RGBA") for i in range(n))
            f = out / f"{name}.{'mov' if alpha else 'mp4'}"
            encode(frames, f, fps, W, H, alpha)
            item["file"] = str(f.absolute())
            item.setdefault("full_screen", not alpha)
            print(f"  {f.name}  {on:.2f}s + {tail}s tail")
    if sheet:
        cols, tw = 4, 480
        th = int(tw * H / W)
        rows = (len(sheet) + cols - 1) // cols
        cs = Image.new("RGB", (cols * tw, rows * (th + 28)), (30, 30, 30))
        dr = ImageDraw.Draw(cs)
        lab = ImageFont.truetype(font_file("Helvetica"), 18)
        for i, (gid, im) in enumerate(sheet):
            x, y = (i % cols) * tw, (i // cols) * (th + 28)
            cs.paste(im.resize((tw, th)), (x, y + 28))
            dr.text((x + 6, y + 4), gid, fill=(230, 230, 230), font=lab)
        cs.save(out / "contact_sheet.png")
        print(f"{len(sheet)} stills in {out / 'stills'}; contact sheet: {out / 'contact_sheet.png'}")
    if a.video:
        op = out / "OUT_PLAN.json"
        op.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
        print(f"Plan with files: {op}")


if __name__ == "__main__":
    main()
