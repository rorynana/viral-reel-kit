# -*- coding: utf-8 -*-
"""5단계 글자 검사: spec.json과 캡션.txt를 만들기 전에 검사한다. FAIL이 하나라도 있으면 build가 안 돈다.

  py -3.11 tools/lint.py <에피소드이름>

보는 것: 장 구성(첫 장 표지, 10장 이하, 표지 3줄), 글자가 칸에 들어가는지, em-dash, 영상 구간이 원본 길이 안인지,
사례 장의 beats(카피가 가리키는 장면이 구간 안에 2초 이상 보이는지), 구간이 카피 읽는 시간보다 긴지,
캡션 해시태그 3개(브랜드 태그 포함).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from _kit import episode, stop, theme_cta, theme_dir

fails = 0


def out(tag, name, msg):
    global fails
    if tag == "FAIL":
        fails += 1
    print(f"[{tag}] {name}: {msg}")


def load_spec(ep):
    p = ep / "spec.json"
    if not p.exists():
        stop(f"{p} 가 없습니다. Claude에게 장별 카피를 spec.json으로 써 달라고 하세요.")
    return json.loads(p.read_text(encoding="utf-8"))


# 카피가 가리키는 장면(beat)이 구간 안에서 이만큼은 머물러야 한다(10/6 사례3: 핵심 대사 전에 다음 장으로 넘어감)
BEAT_LEAD = 0.3
BEAT_DWELL = 2.0
READ_CPS = 9.0      # 영상 위 자막을 읽는 속도(글자/초, 공백 제외)
READ_PAD = 1.5      # 장 전환 뒤 눈이 글자에 닿는 시간
READ_MIN = 6.0


def text_len(s) -> int:
    return len(re.sub(r"\s", "", s["head"] + s["body"]))


def read_seconds(s) -> float:
    return max(READ_MIN, text_len(s) / READ_CPS + READ_PAD)


def check_beats(s, n):
    """사례 장은 beats = [{"at": 원본 초, "what": "카피가 가리키는 화면"}] 가 있어야 한다."""
    beats = s.get("beats") or []
    if not beats:
        out("FAIL", n, "beats가 없습니다. 헤드·본문이 가리키는 장면의 원본 시각을 적으세요")
        return
    ss, t = float(s["ss"]), float(s["t"])
    lo, hi = ss + BEAT_LEAD, ss + t - BEAT_DWELL
    for b in beats:
        at, what = b.get("at"), (b.get("what") or "").strip()
        if at is None or not what:
            out("FAIL", n, f"beat에 at·what이 둘 다 있어야 합니다: {b}")
            continue
        ok = lo <= float(at) <= hi
        out("PASS" if ok else "FAIL", n,
            f"beat {float(at):.1f}초 '{what}' (구간 {ss:.1f}~{ss + t:.1f}초, {BEAT_DWELL:.0f}초 이상 보여야 함)")


def check(ep) -> int:
    td = theme_dir()
    os.environ["KIT_THEME"] = str(td)
    from PIL import Image, ImageDraw
    from design import F, tw, wrap_lines, W, M
    from videocard import fit_size, _pairs
    from probe import ffprobe_meta
    from spec import normalize_spec

    raw = load_spec(ep)
    try:
        spec = normalize_spec(raw, theme_cta(td))
    except ValueError as e:
        out("FAIL", "구성", str(e))
        return 1
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    budget = W - 2 * M
    for s in spec["slides"]:
        n, k = s["name"], s["kind"]
        if "—" in json.dumps(s, ensure_ascii=False):
            out("FAIL", n, "em-dash(—) 금지")
        if k in ("cover", "win43", "full"):
            src = ep / s["src"]
            if not src.exists():
                out("FAIL", n, f"원본 없음: {s['src']}")
            else:
                dur = ffprobe_meta(src)["duration"]
                end = float(s["ss"]) + float(s["t"])
                if end > dur + 0.05:
                    out("FAIL", n, f"구간 {s['ss']}+{s['t']}초가 원본 길이 {dur:.1f}초를 넘음")
        if k == "cover":
            lines = _pairs(s["lines"])
            size = fit_size(d, lines, 100, budget)
            out("PASS" if size >= 80 else "FAIL", n, f"표지 헤드 글자 {size}px(80 이상)")
            sw = tw(d, s.get("sub", ""), F("sb", 38))
            out("PASS" if sw <= budget else "FAIL", n, f"서브 폭 {sw}/{budget}")
        elif k in ("win43", "full"):
            hs = fit_size(d, [[(s["head"], 0)]], 64, budget)
            out("PASS" if hs >= 52 else "FAIL", n, f"헤드 글자 {hs}px(52 이상) '{s['head']}'")
            bl = wrap_lines(d, budget, s["body"], F("sb", 36))
            out("PASS" if len(bl) <= 2 else "FAIL", n, f"본문 {len(bl)}줄(2줄 한도)")
            for key, f in (("pill", F("bd", 30)), ("foot", F("bd", 28))):
                w_ = tw(d, s[key], f) + 44
                out("PASS" if w_ <= budget else "FAIL", n, f"{key} 폭 {w_}/{budget}")
            if not (5 <= float(s["t"]) <= 15):
                out("WARN", n, f"구간 {s['t']}초(권장 6~12초)")
            check_beats(s, n)
            need = read_seconds(s)
            out("PASS" if float(s["t"]) >= need else "FAIL", n,
                f"구간 {s['t']}초, 읽는 시간 {need:.1f}초 이상 필요(헤드+본문 {text_len(s)}자)")
        elif k == "statement":
            size = fit_size(d, _pairs(s["lines"]), 92, budget)
            out("PASS" if size >= 70 else "WARN", n, f"결론 글자 {size}px")

    # 표지 장면이 사례 장에 또 나오면 안 된다(10/6 대표 피드백). 같은 원본(사본 접미사 무시)에서 구간이 겹치면 FAIL
    base = lambda s: Path(s["src"]).stem.split("_")[0]
    cov = [s for s in spec["slides"] if s["kind"] == "cover"]
    for c in cov:
        c0, c1 = float(c["ss"]), float(c["ss"]) + float(c["t"])
        for s in spec["slides"]:
            if s["kind"] in ("win43", "full") and base(s) == base(c):
                s0, s1 = float(s["ss"]), float(s["ss"]) + float(s["t"])
                ok = c1 <= s0 or s1 <= c0
                out("PASS" if ok else "FAIL", c["name"],
                    f"표지 구간 {c0:.1f}~{c1:.1f}초가 {s['name']}({s0:.1f}~{s1:.1f}초)와 " + ("안 겹침" if ok else "겹침. 표지는 사례에 안 나오는 장면으로"))

    cap_p = ep / "캡션.txt"
    if not cap_p.exists():
        out("FAIL", "캡션", "캡션.txt가 없습니다")
    else:
        cap = cap_p.read_text(encoding="utf-8")
        if "—" in cap:
            out("FAIL", "캡션", "em-dash(—) 금지")
        tags = re.findall(r"#\S+", cap)
        brand = theme_cta(td)["hashtag"]
        out("PASS" if len(tags) == 3 else "FAIL", "캡션", f"해시태그 {len(tags)}개(3개): {' '.join(tags)}")
        if brand not in tags:
            out("FAIL", "캡션", f"브랜드 태그 {brand} 가 없습니다")
        if re.search(r"(?<![\w.])@\w", cap):
            out("WARN", "캡션", "@멘션이 있습니다. 같은 멘션은 하루 한 번만 올라갑니다")
    print("RESULT:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


def main():
    if len(sys.argv) < 2:
        stop("사용법: py -3.11 tools/lint.py <에피소드이름>")
    sys.exit(check(episode(sys.argv[1])))


if __name__ == "__main__":
    main()
