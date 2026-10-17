#!/usr/bin/env python3
"""Voice the demo video's narration (tools/video/narration.json) with Google Cloud Text-to-Speech,
one clip per sentence (cached by its text and voice), joined per scene with short pauses; write the
timings the recording follows and the script for review (docs/submission/demo-video/script.md).

Usage: cd backend && uv run python ../tools/video/narrate.py
Credentials come from Application Default Credentials (gcloud auth application-default login);
the Cloud Text-to-Speech API must be enabled on the project named in narration.json (or
GOOGLE_CLOUD_PROJECT).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
AUDIO = OUT / "audio"
SCRIPT = ROOT / "docs" / "submission" / "demo-video" / "script.md"
RATE = 44100
TTS = "https://texttospeech.googleapis.com/v1/text:synthesize"


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def session(project: str) -> AuthorizedSession:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    # Billed to the project that has the API, whatever the credentials' own quota project.
    s = AuthorizedSession(credentials.with_quota_project(project))
    s.headers["x-goog-user-project"] = project
    return s


def speak(text: str, voice: dict, api: AuthorizedSession) -> Path:
    digest = hashlib.sha256(json.dumps([text, voice], sort_keys=True).encode()).hexdigest()[:16]
    target = AUDIO / f"s_{digest}.mp3"
    if target.exists():
        return target
    body = {
        "input": {"text": text},
        "voice": {"languageCode": voice["languageCode"], "name": voice["voice"]},
        "audioConfig": {
            "audioEncoding": "MP3",
            "sampleRateHertz": RATE,
            "speakingRate": voice.get("speakingRate", 1.0),
        },
    }
    res = api.post(TTS, json=body, timeout=120)
    if res.status_code != 200:
        raise SystemExit(f"Text-to-Speech {res.status_code}: {res.text[:300]}")
    target.write_bytes(base64.b64decode(res.json()["audioContent"]))
    return target


def scene_audio(clips: list[Path], gap: float, tail: float, target: Path) -> None:
    """The scene's clips with `gap` seconds between them and `tail` after the last, as one WAV."""
    inputs, parts = [], []
    for i, clip in enumerate(clips):
        inputs += ["-i", str(clip)]
        pad = tail if i == len(clips) - 1 else gap
        parts.append(
            f"[{i}:a]aresample={RATE},aformat=channel_layouts=mono,apad=pad_dur={pad}[a{i}]"
        )
    joined = "".join(f"[a{i}]" for i in range(len(clips)))
    graph = ";".join(parts) + f";{joined}concat=n={len(clips)}:v=0:a=1[out]"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            *inputs,
            "-filter_complex",
            graph,
            "-map",
            "[out]",
            "-ar",
            str(RATE),
            str(target),
        ],
        check=True,
    )


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def main() -> int:
    plan = json.loads((HERE / "narration.json").read_text(encoding="utf-8"))
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or plan["voice"]["project"]
    api = session(project)
    AUDIO.mkdir(parents=True, exist_ok=True)
    gap, tail = plan["gapSeconds"], plan["tailSeconds"]
    timings: dict = {"scenes": []}
    for scene in plan["scenes"]:
        spoken = [s.get("say") or s["text"] for s in scene["sentences"]]
        clips, sentences, t = [], [], 0.0
        for i, sentence in enumerate(scene["sentences"]):
            clip = speak(spoken[i], plan["voice"], api)
            length = duration(clip)
            sentences.append(
                {"text": sentence["text"], "start": round(t, 3), "end": round(t + length, 3)}
            )
            t += length + (gap if i < len(spoken) - 1 else tail)
            clips.append(clip)
        target = AUDIO / f"{scene['id']}.wav"
        scene_audio(clips, gap, tail, target)
        timings["scenes"].append(
            {
                "id": scene["id"],
                "kind": scene["kind"],
                "duration": round(duration(target), 3),
                "sentences": sentences,
            }
        )
        print(f"{scene['id']:<13} {timings['scenes'][-1]['duration']:6.2f} s")
    (OUT / "timings.json").write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")
    total = sum(s["duration"] for s in timings["scenes"])
    print(f"narration {total:.1f} s")

    # The script for review, with the time each scene starts in the final cut (0.5 s dissolves).
    lines = [
        f"# {plan['title']} (demo video script)",
        "",
        "> Generated by `tools/video/narrate.py` from `tools/video/narration.json`; edit the",
        "> JSON, not this file.",
        f"> Voice: Google Cloud Text-to-Speech, {plan['voice']['voice']}. Recorded on",
        "> production with the public demo account (synthetic data). Sources: ACFE, *Occupational",
        "> Fraud 2024: A Report to the Nations* (5% of revenue; median loss USD 141,000 for",
        "> organizations under 100 employees).",
        "",
        "| Time | Scene | Shot | Voice-over |",
        "|---|---|---|---|",
    ]
    start = 0.0
    for scene, timing in zip(plan["scenes"], timings["scenes"], strict=False):
        voice_over = " ".join(s["text"] for s in scene["sentences"]).replace("|", "\\|")
        lines.append(f"| {clock(start)} | {scene['id']} | {scene['shot']} | {voice_over} |")
        start += timing["duration"] - 0.5
    lines += ["", f"Total: about {clock(start + 0.5)}.", ""]
    SCRIPT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {SCRIPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
