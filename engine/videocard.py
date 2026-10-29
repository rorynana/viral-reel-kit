# -*- coding: utf-8 -*-
"""영상 카드뉴스 공용 렌더 모듈(1편 _make_videocard_aicover.py에서 일반화, 2026-09-21).

장 = 원본 영상 구간 + 하단 밴드. PIL이 글자 레이어(투명 PNG)를 만들고 ffmpeg가 원본 위에 합성한다.
- cover : 원본을 4:5로 채워 깔고 스크림 + 뱃지·헤드 3줄·서브·로고
- win43 : 4:3 원본을 위 1080x810, 아래 단색 밴드
- full  : 원본 crop 영역을 4:5로 채우고 하단 반투명 밴드
- statement / cta : 정지 PNG(기존 카드뉴스 엔진과 같은 그림)
규격: 1080x1350, 30fps, H.264 yuv420p, AAC 44.1k 160k, 전 장 원본 소리(afade 0.3/0.5).
"""
import os, subprocess
from PIL import Image, ImageDraw
from design import *

_orig_rr = ImageDraw.ImageDraw.rounded_rectangle
def _safe_rr(self, xy, radius=0, **kw):
    if len(xy) == 4: x0, y0, x1, y1 = xy
    else: (x0, y0), (x1, y1) = xy
    return _orig_rr(self, xy, radius=min(radius, max(0, (min(x1 - x0, y1 - y0) - 2) // 2)), **kw)
ImageDraw.ImageDraw.rounded_rectangle = _safe_rr

BAND_BG = (12, 12, 14)
NB = " "   # 붙임 공백
FPS = 30

def _pairs(lines):
    """json의 [[text, kw], ...] 줄 목록을 튜플 목록으로."""
    return [[(str(t), int(kw)) for t, kw in line] for line in lines]

def fit_size(d, lines, base, maxw, weight="xb"):
    s = base
    while s > 40:
        f = F(weight, s)
        if all(sum(tw(d, t, f) for t, _ in line) <= maxw for line in lines): return s
        s -= 2
    return s

def pill(d, x, y, text, f, fill=None, outline=None, fg=WHITE):
    padx, pady = 22, 11
    bw = tw(d, text, f) + padx * 2; bh = d.textbbox((0, 0), "가", font=f)[3] + pady * 2 + 6
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=bh // 2, fill=fill, outline=outline, width=2 if outline else 0)
    d.text((x + padx, y + pady - 2), text.replace(NB, " "), font=f, fill=fg)
    return bh

def band_block(c, y, s, dry=False):
    d = ImageDraw.Draw(c); y0 = y
    fp = F("bd", 30)
    h = d.textbbox((0, 0), "가", font=fp)[3] + 22 + 6
    if not dry: pill(d, M, y, s["pill"], fp, fill=ORANGE)
    y += h + 26
    hs = fit_size(d, [[(s["head"], 0)]], 64, W - 2 * M)
    if not dry: tshadow(c, M, y, s["head"], F("xb", hs), WHITE, blur=8); d = ImageDraw.Draw(c)
    y += int(hs * 1.25) + 14
    fb = F("sb", 36)
    lines = wrap_lines(d, W - 2 * M, s["body"], fb)
    if len(lines) > 2:
        raise SystemExit(f"{s['name']} 설명이 3줄 이상입니다(2줄 한도): {lines}")
    for ln in lines:
        if not dry: d.text((M, y), ln.replace(NB, " "), font=fb, fill=(228, 228, 232))
        y += 54
    y += 22
    ff = F("bd", 28)
    fh = d.textbbox((0, 0), "가", font=ff)[3] + 20 + 6
    if not dry: pill(d, M, y, s["foot"], ff, outline=(255, 255, 255, 150))
    y += fh
    return y - y0

WIN_GAP, BAND_BOTTOM = 36, 44

def win_h(s):
    """창 높이 = 1350에서 밴드와 위아래 여백을 뺀 나머지.

    창을 1080x810으로 고정해 두었더니 16:9 원본이 1080x608로 들어가 창 안에도 검정이 생기고,
    밴드가 810 아래 540px 안에서 가운데로 떠서 화면의 40~53%가 검게 비었다(9/22 2·3편 실측).
    창을 밴드 바로 위까지 키우고 밴드는 아래에 붙인다."""
    bh = band_block(Image.new("RGBA", (W, H), (0, 0, 0, 0)), 0, s, dry=True)
    return H - bh - WIN_GAP - BAND_BOTTOM

def layer_win43(s):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bh = band_block(c, 0, s, dry=True)
    band_block(c, H - BAND_BOTTOM - bh, s)
    return c

def layer_full(s):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bh = band_block(c, 0, s, dry=True)
    top = H - bh - 50
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for yy in range(top - 160, H):
        a = 215 if yy >= top - 40 else int(215 * (yy - (top - 160)) / 120)
        gd.line([(0, yy), (W, yy)], fill=BAND_BG + (max(0, a),))
    c.alpha_composite(g)
    band_block(c, top, s)
    return c

def layer_cover(s):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.alpha_composite(scrim(W, H, 0.28))
    d = ImageDraw.Draw(c)
    lines = _pairs(s["lines"]); size = fit_size(d, lines, 100, W - 2 * M)
    lh = int(size * 1.18)
    by = H - 160 - 46 - len(lines) * lh - 46 - 64
    bh = pill(d, M, by, s["badge"], F("bd", 30), fill=ORANGE)
    hy = by + bh + 30
    for line in lines:
        cx = M
        for t, kw in line:
            tshadow(c, cx, hy, t, F("xb", size), ORANGE if kw else WHITE)
            cx += tw(ImageDraw.Draw(c), t, F("xb", size))
        hy += lh
    tshadow(c, M, hy + 6, s["sub"], F("sb", 38), (235, 235, 238), blur=8)
    logo_at(c, M, H - 132, 48, white=True, handle=None)
    return c

def statement(lines, dark=True, sub=None, size=92):
    lines = _pairs(lines)
    bg = INK if dark else PAPER; fg = WHITE if dark else INK
    c = Image.new("RGBA", (W, H), bg + (255,)); grain(c, W, H, 8 if dark else 5); d = ImageDraw.Draw(c)
    size = fit_size(d, lines, size, W - 2 * M)
    lh = int(size * 1.38); total = len(lines) * lh + (70 if sub else 0); y = (H - total) // 2 - 20
    for line in lines:
        lw = sum(tw(d, t, F("xb", size)) for t, _ in line); xx = W // 2 - lw // 2
        for t, kw in line: d.text((xx, y), t, font=F("xb", size), fill=ORANGE if kw else fg); xx += tw(d, t, F("xb", size))
        y += lh
    if sub: ctext(d, W // 2, y + 24, sub, F("med", 34), (168, 168, 174) if dark else GRAYT)
    logo_at(c, W // 2, H - 128, 46, white=dark, center=True, handle=None); return c

def cta(s):
    """s = {"head": "줄1 / 줄2", "sub", "title", "items", "chip", "badge"}"""
    h1, _, h2 = [x.strip() for x in s["head"].partition("/")]
    sub, card_title, items, chip, badge = s["sub"], s["title"], list(s["items"]), s["chip"], s.get("badge", "소개")
    c = Image.new("RGBA", (W, H), ORANGE + (255,)); grain(c, W, H, 7); d = ImageDraw.Draw(c); CX = W // 2
    s0 = 84
    while max(tw(d, h1, F("xb", s0)), tw(d, h2, F("xb", s0))) > W - 120 and s0 > 56: s0 -= 2
    ctext(d, CX, 120 + (84 - s0), h1, F("xb", s0), WHITE); ctext(d, CX, 214, h2, F("xb", s0), INK)
    ctext(d, CX, 338, sub, F("med", 36), WHITE)
    cw, ch = 600, 624; cx0 = (W - cw) // 2; cy0 = 430; cshadow(c, [cx0, cy0, cx0 + cw, cy0 + ch], 32, blur=26, alpha=75)
    d = ImageDraw.Draw(c); d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=32, fill=WHITE)
    obadge(d, cx0 + 44, cy0 + 44, badge, WHITE, fill=ORANGE)
    tsz = 50; tf = F("xb", tsz); maxw = cw - 88
    while tw(d, card_title, tf) > maxw and tsz > 28: tsz -= 2; tf = F("xb", tsz)
    d.text((cx0 + 44, cy0 + 130 + (50 - tsz) // 2), card_title, font=tf, fill=INK)
    d.line([(cx0 + 44, cy0 + 208), (cx0 + cw - 44, cy0 + 208)], fill=(232, 230, 226), width=2)
    iy = cy0 + 248; imaxw = cw - 88 - 64
    for it in items:
        ex, ey = cx0 + 44, iy; d.ellipse([ex, ey, ex + 44, ey + 44], fill=ORANGE)
        cxm, cym = ex + 22, ey + 22
        d.line([(cxm - 10, cym + 1), (cxm - 3, cym + 8)], fill=WHITE, width=5); d.line([(cxm - 3, cym + 8), (cxm + 10, cym - 8)], fill=WHITE, width=5)
        isz = 36; itf = F("sb", isz)
        while tw(d, it, itf) > imaxw and isz > 26: isz -= 2; itf = F("sb", isz)
        d.text((ex + 64, iy + 2 + (36 - isz) // 2), it, font=itf, fill=(50, 50, 56)); iy += 66
    lw = int(LOGO.width * (34 / LOGO.height)); c.alpha_composite(LOGO.resize((lw, 34), Image.LANCZOS), (cx0 + 44, cy0 + ch - 56))
    d = ImageDraw.Draw(c); f = F("bd", 42); chw = tw(d, chip, f) + 72; chy = cy0 + ch + 44
    cshadow(c, [CX - chw // 2, chy, CX + chw // 2, chy + 96], 48, blur=14, alpha=70)
    d = ImageDraw.Draw(c); d.rounded_rectangle([CX - chw // 2, chy, CX + chw // 2, chy + 96], radius=48, fill=INK); ctext(d, CX, chy + 22, chip, f, WHITE)
    return c

def video_filter(s, src_w, src_h):
    if s["kind"] == "win43":
        # 비율은 지키되 창을 꽉 채운다. 남는 좌우는 fx(0~1) 자리에서 자른다(기본 가운데).
        # 시네마스코프(2.37:1)는 좌우 절반이 잘리지만 인물이 크게 들어와 오히려 낫다(9/22 목업 실측).
        wh = win_h(s)
        sw = max(W, int(round(src_w * wh / src_h / 2)) * 2)
        x = int((sw - W) * float(s.get("fx", 0.5)))
        return (f"[0:v]scale={sw}:{wh},crop={W}:{wh}:{x}:0,"
                f"setsar=1,pad=1080:1350:0:0:color=0x0C0C0E,fps={FPS}[b];[b][1:v]overlay=0:0[o]")
    if s["kind"] == "full":
        if s.get("crop"):
            cw, ch, cx, cy = s["crop"]
            return f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale=1080:1350,setsar=1,fps={FPS}[b];[b][1:v]overlay=0:0[o]"
        # crop이 없으면 가운데를 4:5로 채운다
        return f"[0:v]scale=1080:1350:force_original_aspect_ratio=increase,crop=1080:1350,setsar=1,fps={FPS}[b];[b][1:v]overlay=0:0[o]"
    # cover: 원본 비율을 세로 4% 더 키워 가장자리를 밀어내고 fx(0~1) 위치에서 4:5로 자른다
    sh = int(H * 1.04); sw = int(round(src_w * sh / src_h / 2)) * 2
    if sw < W:
        sw = W; sh = int(round(src_h * sw / src_w / 2)) * 2
    x = int((sw - W) * float(s.get("fx", 0.5))); y = max(0, (sh - H) // 2)
    return f"[0:v]scale={sw}:{sh},crop={W}:{H}:{x}:{y},setsar=1,fps={FPS}[b];[b][1:v]overlay=0:0[o]"

def _src_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)

def _has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return "audio" in out

def render_video(s, src_path, layer_png, out_mp4):
    t = float(s["t"]); w, h = _src_size(src_path)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(s["ss"]), "-t", str(t), "-i", src_path,
           "-loop", "1", "-t", str(t), "-i", layer_png]
    fc = video_filter(s, w, h)
    if _has_audio(src_path):
        fc += f";[0:a]afade=t=in:d=0.3,afade=t=out:st={max(0.0, t - 0.5)}:d=0.5[a]"
    else:   # 소리 없는 원본은 무음 트랙을 넣어 이어붙이기에서 오디오 스트림 수가 맞게 한다
        cmd += ["-f", "lavfi", "-t", str(t), "-i", "anullsrc=r=44100:cl=stereo"]
        fc += ";[2:a]anull[a]"
    cmd += ["-filter_complex", fc, "-map", "[o]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18", "-preset", "medium",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", "-t", str(t), out_mp4]
    subprocess.run(cmd, check=True)

LAYERS = {"cover": layer_cover, "win43": layer_win43, "full": layer_full}
