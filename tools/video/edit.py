#!/usr/bin/env python3
"""Cut the demo video from the recorded frames (frontend/tests/video/demo.spec.ts) and the narration
(narrate.py): each scene's frames on its own clock with the loading cut out, held until the next
frame, at 30 fps under its narration; the scenes joined with short dissolves; the sound brought to
-16 LUFS. Writes docs/submission/demo-video/kredibel-demo.mp4, its captions (.srt) and a poster.

With --silent it cuts the recording made without captions (VIDEO_FRAMES=frames-silent) to the same
timings, with no sound: kredibel-demo-silent.mp4 to dub over, and its .srt as the dubbing script.

Usage: python3 tools/video/edit.py [--silent]
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


def build_scene(scene: dict, frames_dir: str, sound: bool) -> tuple[Path, float]:
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
    args = parser.parse_args()
    frames_dir = "frames-silent" if args.silent else "frames"
    name = "kredibel-demo-silent" if args.silent else "kredibel-demo"
    sound = not args.silent

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
    run(
        *inputs,
        *("-filter_complex", ";".join(parts)),
        *maps,
        *("-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p"),
        *("-movflags", "+faststart"),
        str(film),
    )

    # Captions for players that show them, from the narration's own timings.
    cues, n = [], 0
    for scene, start in zip(timings, offsets, strict=False):
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
        print(
            f"over {MAX_SECONDS // 60}:00 by {length - MAX_SECONDS:.1f} s: shorten narration.json"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
