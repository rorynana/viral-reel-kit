# -*- coding: utf-8 -*-
"""3단계 구간 보기: 영상마다 장면 6개를 초 표시와 함께 한 장으로 이어 붙인다.

  py -3.11 tools/sheet.py <에피소드이름>

결과 = 에피소드/sheets/<영상id>.jpg. Claude가 이 그림을 보고 어느 초부터 쓸지(ss) 정한다.
"""
from __future__ import annotations

import subprocess
import sys

from _kit import episode, stop


def main():
    if len(sys.argv) < 2:
        stop("사용법: py -3.11 tools/sheet.py <에피소드이름>")
    from PIL import Image, ImageDraw, ImageFont
    from probe import ffprobe_meta

    ep = episode(sys.argv[1])
    clips = sorted((ep / "clips").glob("*.mp4"))
    if not clips:
        stop(f"{ep / 'clips'} 에 영상이 없습니다. 먼저 fetch.py로 받으세요.")
    out_dir = ep / "sheets"
    out_dir.mkdir(exist_ok=True)
    tmp = out_dir / "_tmp.jpg"
    try:
        font = ImageFont.truetype("malgun.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    for clip in clips:
        dur = ffprobe_meta(clip)["duration"]
        tiles = []
        for i in range(6):
            at = dur * (i + 0.5) / 6
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(clip), "-frames:v", "1",
                            "-vf", "scale=-2:420", str(tmp)], check=True)
            im = Image.open(tmp).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 120, 40], fill=(0, 0, 0))
            d.text((8, 4), f"{at:.1f}초", font=font, fill=(255, 200, 80))
            tiles.append(im)
        w, h = tiles[0].size
        sheet = Image.new("RGB", (w * 3 + 20, h * 2 + 10), (30, 30, 30))
        for i, t in enumerate(tiles):
            sheet.paste(t.resize((w, h)), ((i % 3) * (w + 10), (i // 3) * (h + 10)))
        p = out_dir / f"{clip.stem}.jpg"
        sheet.save(p, quality=85)
        print(f"{clip.stem}: 길이 {dur:.1f}초 → {p}")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
