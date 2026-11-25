"""CapCut project files: the building blocks every other script uses, plus a tool to write a named track.

CapCut keeps a project's timeline in more than one place, and they all have to match:
  draft_info.json                     the timeline (its "id" is the project ID)
  template-2.tmp                      an identical copy
  Timelines/<timeline id>/draft_info.json   the copy CapCut actually reads (its "id" is the timeline ID,
                                      from Timelines/project.json, "main_timeline_id")
  draft_meta_info.json                the media bin, plus the timeline's byte size and a modified time
write_project() writes all of them. Times are microseconds.

Write a named track from a spec (graphics, B-roll, music), replacing any track with the same name:
  python3 capcut_project.py track SPEC.json [--dry-run]
SPEC: {"project": NAME, "track_name": "Overlays", "clips": [{"path", "start", "duration", "src_start" (0),
       "volume" (0), "scale" [x, y], "pos" [x, y]}]}
Every other track is left exactly as it is.
"""
import json, subprocess, sys, time, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import common  # noqa: E402

def uid() -> str:
    return str(uuid.uuid4()).upper()


def us(seconds: float) -> int:
    return int(round(seconds * 1_000_000))


def probe_us(path: str) -> int:
    """File duration in microseconds (ffprobe)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return int(float(r.stdout.strip()) * 1_000_000)
    except ValueError:
        sys.exit(f"Can't read the length of {path}. Is it a video or audio file?")


def probe_streams(path):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                                    "-of", "json", str(path)], capture_output=True, text=True).stdout or "{}")
    w = h = 0
    audio = False
    for st in pr.get("streams", []):
        if st.get("codec_type") == "video" and st.get("width"):
            w, h = st["width"], st["height"]
        if st.get("codec_type") == "audio":
            audio = True
    return w, h, audio


PHOTO = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORT = ["speeds", "placeholder_infos", "canvases", "material_animations",
           "sound_channel_mappings", "material_colors", "vocal_separations"]


def speed_material() -> dict:
    return {"curve_speed": None, "id": uid(), "mode": 0, "speed": 1.0, "type": "speed"}


def canvas_material() -> dict:
    return {
        "album_image": "", "blur": 0.0, "color": "", "id": uid(),
        "image": "", "image_id": "", "image_name": "",
        "source_platform": 0, "team_id": "", "type": "canvas_color"
    }


def animation_material() -> dict:
    return {"animations": [], "id": uid(), "multi_language_current": "none", "type": "sticker_animation"}


def sound_channel_material() -> dict:
    return {"audio_channel_mapping": 0, "id": uid(), "is_config_open": False, "type": "none"}


def vocal_separation_material() -> dict:
    return {
        "id": uid(), "type": "vocal_separation",
        "choice": 0, "removed_sounds": [],
        "time_range": None, "production_path": "",
        "final_algorithm": "", "enter_from": ""
    }


def placeholder_info_material() -> dict:
    return {
        "id": uid(), "type": "placeholder_info",
        "meta_type": "none", "res_path": "",
        "res_text": "", "error_path": "", "error_text": ""
    }


def chroma_material(color: str = "#00993eff") -> dict:
    return {
        "id": uid(), "type": "chroma",
        "color": color, "intensity_value": 0.2,
        "shadow_value": 0.0,
        "path": "/Applications/CapCut.app/Contents/Resources/Chroma2",
        "resource_id": "", "should_transfer_color": True,
        "edge_smooth_value": 0.0, "spill_value": 0.0, "version": "v2"
    }


def material_color_material() -> dict:
    return {
        "id": uid(),
        "is_color_clip": False, "is_gradient": False,
        "solid_color": "", "gradient_colors": [],
        "gradient_percents": [], "gradient_angle": 90.0,
        "width": 0.0, "height": 0.0
    }


def video_material(path: str, file_dur_us: int) -> dict:
    return {
        "id": uid(),
        "unique_id": uid().replace("-", "").lower()[:32],
        "type": "video",
        "duration": file_dur_us,
        "path": str(path),
        "media_path": "",
        "local_id": "",
        "has_audio": False,
        "reverse_path": "",
        "intensifies_path": "",
        "reverse_intensifies_path": "",
        "intensifies_audio_path": "",
        "cartoon_path": "",
        "width": 1920,
        "height": 1080,
        "category_id": "",
        "category_name": "local",
        "material_id": "",
        "material_name": Path(path).name,
        "material_url": "",
        "crop": {
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
        },
        "crop_ratio": "free",
        "audio_fade": None,
        "crop_scale": 1.0,
        "extra_type_option": 0,
        "stable": {"stable_level": 0, "matrix_path": "",
                   "time_range": {"start": 0, "duration": 0}},
        "matting": {
            "flag": 0, "path": "", "interactiveTime": [],
            "has_use_quick_brush": False, "strokes": [],
            "has_use_quick_eraser": False, "expansion": 0,
            "feather": 0, "reverse": False, "custom_matting_id": "",
            "enable_matting_stroke": False, "is_clould": False,
            "mask_video_path": "", "cloud_product_fps": 0.0,
        },
        "source": 0,
        "source_platform": 0,
        "formula_id": "",
        "check_flag": 62978047,
        "video_algorithm": {
            "algorithms": [], "time_range": None, "path": "",
            "gameplay_configs": [], "ai_in_painting_config": [],
            "complement_frame_config": None, "motion_blur_config": None,
            "deflicker": None, "noise_reduction": None,
            "quality_enhance": None, "super_resolution": None,
            "ai_background_configs": [], "smart_complement_frame": None,
            "aigc_generate": None, "aigc_generate_list": [],
            "mouth_shape_driver": None, "ai_expression_driven": None,
            "ai_motion_driven": None, "image_interpretation": None,
            "story_video_modify_video_config": {
                "task_id": "", "is_overwrite_last_video": False,
                "tracker_task_id": "", "generate_id": "", "generate_card_id": ""
            },
            "skip_algorithm_index": [],
        },
        "is_unified_beauty_mode": False,
        "is_set_beauty_mode": False,
        "object_locked": None,
        "smart_motion": None,
        "multi_camera_info": None,
        "freeze": None,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "team_id": "",
        "local_material_id": uid().lower(),
        "origin_material_id": "",
        "request_id": "",
        "has_sound_separated": False,
        "is_text_edit_overdub": False,
        "is_ai_generate_content": False,
        "is_video_copilot_aigc_content": False,
        "aigc_type": "none",
        "is_copyright": False,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "local_material_from": "",
        "smart_match_info": None,
        "beauty_face_preset_infos": [],
        "beauty_body_preset_id": "",
        "beauty_face_auto_preset": {"preset_id": "", "name": "", "rate_map": "", "scene": ""},
        "beauty_face_auto_preset_infos": [],
        "beauty_body_auto_preset": None,
        "live_photo_timestamp": -1,
        "live_photo_cover_path": "",
        "content_feature_info": None,
        "corner_pin": None,
        "surface_trackings": [],
        "video_mask_stroke": {
            "resource_id": "", "path": "", "type": "", "color": "",
            "size": 0.0, "alpha": 0.0, "distance": 0.0, "texture": 0.0,
            "horizontal_shift": 0.0, "vertical_shift": 0.0,
        },
        "video_mask_shadow": {
            "resource_id": "", "path": "", "color": "",
            "alpha": 0.0, "blur": 0.0, "distance": 0.0, "angle": 0.0,
        },
        "pre_applied_vip_materials": [],
        "workflow_node_id": "",
    }


def audio_material(path: str, file_dur_us: int) -> dict:
    p = Path(path)
    return {
        "ai_music_type": "", "aigc_history_id": "", "aigc_item_id": "",
        "app_id": 0, "category_id": "", "category_name": "local",
        "check_flag": 1, "duration": file_dur_us,
        "effect_id": "", "extra_info": None,
        "file_id": "", "formula_id": "",
        "id": uid(),
        "intensifies_path": "",
        "local_material_id": uid().lower(),
        "material_id": "", "material_name": p.name,
        "music_id": "", "path": str(path),
        "query": "", "request_id": "", "resource_id": "",
        "search_id": "", "source_platform": 0,
        "team_id": "", "text": "", "title": p.stem,
        "tone_category_id": "", "tone_category_name": "",
        "type": "extract_music", "wave_points": []
    }


def segment(material_id: str,
            t_start: int, t_dur: int,
            s_start: int, s_dur: int,
            render_index: int = 0,
            track_render_index: int = 0,
            scale_x: float = 1.0, scale_y: float = 1.0,
            pos_x: float = 0.0, pos_y: float = 0.0,
            alpha: float = 1.0, volume: float = 1.0,
            extra_material_refs: list = None) -> dict:
    return {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": alpha,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": scale_x, "y": scale_y},
            "transform": {"x": pos_x, "y": pos_y}
        },
        "color_correct_alg_result": "",
        "common_keyframes": [],
        "desc": "",
        "digital_human_template_group_id": "",
        "enable_adjust": True, "enable_adjust_mask": False,
        "enable_color_adjust_pro": False,
        "enable_color_correct_adjust": False, "enable_color_curves": True,
        "enable_color_match_adjust": False, "enable_color_wheels": True,
        "enable_hsl": False, "enable_hsl_curves": True,
        "enable_lut": True,
        "enable_mask_shadow": False, "enable_mask_stroke": False,
        "enable_smart_color_adjust": False,
        "enable_video_mask": True,
        "extra_material_refs": extra_material_refs if extra_material_refs is not None else [],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "hdr_vivid_settings": None,
        "id": uid(),
        "intensifies_audio": False,
        "is_loop": False,
        "is_placeholder": False, "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": volume,
        "lyric_keyframes": None,
        "material_id": material_id,
        "raw_segment_id": "",
        "render_index": render_index,
        "render_timerange": {"start": 0, "duration": 0},
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "segment_color_tag": "",
        "source": "segmentsourcenormal",
        "source_timerange": {"duration": s_dur, "start": s_start},
        "speed": 1.0,
        "state": 0,
        "target_timerange": {"duration": t_dur, "start": t_start},
        "template_id": "", "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": track_render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": volume
    }


def new_video_material(path):
    """A material for a file, with its real length, size and whether it has sound."""
    if Path(path).suffix.lower() in PHOTO:
        mat = video_material(str(path), 10_800_000_000)   # CapCut gives stills three hours
        mat.update(type="photo", has_audio=False)
    else:
        mat = video_material(str(path), probe_us(path))
    w, h, audio = probe_streams(path)
    if w:
        mat["width"], mat["height"] = w, h
    if mat.get("type") != "photo":
        mat["has_audio"] = audio
    return mat


def support_materials(mats):
    """The helper materials CapCut gives every clip; returns their ids for extra_material_refs."""
    extras = [speed_material(), placeholder_info_material(), canvas_material(), animation_material(),
              sound_channel_material(), material_color_material(), vocal_separation_material()]
    for key, obj in zip(SUPPORT, extras):
        mats.setdefault(key, []).append(obj)
    return extras


def write_project(project_dir: Path, draft: dict):
    """Write every timeline copy CapCut expects. Call common.require_closed() and common.backup() first."""
    meta_path = project_dir / "draft_meta_info.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    draft["id"] = meta.get("draft_id", draft.get("id"))
    total_dur = draft.get("duration", 0)
    content = json.dumps(draft, separators=(",", ":"), ensure_ascii=False)

    tl_dir, tl_id = None, None
    proj_json = project_dir / "Timelines" / "project.json"
    if proj_json.exists():
        try:
            tl_id = json.loads(proj_json.read_text()).get("main_timeline_id") or None
            if tl_id:
                tl_dir = project_dir / "Timelines" / tl_id
        except json.JSONDecodeError:
            pass

    (project_dir / "draft_info.json").write_text(content)
    (project_dir / "template-2.tmp").write_text(content)
    if tl_dir and tl_dir.exists():
        tl = dict(draft, id=tl_id)
        tl_content = json.dumps(tl, separators=(",", ":"), ensure_ascii=False)
        (tl_dir / "draft_info.json").write_text(tl_content)
        (tl_dir / "template-2.tmp").write_text(tl_content)

    stale = project_dir / "draft_virtual_store.json"
    if stale.exists():
        stale.unlink()

    layout_id = tl_id if tl_dir else draft["id"]
    (project_dir / "timeline_layout.json").write_text(json.dumps(
        {"dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [layout_id], "timelineNames": ["Timeline 01"]}],
         "layoutOrientation": 1}, separators=(",", ":")))
    (project_dir / "draft_biz_config.json").write_text(json.dumps(
        {"timeline_settings": {layout_id: {"linkage_enabled": False}}}, separators=(",", ":")))

    if meta:
        meta["draft_timeline_materials_size_"] = (project_dir / "draft_info.json").stat().st_size
        meta["tm_duration"] = total_dur
        meta["tm_draft_modified"] = int(time.time() * 1_000_000)
        meta_path.write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False))


def media_bin(project_dir):
    meta = json.loads((project_dir / "draft_meta_info.json").read_text())
    return {v.get("file_Path") for g in meta.get("draft_materials", []) for v in g.get("value", []) if v.get("file_Path")}


def set_track(draft, name, clips, in_bin):
    """Add or replace the track called name in a loaded draft. Returns report lines."""
    mats = draft["materials"]
    clips = sorted(clips, key=lambda c: c["start"])
    for a, b in zip(clips, clips[1:]):
        if a["start"] + a["duration"] > b["start"] + 0.002:
            sys.exit(f"{Path(a['path']).name} and {Path(b['path']).name} overlap on track {name!r}. "
                     "One clip at a time per track.")
    end = draft.get("duration", 0) / 1e6
    segs, report = [], []
    old = next((t for t in draft["tracks"] if t.get("name") == name), None)
    for c in clips:
        p = Path(c["path"])
        if str(p) not in in_bin:
            sys.exit(f"{p.name} isn't in the project's media bin yet. Run capcut_import.py on it first.")
        mat = new_video_material(p)
        src = 0.0 if mat.get("type") == "photo" else c.get("src_start", 0.0)
        if mat.get("type") != "photo" and us(src + c["duration"]) > mat["duration"] + 2000:
            sys.exit(f"{p.name} is only {mat['duration']/1e6:.2f}s long; asked for {src}+{c['duration']}s.")
        if c["start"] + c["duration"] > end + 0.002:
            sys.exit(f"{p.name} would run past the end of the edit ({end:.2f}s).")
        mats.setdefault("videos", []).append(mat)
        refs = [o["id"] for o in support_materials(mats)]
        sx, sy = c.get("scale", [1.0, 1.0])
        px, py = c.get("pos", [0.0, 0.0])
        segs.append(segment(mat["id"], us(c["start"]), us(c["duration"]), us(src), us(c["duration"]),
                            scale_x=sx, scale_y=sy, pos_x=px, pos_y=py, volume=c.get("volume", 0.0),
                            extra_material_refs=refs))
        report.append(f"  {common.tc(c['start'])}  {c['duration']:5.2f}s  {p.name}")
    track = {"attribute": 0, "flag": 2, "id": uid(), "is_default_name": False,
             "name": name, "segments": segs, "type": "video"}
    if old is not None:
        draft["tracks"][draft["tracks"].index(old)] = track   # keep its layer, so it doesn't jump above others
    else:
        draft["tracks"].append(track)
    for ti, t in enumerate(draft["tracks"]):
        for s in t["segments"]:
            s["track_render_index"] = ti
            if t is track:
                s["render_index"] = ti
    return [f"{'Replacing' if old else 'Adding'} track {name!r} with {len(segs)} clips"] + report


def write_track(spec, dry_run=False):
    """Add or replace one named track from a spec (see the module docstring)."""
    project_dir = common.find_project(spec["project"])
    if not dry_run:
        common.require_closed()
    draft = common.load_draft(project_dir)
    report = set_track(draft, spec["track_name"], spec["clips"], media_bin(project_dir))
    if dry_run:
        return report + ["Dry run: nothing written."]
    bk = common.backup(project_dir)
    write_project(project_dir, draft)
    return report + [f"Written. Backup: {bk}"]


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "track":
        print("\n".join(write_track(json.loads(Path(sys.argv[2]).read_text()), "--dry-run" in sys.argv)))
    else:
        sys.exit(__doc__)
