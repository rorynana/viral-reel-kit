# -*- coding: utf-8 -*-
"""내 테마 만들기: 채널 이름·핸들·색·소개 문구로 themes/mine 을 만든다. 카드 로고와 마지막 장(CTA)이 내 것이 된다.

  python tools/theme.py --name "성윤의 AI 마케팅" --handle "seongyun.ai" --color "#2F6BFF" \
      --head "AI 마케팅이 / 궁금하다면?" --sub "매주 터진 영상을 마케터 눈으로 풀어 드립니다" \
      --items "이번 주 터진 영상|왜 터졌는지 한 줄|내 일에 쓰는 법" --chip "팔로우하고 다음 편 받기" --hashtag "#성윤의AI마케팅"

로고는 채널 이름 글자로 그린다(로고 파일이 있으면 --logo 로 줘도 된다).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil

from _kit import ROOT, stop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--handle", required=True)
    ap.add_argument("--color", default="#FF7F00")
    ap.add_argument("--head", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--title", default="이 계정에서 보는 것")
    ap.add_argument("--items", default="")
    ap.add_argument("--chip", default="팔로우하고 다음 편 받기")
    ap.add_argument("--hashtag", default="")
    ap.add_argument("--logo", default="")
    a = ap.parse_args()
    if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", a.color):
        stop("색은 #2F6BFF 처럼 # 뒤 여섯 자리로 주세요.")
    from PIL import Image, ImageDraw, ImageFont

    d = ROOT / "themes" / "mine"
    d.mkdir(parents=True, exist_ok=True)
    if a.logo:
        shutil.copyfile(a.logo, d / "logo.png")
    else:
        f = ImageFont.truetype(str(ROOT / "themes" / "fonts" / "Paperlogy-8ExtraBold.ttf"), 120)
        box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), a.name, font=f)
        im = Image.new("RGBA", (box[2] - box[0] + 20, box[3] - box[1] + 20), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10 - box[0], 10 - box[1]), a.name, font=f, fill=(24, 24, 28, 255))
        im.save(d / "logo.png")
    tag = a.hashtag or "#" + re.sub(r"\s+", "", a.name)
    theme = {"name": a.name, "colors": {"accent": "#" + a.color.lstrip("#").upper()},
             "fonts": {"dir": "../fonts", "med": "Paperlogy-5Medium.ttf", "sb": "Paperlogy-6SemiBold.ttf",
                       "bd": "Paperlogy-7Bold.ttf", "xb": "Paperlogy-8ExtraBold.ttf", "bk": "Paperlogy-9Black.ttf"},
             "logo": "logo.png", "handle": a.handle.lstrip("@"),
             "cta": {"title": a.title, "chip": a.chip, "hashtag": tag}}
    if a.head:
        theme["cta"]["head"] = a.head
    if a.sub:
        theme["cta"]["sub"] = a.sub
    if a.items:
        theme["cta"]["items"] = [x.strip() for x in a.items.split("|") if x.strip()][:3]
    (d / "theme.json").write_text(json.dumps(theme, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"내 테마 완성: {a.name} (@{theme['handle']}, 색 {theme['colors']['accent']}, 해시태그 {tag})")
    print(f"→ {d}")


if __name__ == "__main__":
    main()
