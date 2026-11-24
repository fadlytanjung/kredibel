#!/usr/bin/env python3
"""Cut the demo video from the recorded frames (frontend/tests/video/demo.spec.ts) and the narration
(narrate.py): each scene's frames on its own clock with the loading cut out, held until the next
frame, at 30 fps under its narration; the scenes joined with short dissolves; the sound brought to
-16 LUFS. Writes docs/submission/demo-video/kredibel-demo.mp4, its captions (.srt) and a poster.

With --silent it cuts the recording made without captions (VIDEO_FRAMES=frames-silent) to the same
timings, with no sound: kredibel-demo-silent.mp4 to dub over, and its .srt as the dubbing script.

With --cut NAME it cuts tools/video/out-NAME/ (narrate.py --cut, the recording with VIDEO_CUT=NAME)
to docs/submission/<the plan's scriptDir>/kredibel-NAME.mp4, kept within the plan's maxSeconds and
maxMegabytes (a high-quality master first, then a two-pass encode to the size). --camera PATH puts
the presenter's own clip in the camera scene (fitted to 1920x1080, with the name tag the recording
drew, out-NAME/name-tag.png); without it the scene shows the placeholder card, for a preview.

Usage: python3 tools/video/edit.py [--silent] [--cut featured [--camera intro.mp4]]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
FILM = ROOT / "docs" / "submission" / "demo-video"
FPS = 30
DISSOLVE = 0.5
MAX_SECONDS = 180  # the team's limit: three minutes at most
MAX_MEGABYTES: float | None = None
CAMERA: Path | None = None
CAMERA_SPAN: tuple[float | None, float | None] = (None, None)  # seconds of the clip to keep
AUDIO_KBPS = 128


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def probe(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def scene_clock(manifest: dict) -> tuple[list[tuple[float, str]], float]:
    """Each frame on the scene's own clock (the cut loading left out), and the scene's length."""
    start, cuts = manifest["start"], manifest["cuts"]

    def v(ts: float) -> float:
        return (ts - start) - sum(max(0.0, min(ts, b) - a) for a, b in cuts if a < ts)

    placed: dict[float, str] = {}
    for frame in sorted(manifest["frames"], key=lambda f: f["ts"]):
        placed[round(max(0.0, v(frame["ts"])), 3)] = frame["f"]  # the last frame of a cut wins
    frames = sorted(placed.items())
    if frames and frames[0][0] > 0:
        frames[0] = (0.0, frames[0][1])
    return frames, v(manifest["end"])


def build_camera(scene: dict, clip: Path) -> tuple[Path, float]:
    """The presenter's own clip: 1920x1080 at 30 fps, its own voice, the name tag laid over it."""
    scenes = OUT / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    target = scenes / f"{scene['id']}.mp4"
    tag = OUT / "name-tag.png"
    fill = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1"
    fit = f"[0:v]fps={FPS},{fill}"
    start, end = CAMERA_SPAN
    span = [*(["-ss", f"{start:.3f}"] if start else []), *(["-to", f"{end:.3f}"] if end else [])]
    length = (end or probe(clip)) - (start or 0.0)
    # The tag shows from the first frame: it also covers a video call's own name label there.
    if tag.exists():
        graph = f"{fit}[cam];[1:v]format=rgba[tag];[cam][tag]overlay=0:0,format=yuv420p[v]"
        inputs = [*span, "-i", str(clip), "-loop", "1", "-i", str(tag)]
    else:
        graph = f"{fit},format=yuv420p[v]"
        inputs = [*span, "-i", str(clip)]
    voice = "[0:a]aresample=48000,aformat=channel_layouts=mono,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    run(
        *inputs,
        *("-filter_complex", f"{graph};{voice}"),
        *("-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}"),
        *("-c:v", "libx264", "-preset", "medium", "-crf", "16", "-c:a", "aac", "-b:a", "192k"),
        str(target),
    )
    return target, probe(target)


