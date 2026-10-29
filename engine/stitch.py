"""4:5 장들을 9:16 릴스 하나로. 9/17 릴스판(편집 툴 수동, 크로스페이드로 글자 겹침)의 자동 대체.

- 각 장을 1080×1350으로 맞춰 1080×1920 검정 캔버스 세로 중앙에 놓는다(캐러셀과 픽셀 동일).
- 전환 = 딥투블랙: 장 끝 fade out 0.2초, 다음 장 fade in 0.2초. 크로스페이드 금지.
  첫 장은 fade in을 넣지 않는다. 인스타가 0초 프레임을 릴스 표지로 쓰기 때문에 검은 표지가 됐다(9/29 스탤론편).
- 정지 PNG는 still_sec 동안, 무음 트랙을 만들어 concat의 오디오 스트림 수를 맞춘다.
- 규격 통일: 30fps·yuv420p·AAC 44.1k stereo, 끝에 loudnorm. 워터마크는 우상단 안전영역(위 120px, 오른쪽 60px).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from probe import ffprobe_meta

REEL_W, REEL_H = 1080, 1920
CARD_W, CARD_H = 1080, 1350
FPS = 30
DIP = 0.2
STILL_SEC = 3.0         # 정지 장은 소리도 움직임도 없다. 4초면 사례에서 넘어온 뒤 늘어진다(9/22 2·3편 실측)
MAX_SEC = 90.0
_VIDEO_EXT = {".mp4", ".mov", ".m4v"}


def _is_video(p: Path) -> bool:
    return p.suffix.lower() in _VIDEO_EXT


def stitch(items: list[Path], out: Path, *, watermark: Path | None = None, still_sec: float = STILL_SEC,
           run=subprocess.run) -> dict:
    items = [Path(p) for p in items]
    if not items:
        raise ValueError("이어붙일 장이 없습니다")
    durs, has_audio = [], []
    for p in items:
        if _is_video(p):
            m = ffprobe_meta(p); durs.append(m["duration"]); has_audio.append(m["has_audio"])
        else:
            durs.append(float(still_sec)); has_audio.append(False)
    total = sum(durs)
    if total > MAX_SEC:
        raise ValueError(f"릴스 총 길이 {total:.1f}초가 상한 {MAX_SEC:.0f}초를 넘습니다")

    cmd = ["ffmpeg", "-v", "error", "-y"]
    fc, idx = [], 0
    labels = []
    for i, (p, d, aud) in enumerate(zip(items, durs, has_audio)):
        if _is_video(p):
            cmd += ["-i", str(p)]; vi = idx; idx += 1
        else:
            cmd += ["-loop", "1", "-t", f"{d:.3f}", "-i", str(p)]; vi = idx; idx += 1
        if aud:
            ai = vi
        else:
            cmd += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]; ai = idx; idx += 1
        fo = max(0.0, d - DIP)
        fade_in = "" if i == 0 else f"fade=t=in:st=0:d={DIP},"
        fc.append(f"[{vi}:v]scale={CARD_W}:{CARD_H}:force_original_aspect_ratio=decrease,"
                  f"pad={REEL_W}:{REEL_H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS},format=yuv420p,"
                  f"trim=duration={d:.3f},{fade_in}fade=t=out:st={fo:.3f}:d={DIP},setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[{ai}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={d:.3f},"
                  f"afade=t=in:st=0:d={DIP},afade=t=out:st={fo:.3f}:d={DIP},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    fc.append("".join(labels) + f"concat=n={len(items)}:v=1:a=1[vc][ac]")
    vout = "[vc]"
    if watermark:
        cmd += ["-i", str(watermark)]; wi = idx; idx += 1
        fc.append(f"[{wi}:v]scale=220:-1[wm];[vc][wm]overlay=W-w-60:120:format=auto[vo]"); vout = "[vo]"
    fc.append("[ac]loudnorm=I=-16:TP=-1.5:LRA=11[ao]")
    cmd += ["-filter_complex", ";".join(fc), "-map", vout, "-map", "[ao]",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", str(out)]
    cp = run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if getattr(cp, "returncode", 0) != 0:
        raise RuntimeError(f"릴스 이어붙이기 실패: {(cp.stderr or '')[-800:]}")
    return {"path": str(out), "seconds": round(total, 1), "items": len(items)}


def make_deck(thumbs: list[Path], out: Path, cols: int = 3) -> Path:
    from PIL import Image
    tw_, th_ = 360, 450
    rows = (len(thumbs) + cols - 1) // cols
    cv = Image.new("RGB", (tw_ * cols + 10 * (cols + 1), th_ * rows + 10 * (rows + 1)), (240, 240, 240))
    for i, p in enumerate(thumbs):
        cv.paste(Image.open(p).convert("RGB").resize((tw_, th_), Image.LANCZOS),
                 (10 + (i % cols) * (tw_ + 10), 10 + (i // cols) * (th_ + 10)))
    out.parent.mkdir(parents=True, exist_ok=True)
    cv.save(out)
    return out
