# -*- coding: utf-8 -*-
"""키트 공용: 폴더 위치, 설정(kit_config.yaml), 테마, CTA 기본 문구. 인터넷 서버에 접속하는 코드는 없다."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
EPISODES = ROOT / "episodes"
SEEDS = ROOT / "seeds"
sys.path.insert(0, str(ENGINE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def config() -> dict:
    import yaml
    return yaml.safe_load((ROOT / "kit_config.yaml").read_text(encoding="utf-8")) or {}


def stop(msg: str, code: int = 2):
    print("멈춤:", msg)
    sys.exit(code)


def episode(arg: str) -> Path:
    """에피소드 폴더. 이름만 주면 episodes/ 아래에서 찾는다."""
    p = Path(arg)
    if not p.is_absolute() and not p.exists():
        p = EPISODES / arg
    return p


def theme_dir(name: str | None = None) -> Path:
    name = name or config().get("theme") or "mine"
    d = ROOT / "themes" / name
    if not (d / "theme.json").exists():
        stop(f"테마 {name} 가 없습니다: {d}\\theme.json")
    return d


DEFAULT_CTA = {"head": "이런 소식이 / 궁금하다면?", "sub": "매일 바이럴을 골라 드립니다",
               "title": "이 계정에서 보는 것",
               "items": ["이번 주 터진 영상", "왜 터졌는지 한 줄", "내 일에 쓰는 법"],
               "chip": "팔로우하고 다음 편 받기", "hashtag": "#바이럴"}


def theme_cta(d: Path) -> dict:
    t = json.loads((d / "theme.json").read_text(encoding="utf-8"))
    c = t.get("cta") or {}
    out = dict(DEFAULT_CTA)
    for k in ("head", "sub", "title", "chip", "hashtag"):
        if c.get(k):
            out[k] = str(c[k]).strip()
    if c.get("items"):
        out["items"] = [str(x) for x in c["items"]]
    return out


def clip_key(url: str) -> str:
    """링크에서 영상 id를 뽑아 파일 이름으로 쓴다."""
    for pat in (r"instagram\.com/(?:reel|reels|p)/([\w-]+)", r"tiktok\.com/.*/video/(\d+)",
                r"(?:youtube\.com/shorts/|youtu\.be/|[?&]v=)([\w-]{6,})", r"reddit\.com/r/\w+/comments/(\w+)",
                r"(?:x|twitter)\.com/\w+/status/(\d+)"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return re.sub(r"\W+", "_", url.split("//")[-1])[-40:]