def fit_size(master: Path, film: Path, megabytes: float) -> None:
    """Two passes to a bitrate that keeps the film under `megabytes` (5% kept for the container)."""
    seconds = probe(master)
    kbps = int(megabytes * 8000 * 0.95 / seconds) - AUDIO_KBPS
    log = OUT / "x264-2pass"
    common = ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{kbps}k", "-pix_fmt", "yuv420p"]
    run("-i", str(master), *common, "-pass", "1", "-passlogfile", str(log), "-an", "-f", "mp4",
        "/dev/null")  # fmt: skip
    run("-i", str(master), *common, "-pass", "2", "-passlogfile", str(log),
        "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-movflags", "+faststart", str(film))  # fmt: skip


def build_scene(scene: dict, frames_dir: str, sound: bool) -> tuple[Path, float]:
    if scene.get("kind") == "camera" and CAMERA is not None:
        return build_camera(scene, CAMERA)
    folder = OUT / frames_dir / scene["id"]
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    frames, length = scene_clock(manifest)
    length = max(length, scene["duration"])
    # On an exact 30 fps grid: each tick shows the latest frame at or before it, so the picture
    # keeps the narration's time however fast Chrome sent frames; runs of one frame are merged.
    ticks = int(round(length * FPS))
    shown: list[tuple[str, int]] = []
    j = 0
    for k in range(ticks):
        while j + 1 < len(frames) and frames[j + 1][0] <= k / FPS:
            j += 1
        name = frames[j][1]
        if shown and shown[-1][0] == name:
            shown[-1] = (name, shown[-1][1] + 1)
        else:
            shown.append((name, 1))
    lines = []
    for name, count in shown:
        lines += [f"file '{folder / name}'", f"duration {count / FPS:.6f}"]
    lines.append(f"file '{folder / shown[-1][0]}'")
    scenes = OUT / "scenes" / frames_dir
    scenes.mkdir(parents=True, exist_ok=True)
    listing = scenes / f"{scene['id']}.txt"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target = scenes / f"{scene['id']}.mp4"
    video = f"[0:v]fps={FPS},scale=1920:1080:flags=lanczos,format=yuv420p[v]"
    if sound:
        run(
            *("-f", "concat", "-safe", "0", "-i", str(listing)),
            *("-i", str(OUT / "audio" / f"{scene['id']}.wav")),
            *("-filter_complex", f"{video};[1:a]aresample=48000,apad[a]"),
            *("-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}"),
            *("-c:v", "libx264", "-preset", "medium", "-crf", "16"),
            *("-c:a", "aac", "-b:a", "192k"),
            str(target),
        )
    else:
        run(
            *("-f", "concat", "-safe", "0", "-i", str(listing)),
            *("-filter_complex", video),
            *("-map", "[v]", "-t", f"{length:.3f}", "-an"),
            *("-c:v", "libx264", "-preset", "medium", "-crf", "16"),
            str(target),
        )
    return target, probe(target)


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--silent", action="store_true", help="No captions, no sound: to dub over")
    parser.add_argument("--cut", default="", help="A cut in tools/video/<cut>/ (e.g. featured)")
    parser.add_argument("--camera", type=Path, help="The presenter's own clip for the camera scene")
    parser.add_argument("--camera-from", type=float, help="Second of the clip where it starts")
    parser.add_argument("--camera-to", type=float, help="Second of the clip where it ends")
    args = parser.parse_args()
    global OUT, FILM, MAX_SECONDS, MAX_MEGABYTES, CAMERA, CAMERA_SPAN
    frames_dir = "frames-silent" if args.silent else "frames"
    name = "kredibel-demo-silent" if args.silent else "kredibel-demo"
    sound = not args.silent
    if args.cut:
        plan = json.loads((HERE / args.cut / "narration.json").read_text(encoding="utf-8"))
        OUT = HERE / f"out-{args.cut}"
        FILM = ROOT / "docs" / "submission" / plan.get("scriptDir", args.cut)
        MAX_SECONDS = int(plan.get("maxSeconds", MAX_SECONDS))
        MAX_MEGABYTES = plan.get("maxMegabytes")
        name = f"kredibel-{args.cut}" + ("-silent" if args.silent else "")
        if args.camera:
            CAMERA = args.camera.resolve()
            if not CAMERA.exists():
                raise SystemExit(f"no camera clip at {CAMERA}")
            CAMERA_SPAN = (args.camera_from, args.camera_to)

    timings = json.loads((OUT / "timings.json").read_text(encoding="utf-8"))["scenes"]
    # A scene recorded only on request (the Google onboarding needs VIDEO_OWNER_EMAIL) is left out.
    recorded = [s for s in timings if (OUT / frames_dir / s["id"] / "manifest.json").exists()]
    for scene in timings:
        if scene not in recorded:
            print(f"{scene['id']:<13} not recorded, left out")
    timings = recorded
    built = [build_scene(scene, frames_dir, sound) for scene in timings]
    for scene, (_, length) in zip(timings, built, strict=False):
        print(f"{scene['id']:<13} {length:6.2f} s (narration {scene['duration']:.2f})")

    # Join with dissolves: each next scene starts DISSOLVE seconds before the previous one ends.
    inputs: list[str] = []
    for path, _ in built:
        inputs += ["-i", str(path)]
    parts, offsets, offset = [], [0.0], 0.0
    last_v, last_a = "[0:v]", "[0:a]"
    for i in range(1, len(built)):
        offset += built[i - 1][1] - DISSOLVE
        offsets.append(offset)
        parts.append(
            f"{last_v}[{i}:v]xfade=transition=fade:duration={DISSOLVE}:offset={offset:.3f}[v{i}]"
        )
        if sound:
            parts.append(f"{last_a}[{i}:a]acrossfade=d={DISSOLVE}[a{i}]")
        last_v, last_a = f"[v{i}]", f"[a{i}]"
    total = offsets[-1] + built[-1][1]
    parts.append(f"{last_v}fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.3f}:d=0.8[vout]")
    maps = ["-map", "[vout]"]
    if sound:
        parts.append(
            f"{last_a}loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={total - 0.8:.3f}:d=0.8[aout]"
        )
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        maps.append("-an")
    FILM.mkdir(parents=True, exist_ok=True)
    film = FILM / f"{name}.mp4"
    master = OUT / f"{name}-master.mp4" if MAX_MEGABYTES else film
    run(
        *inputs,
        *("-filter_complex", ";".join(parts)),
        *maps,
        *("-c:v", "libx264", "-preset", "slow", "-crf", "18" if MAX_MEGABYTES else "20"),
        *("-pix_fmt", "yuv420p", "-movflags", "+faststart"),
        str(master),
    )
    if MAX_MEGABYTES:
        fit_size(master, film, float(MAX_MEGABYTES))

    # Captions for players that show them, from the narration's own timings.
    cues, n = [], 0
    for scene, start, (_, length) in zip(timings, offsets, built, strict=False):
        if scene.get("kind") == "camera":
            scene = {**scene, "sentences": [{**scene["sentences"][0], "end": length - 0.5}]}
        for sentence in scene["sentences"]:
            n += 1
            begin, end = srt_time(start + sentence["start"]), srt_time(start + sentence["end"])
            cues.append(f"{n}\n{begin} --> {end}\n{sentence['text']}\n")
    (FILM / f"{name}.srt").write_text("\n".join(cues), encoding="utf-8")
    if sound:
        run(
            "-ss",
            f"{offsets[2] + 3:.2f}",
            "-i",
            str(film),
            "-frames:v",
            "1",
            str(FILM / "poster.png"),
        )
    length = probe(film)
    size = film.stat().st_size / 1e6
    print(f"wrote {film.relative_to(ROOT)}: {int(length // 60)}:{length % 60:04.1f}, {size:.1f} MB")
    if length > MAX_SECONDS:
        print(f"over {MAX_SECONDS} s by {length - MAX_SECONDS:.1f} s: shorten the narration")
        return 1
    if MAX_MEGABYTES and size > float(MAX_MEGABYTES):
        print(f"over {MAX_MEGABYTES} MB: lower maxMegabytes a little and cut again")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
