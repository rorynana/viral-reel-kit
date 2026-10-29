"""videocard.json 검증·정규화. 화면(운영 트랙)과 LLM 카피가 이 꼴로 맞춰 준다."""
from __future__ import annotations

import copy
import re
from pathlib import Path

VIDEO_KINDS = ("cover", "win43", "full")
STILL_KINDS = ("statement", "cta")
MAX_SLIDES = 10          # 인스타 API 캐러셀 한도
_NAME = re.compile(r"^\d{2}_")
CTA_BADGE = "소개"


def normalize_spec(raw: dict, cta_defaults: dict) -> dict:
    spec = copy.deepcopy(raw or {})
    slides = spec.get("slides") or []
    if not slides:
        raise ValueError("slides가 비어 있습니다")
    if len(slides) > MAX_SLIDES:
        raise ValueError(f"장은 최대 {MAX_SLIDES}장입니다(인스타 캐러셀 한도), 지금 {len(slides)}장")
    if slides[0].get("kind") != "cover":
        raise ValueError("첫 장은 kind=cover(표지)여야 합니다")
    for i, s in enumerate(slides, 1):
        name = str(s.get("name") or "")
        if not _NAME.match(name):
            raise ValueError(f"{i}번째 장 이름은 'NN_' 접두여야 합니다: {name!r}")
        kind = s.get("kind")
        if kind in VIDEO_KINDS:
            for k in ("src", "ss", "t"):
                if k not in s:
                    raise ValueError(f"{name}: 영상 장은 {k}가 필요합니다")
            if not (3 <= float(s["t"]) <= 20):
                raise ValueError(f"{name}: 구간 길이 t는 3~20초입니다({s['t']})")
            if kind == "cover":
                s.setdefault("fx", 0.5); s.setdefault("badge", "AI 트렌드")
                if len(s.get("lines") or []) != 3:
                    raise ValueError(f"{name}: 표지 헤드는 3줄 고정입니다")
            else:
                for k in ("pill", "head", "body", "foot"):
                    if not s.get(k):
                        raise ValueError(f"{name}: {k}가 비었습니다")
            if kind == "full" and "crop" in s and len(s["crop"]) != 4:
                raise ValueError(f"{name}: crop은 [w, h, x, y]")
        elif kind == "statement":
            if not s.get("lines"):
                raise ValueError(f"{name}: statement lines가 비었습니다")
            s.setdefault("sub", ""); s.setdefault("dark", True)
        elif kind == "cta":
            for k in ("head", "sub", "title", "items", "chip"):
                if not s.get(k):
                    s[k] = cta_defaults.get(k)
            s.setdefault("badge", CTA_BADGE)
        else:
            raise ValueError(f"{name}: 모르는 kind {kind!r}")
    return spec


def clip_keys(spec: dict) -> list[str]:
    out = []
    for s in spec.get("slides") or []:
        src = str(s.get("src") or "")
        if src.startswith("clip:") and src[5:] not in out:
            out.append(src[5:])
    return out


def resolve_clip_paths(spec: dict, clips_dir: Path) -> dict:
    spec = copy.deepcopy(spec)
    for s in spec["slides"]:
        src = str(s.get("src") or "")
        if src.startswith("clip:"):
            p = Path(clips_dir) / f"{src[5:]}.mp4"
            if not p.exists():
                raise FileNotFoundError(f"원본 없음: {src[5:]}")
            s["src"] = str(p)
    return spec


def output_name(slide: dict) -> str:
    return f"{slide['name']}.{'mp4' if slide.get('kind') in VIDEO_KINDS else 'png'}"
