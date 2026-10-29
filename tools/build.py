# -*- coding: utf-8 -*-
"""6단계 만들기: 검사 통과한 spec.json으로 카드(4:5)와 릴스(9:16), 전체 그리드를 만든다.

  py -3.11 tools/build.py <에피소드이름>            (전 장)
  py -3.11 tools/build.py <에피소드이름> --only 03_사례2   (한 장만 다시)

결과 = 에피소드/build/ (장별 mp4·png), 에피소드/릴스.mp4, 에피소드/전체그리드.png
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from _kit import episode, stop, theme_cta, theme_dir
import lint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ep = episode(a.episode)

    print("== 글자 검사")
    if lint.check(ep) != 0:
        stop("검사에서 FAIL이 나서 만들지 않았습니다. 위 FAIL 줄을 고치고 다시 실행하세요.")

    from videocard import LAYERS, statement, cta, render_video
    from spec import normalize_spec, output_name
    from stitch import stitch, make_deck

    spec = normalize_spec(lint.load_spec(ep), theme_cta(theme_dir()))
    out = ep / "build"
    lay = out / "_layers"
    lay.mkdir(parents=True, exist_ok=True)

    print("== 장 만들기")
    reviews = []
    for s in spec["slides"]:
        if a.only and s["name"] != a.only:
            continue
        mid = lay / f"{s['name']}_mid.png"
        if s["kind"] in LAYERS:
            layer = LAYERS[s["kind"]](s)
            lp = lay / f"{s['name']}.png"
            layer.save(lp)
            mp4 = out / f"{s['name']}.mp4"
            render_video(s, str(ep / s["src"]), str(lp), str(mp4))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(float(s["t"]) / 2), "-i", str(mp4),
                            "-frames:v", "1", str(mid)], check=True)
            from review import review_sheet
            reviews.append(review_sheet(s, mp4, ep / "검수"))
            print(f"  영상 {s['name']} {s['t']}초")
        else:
            img = statement(s["lines"], dark=bool(s.get("dark", True)), sub=s.get("sub") or None) \
                if s["kind"] == "statement" else cta(s)
            png = out / f"{s['name']}.png"
            img.convert("RGB").save(png)
            shutil.copyfile(png, mid)
            print(f"  정지 {s['name']}")

    items = [out / output_name(s) for s in spec["slides"]]
    missing = [p.name for p in items if not p.exists()]
    if missing:
        stop("아직 안 만든 장이 있어 릴스를 못 붙였습니다: " + ", ".join(missing))
    print("== 릴스 이어 붙이기")
    r = stitch(items, ep / "릴스.mp4")
    make_deck([lay / f"{s['name']}_mid.png" for s in spec["slides"]], ep / "전체그리드.png")
    print(f"\n완성: 릴스 {r['seconds']}초, 카드 {len(items)}장")
    print(f"  릴스   {ep / '릴스.mp4'}")
    print(f"  그리드 {ep / '전체그리드.png'}")
    print(f"  카드   {out}")
    if reviews:
        print("\n== 검수 시트 (빨간 칸마다 beat가 화면에 보이는지 Read로 확인. 안 보이면 ss·t 고치고 --only)")
        for p in reviews:
            print(f"  {p}")


if __name__ == "__main__":
    main()
