# -*- coding: utf-8 -*-
"""1단계 소재 찾기: 키트에 들어 있는 후보표(seeds/후보.md)를 보여 준다. 인터넷에 접속하지 않는다.

  python tools/find.py                 (전체)
  python tools/find.py --kit           (키트에 영상이 들어 있는 것만)
  python tools/find.py --group "AI 영상" (한 묶음만: AI 영상 / 뷰티 브랜드 / 생활·라이프)

후보는 시드 계정(seeds/시드계정.md)이 최근 30일에 올린 영상 중 평소보다 많이 본 것이다.
"""
from __future__ import annotations

import argparse

from _kit import SEEDS, stop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", action="store_true")
    ap.add_argument("--group", default="")
    a = ap.parse_args()
    p = SEEDS / "후보.md"
    if not p.exists():
        stop("seeds/후보.md 가 없습니다. 키트를 다시 받으세요.")
    lines = p.read_text(encoding="utf-8").splitlines()
    head = [l for l in lines if l.startswith("| # ") or l.startswith("|---")]
    rows = [l for l in lines if l.startswith("| ") and not l.startswith("| # ")]
    if a.kit or a.group:
        rows = [l for l in rows if "있음" in l]
    if a.group:
        rows = [l for l in rows if f"있음 · {a.group}" in l]
    if not rows:
        stop("조건에 맞는 후보가 없습니다. 묶음 이름은 AI 영상 / 뷰티 브랜드 / 생활·라이프 입니다.")
    print(lines[0])
    print("\n".join(head + rows))
    print(f"\n후보 {len(rows)}건. 키트 영상이 '있음'인 것은 바로 쓸 수 있습니다.")


if __name__ == "__main__":
    main()
