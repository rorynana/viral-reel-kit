# -*- coding: utf-8 -*-
"""2단계 원본 받기: 링크를 받아 에피소드 폴더 clips/ 에 mp4로 넣는다.

  python tools/fetch.py <에피소드이름> <링크1> <링크2> ...

키트에 이미 들어 있는 영상(seeds/clips)은 내려받지 않고 복사한다(인터넷 안 씀).
없는 영상만 yt-dlp 로 받는다. 레딧은 로그인 없이 못 받는다.
받은 영상 정보(계정·조회·길이·소리)는 clips/_sources.json 에 쌓인다. 카드 하단 출처 줄(foot)의 숫자는 여기 값을 쓴다.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sys

from _kit import SEEDS, clip_key, episode, stop


def main():
    if len(sys.argv) < 3:
        stop("사용법: python tools/fetch.py <에피소드이름> <링크1> <링크2> ...")
    from probe import ffprobe_meta

    ep = episode(sys.argv[1])
    clips = ep / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    src_file = clips / "_sources.json"
    sources = json.loads(src_file.read_text(encoding="utf-8")) if src_file.exists() else {}
    seed_meta = json.loads((SEEDS / "clips" / "_sources.json").read_text(encoding="utf-8"))

    ok, bad = 0, []
    for url in sys.argv[2:]:
        key = clip_key(url)
        out = clips / f"{key}.mp4"
        if key in seed_meta:
            shutil.copyfile(SEEDS / "clips" / f"{key}.mp4", out)
            s = dict(seed_meta[key])
            sources[key] = s
            ok += 1
            print(f"키트에서 복사 {key}.mp4  {s['seconds']}초  {s['account']} 조회 {s['views']} (평소의 {s['multiple']})")
            continue
        if "reddit.com" in url:
            bad.append((url, "레딧은 로그인 없이 못 받습니다"))
            print(f"실패 {url}\n  이유: 레딧은 로그인 없이 못 받습니다")
            continue
        import yt_dlp
        opts = {"outtmpl": str(clips / f"{key}.%(ext)s"), "format": "bv*+ba/b", "merge_output_format": "mp4",
                "quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True}
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(url, download=True)
        except Exception as e:  # noqa: BLE001
            bad.append((url, str(e)[:160]))
            print(f"실패 {url}\n  이유: {str(e)[:160]}")
            continue
        if not out.exists():
            got = sorted(clips.glob(f"{key}.*"))
            if got and got[0].suffix != ".mp4":
                got[0].rename(out)
        m = ffprobe_meta(out)
        sources[key] = {"url": url, "account": "@" + (info.get("channel") or info.get("uploader_id") or info.get("uploader") or ""),
                        "title": (info.get("description") or info.get("title") or "")[:120],
                        "views": info.get("view_count"), "likes": info.get("like_count"),
                        "measured": f"{dt.date.today():%m/%d}", "seconds": round(m["duration"], 1),
                        "sound": m["has_audio"]}
        ok += 1
        s = sources[key]
        print(f"받음 {key}.mp4  {s['seconds']}초  {s['account']} 조회 {s['views'] or '-'} 좋아요 {s['likes'] or '-'}")
    src_file.write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{ok}개 준비, {len(bad)}개 실패 → {clips}")
    if bad:
        print("실패한 링크는 빼고, 후보표에서 키트 영상이 '있음'인 것으로 바꾸세요.")


if __name__ == "__main__":
    main()
