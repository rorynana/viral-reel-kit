# -*- coding: utf-8 -*-
"""0단계 준비 확인: 부품 설치, ffmpeg, 키트 영상, 내 테마를 한 번에 본다.

  python tools/check.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil

from _kit import ROOT, SEEDS, config


def main():
    missing = [m for m in ("PIL", "yaml", "yt_dlp") if importlib.util.find_spec(m) is None]
    print("부품:", "OK" if not missing else "없음 " + ", ".join(missing) + " → python -m pip install -r requirements.txt")
    print("ffmpeg:", "OK" if shutil.which("ffmpeg") else "없음 → winget install --id Gyan.FFmpeg -e 후 터미널을 새로 열기")
    meta = SEEDS / "clips" / "_sources.json"
    n = len(json.loads(meta.read_text(encoding="utf-8"))) if meta.exists() else 0
    print("키트 영상:", f"{n}개" if n else "없음 → 키트를 다시 받으세요")
    if missing:
        return
    name = config().get("theme") or "mine"
    t = ROOT / "themes" / name / "theme.json"
    print("내 테마:", f"OK ({json.loads(t.read_text(encoding='utf-8')).get('name')})" if t.exists()
          else "아직 없음 → 이름·핸들·색을 물어보고 tools/theme.py 로 만든다")


if __name__ == "__main__":
    main()
