# -*- coding: utf-8 -*-
"""6단계 검수 시트: 만든 장(mp4)에서 1초마다 프레임을 뽑아 한 장으로 붙이고, beat 시각 칸에 빨간 테두리를 친다.

build.py가 끝에 자동으로 부른다. 결과 = 에피소드/검수/<장이름>.jpg
Claude는 이 그림을 Read로 열어 빨간 칸마다 beat의 'what'이 실제로 화면에 보이는지 확인한다.
안 보이면 ss·t를 고치고 그 장만 다시 만든다(--only).
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def review_sheet(s: dict, mp4: Path, out_dir: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype("malgun.ttf", 22)
        big = ImageFont.truetype("malgunbd.ttf", 26)
    except OSError:
        font = big = ImageFont.load_default()
    ss, t = float(s["ss"]), float(s["t"])
    beats = [(float(b["at"]) - ss, b["what"]) for b in s.get("beats") or []]
    times = [round(x * 1.0, 1) for x in range(int(t) + 1) if x < t]
    for rel, _ in beats:                        # beat 시각 프레임은 반드시 넣는다
        if 0 <= rel < t and all(abs(rel - x) > 0.25 for x in times):
            times.append(round(rel, 2))
    times.sort()
    tmp = out_dir / "_tmp.jpg"
    tiles = []
    for at in times:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(mp4), "-frames:v", "1",
                        "-vf", "scale=240:-2", str(tmp)], check=True)
        im = Image.open(tmp).convert("RGB")
        d = ImageDraw.Draw(im)
        hit = [w for rel, w in beats if abs(rel - at) <= 0.25]
        d.rectangle([0, 0, 150, 28], fill=(0, 0, 0))
        d.text((6, 2), f"{at:.1f}초 (원본 {ss + at:.1f})", font=font, fill=(255, 200, 80))
        if hit:
            d.rectangle([0, 0, im.width - 1, im.height - 1], outline=(255, 40, 40), width=6)
        tiles.append((im, hit))
    tmp.unlink(missing_ok=True)
    cols = 6
    w, h = tiles[0][0].size
    rows = (len(tiles) + cols - 1) // cols
    head_h = 70 + 30 * len(beats)
    sheet = Image.new("RGB", (cols * (w + 6), head_h + rows * (h + 6)), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    head = s.get("head") or " / ".join("".join(w for w, _ in ln) for ln in s.get("lines") or [])
    body = s.get("body") or s.get("sub") or ""
    d.text((10, 8), f"{s['name']}  {head}", font=big, fill=(255, 255, 255))
    d.text((10, 40), body.replace("\n", " / "), font=font, fill=(200, 200, 200))
    for i, (rel, what) in enumerate(beats):
        d.text((10, 70 + 30 * i), f"beat {rel:.1f}초: {what}", font=font, fill=(255, 90, 90))
    for i, (im, _) in enumerate(tiles):
        sheet.paste(im, ((i % cols) * (w + 6), head_h + (i // cols) * (h + 6)))
    p = out_dir / f"{s['name']}.jpg"
    sheet.save(p, quality=85)
    return p
