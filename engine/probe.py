"""원본 영상 메타·판별·프레임. ffprobe/ffmpeg 서브프로세스만 쓴다(서버 이미지에 있음).

정지영상 판별: 균등 간격 프레임 n장을 뽑아 이웃끼리 평균 밝기 차를 잰다. 전부 threshold 아래면
"정지 이미지에 소리만 얹은 영상"으로 본다(9/15 조사에서 이런 영상이 소재에 섞인 사고 근거).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if cp.returncode != 0:
        raise RuntimeError(f"{cmd[0]} 실패 rc={cp.returncode}: {(cp.stderr or '')[-600:]}")
    return cp


def _fps(rate: str) -> float:
    if "/" in rate:
        a, b = rate.split("/", 1)
        return float(a) / float(b) if float(b) else 0.0
    return float(rate or 0)


def ffprobe_meta(path: Path) -> dict:
    cp = _run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(path)])
    data = json.loads(cp.stdout or "{}")
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return {"duration": float((data.get("format") or {}).get("duration") or 0.0),
            "width": int(v.get("width") or 0), "height": int(v.get("height") or 0),
            "fps": _fps(str(v.get("r_frame_rate") or "0")), "has_audio": has_audio}


def is_43(width: int, height: int) -> bool:
    """4:3 창(유튜브 옛 뮤비·AI 뮤비 상당수). 위 1080×810 + 아래 단색 밴드 레이아웃 대상."""
    return height > 0 and abs(width / height - 4 / 3) < 0.05


def sample_frames(path: Path, out_dir: Path, n: int = 6) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dur = ffprobe_meta(path)["duration"]
    paths = []
    for i in range(n):
        at = dur * (i + 0.5) / n
        p = out_dir / f"frame_{i:02d}.jpg"
        _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", str(p)])
        paths.append(p)
    return paths


def is_static(path: Path, n: int = 5, threshold: float = 2.0) -> bool:
    from PIL import Image, ImageChops, ImageStat
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        frames = sample_frames(path, Path(td), n=n)
        imgs = [Image.open(p).convert("L").resize((160, 90)) for p in frames]
        for a, b in zip(imgs, imgs[1:]):
            if ImageStat.Stat(ImageChops.difference(a, b)).mean[0] >= threshold:
                return False
    return True


def preview_360p(path: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", "scale=-2:360", "-c:v", "libx264", "-crf", "28",
          "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(out)],
         timeout=300)
    return out


def make_test_clip(out: Path, seconds: float = 2.0, size: str = "640x480", static: bool = False,
                   audio: bool = True) -> Path:
    """테스트·발행 시험용 합성 영상. static=True면 단색 화면(정지영상 판별 검사용)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    src = f"color=c=0x336699:size={size}:rate=30" if static else f"testsrc=size={size}:rate=30"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(seconds), "-i", src]
    if audio:
        cmd += ["-f", "lavfi", "-t", str(seconds), "-i", "sine=frequency=440:sample_rate=44100"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30"]
    if audio:
        cmd += ["-c:a", "aac", "-ar", "44100", "-ac", "2"]
    cmd += ["-shortest", str(out)]
    _run(cmd)
    return out
