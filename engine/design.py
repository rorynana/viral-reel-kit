# -*- coding: utf-8 -*-
"""카드뉴스 PIL 디자인 엔진 — 공용 렌더 헬퍼·브랜드 상수.

_make_cardnews*.py 계열에 복붙돼 있던 저수준 헬퍼(smoothstep/grain/scrim/tshadow/
logo_at/wrap/wrap_lines/_white/obadge/fit/rich/toks 등)와 브랜드 상수·경로를 한곳에 모은다.
빌더는 `from design import *` 후 자기 덱에 맞는 렌더 함수(cover/inner_A/inner_B/
statement/cta 등)만 정의한다. 렌더 함수는 파일마다 달라서(예: fable5의 inner_task,
statement 서브·오토핏) 각 빌더에 그대로 남긴다.

주의:
- 결정론: grain()이 random을 쓰므로 산출물이 seed에 의존한다. 빌더에서 렌더 전에
  random.seed(...)를 호출해야 기존과 동일한 산출물이 나온다(이 모듈은 import 시 random을
  소비하지 않는다 — LOGO 합성만 하고 grain은 호출하지 않음).
- logo_at의 handle 기본값은 "". 로고 단독을 쓰는
  fable5 등은 호출부에서 handle=None을 명시한다.
"""
import os, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = str(Path(__file__).resolve().parent.parent)
# 리눅스(도커) 배포에선 KIT_FONT_DIR로 폰트 위치를 지정한다(deploy/fonts).
FONT_DIR = os.environ.get("KIT_FONT_DIR") or os.path.join(
    os.environ.get("LOCALAPPDATA", r"C:\Users\user\AppData\Local"),
    "Microsoft", "Windows", "Fonts")
# 사용자 폰트 폴더에 Paperlogy가 없는 PC(새 노트북 등)는 리포의 deploy/fonts를 쓴다.
if not os.environ.get("KIT_FONT_DIR") and not os.path.exists(os.path.join(FONT_DIR, "Paperlogy-5Medium.ttf")):
    FONT_DIR = os.path.join(ROOT, "deploy", "fonts")
FD = FONT_DIR  # 하위 호환 별칭

# ---- 클라이언트 테마 ----
# KIT_THEME=테마 폴더(theme.json이 있는 곳). 앱이 클라이언트별로 넘긴다.
# 없으면 아래 기본값 그대로. 색·폰트·로고·핸들·CTA 문구만 바뀌고 다섯 틀의 레이아웃은 같다.
# 형식은 assets/themes/README.md 참고.
THEME_DIR = os.environ.get("KIT_THEME") or ""
THEME = {}
if THEME_DIR:
    import json
    with open(os.path.join(THEME_DIR, "theme.json"), encoding="utf-8") as _fh:
        THEME = json.load(_fh)
def _theme_path(p):
    if not p: return None
    return p if os.path.isabs(p) else os.path.join(THEME_DIR, p)
def _hex(s, default):
    if not s: return default
    s = str(s).strip().lstrip("#")
    if len(s) == 3: s = "".join(ch * 2 for ch in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

# ---- 브랜드 상수 (테마가 있으면 그 색) ----
_C = THEME.get("colors") or {}
ORANGE=_hex(_C.get("accent"),(255,127,0)); INK=_hex(_C.get("ink"),(24,24,28)); WHITE=(255,255,255); PAPER=_hex(_C.get("paper"),(250,249,246))
GRAYT=_hex(_C.get("gray_text"),(96,96,102)); ORTINT=_hex(_C.get("accent_tint"),(255,243,231)); GRAYCARD=_hex(_C.get("gray_card"),(240,239,236))
W,H=1080,1350; M=90
HANDLE = THEME.get("handle", "")
_CTA = THEME.get("cta") or {}
CTA_TITLE = _CTA.get("title") or "이 계정에서 보는 것"
CTA_ITEMS = list(_CTA.get("items") or ["AI 콘텐츠 기획·제작", "100만 건 바이럴 데이터 분석", "AEO · 채널 운영"])
CTA_CHIP = _CTA.get("chip") or "문의는 프로필 링크 또는 DM으로"

# ---- 폰트/텍스트 ----
_FONT_KEYS = ("med", "sb", "bd", "xb", "bk")
_FONT_FILES = {"med":"Paperlogy-5Medium.ttf","sb":"Paperlogy-6SemiBold.ttf","bd":"Paperlogy-7Bold.ttf","xb":"Paperlogy-8ExtraBold.ttf","bk":"Paperlogy-9Black.ttf"}
_TF = THEME.get("fonts") or {}
if any(_TF.get(k) for k in _FONT_KEYS):
    FD = FONT_DIR = _theme_path(_TF.get("dir") or "fonts")
    _given = {k: _TF[k] for k in _FONT_KEYS if _TF.get(k)}
    # 없는 두께는 가장 가까운 두께 파일로. 제목용·본문용 둘만 줘도 돌아간다.
    _FONT_FILES = {k: _given.get(k) or _given[min(_given, key=lambda g: abs(_FONT_KEYS.index(g) - _FONT_KEYS.index(k)))]
                   for k in _FONT_KEYS}
def F(w,s):
    return ImageFont.truetype(os.path.join(FD,_FONT_FILES[w]),s)
def tw(d,s,f): b=d.textbbox((0,0),s,font=f); return b[2]-b[0]
def ctext(d,cx,y,s,f,fill): d.text((cx-tw(d,s,f)//2,y),s,font=f,fill=fill)

# ---- 로고 (import 시 1회 합성) ----
def _load(path=None):
    """로고를 RGBA로. 알파가 없는 파일(jpg)은 흰 배경을 투명으로 뺀다."""
    src=Image.open(path or os.path.join(ROOT,"logo.png")); key="A" not in src.getbands()
    lg=src.convert("RGBA"); px=lg.load()
    if key:
        for y in range(lg.height):
            for x in range(lg.width):
                r,g,b,a=px[x,y]
                if r>238 and g>238 and b>238: px[x,y]=(255,255,255,0)
    return lg.crop(lg.getbbox())
LOGO=_load(_theme_path(THEME.get("logo")))
def _white(src):
    im=src.copy(); px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=px[x,y]
            if a==0: continue
            px[x,y]=(255,127,0,a) if (r>170 and 40<g<190 and b<110) else (255,255,255,a)
    return im
def _all_white(src):
    im=src.copy(); px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            a=px[x,y][3]
            if a: px[x,y]=(255,255,255,a)
    return im
# 어두운 배경용 로고: 테마가 따로 주면 그 파일, 테마 로고만 있으면 전부 흰색, 기본 로고는 주황만 남기고 흰색
if THEME.get("logo_dark"): LOGO_W=_load(_theme_path(THEME["logo_dark"]))
elif THEME.get("logo"): LOGO_W=_all_white(LOGO)
else: LOGO_W=_white(LOGO)
def logo_at(c,x,y,h,white=False,handle=HANDLE,center=False):
    src=LOGO_W if white else LOGO; w=int(src.width*(h/src.height))
    if center: x=x-(w+(22+tw(ImageDraw.Draw(c),handle,F("med",28)) if handle else 0))//2
    c.alpha_composite(src.resize((w,h),Image.LANCZOS),(x,y))
    if handle: ImageDraw.Draw(c).text((x+w+22,y+h-36),handle,font=F("med",28),fill=(228,228,231) if white else (150,150,155))

# ---- 이미지/렌더 헬퍼 ----
def fit(path,W,H):
    im=Image.open(path).convert("RGB"); s=max(W/im.width,H/im.height)
    im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
    l=(im.width-W)//2; t=(im.height-H)//2; return im.crop((l,t,l+W,t+H))
def smoothstep(u): u=max(0.0,min(1.0,u)); return u*u*(3-2*u)
def grain(c,cw,ch,a=8):
    n=Image.new("L",(cw//2,ch//2)); px=n.load()
    for y in range(ch//2):
        for x in range(cw//2): px[x,y]=random.randint(100,156)
    n=n.resize((cw,ch)); c.alpha_composite(Image.merge("RGBA",(n,n,n,Image.new("L",(cw,ch),a))),(0,0))
def scrim(cw,ch,start=0.30):
    g=Image.new("L",(1,ch),0); px=g.load()
    for y in range(ch): px[0,y]=int(238*smoothstep(max(0.0,(y/ch-start)/(1-start))))
    g=g.resize((cw,ch)); blk=Image.new("RGBA",(cw,ch),(6,6,10,0)); blk.putalpha(g); return blk
def tshadow(c,x,y,text,font,fill,off=(3,6),blur=10,shcol=(0,0,0,150)):
    l=Image.new("RGBA",c.size,(0,0,0,0)); ImageDraw.Draw(l).text((x+off[0],y+off[1]),text,font=font,fill=shcol)
    c.alpha_composite(l.filter(ImageFilter.GaussianBlur(blur))); ImageDraw.Draw(c).text((x,y),text,font=font,fill=fill)
def cshadow(c,box,rad,blur=18,alpha=55,off=(0,10)):
    sh=Image.new("RGBA",c.size,(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([box[0]+off[0],box[1]+off[1],box[2]+off[0],box[3]+off[1]],radius=rad,fill=(0,0,0,alpha))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
def obadge(d,x,y,text,col,fill=None):
    f=F("bd",30); padx,pady=22,11; bw=tw(d,text,f)+padx*2; bh=d.textbbox((0,0),"가",font=f)[3]+pady*2+6
    if fill: d.rounded_rectangle([x,y,x+bw,y+bh],radius=bh//2,fill=fill); d.text((x+padx,y+pady-2),text,font=f,fill=col)
    else: d.rounded_rectangle([x,y,x+bw,y+bh],radius=bh//2,outline=col,width=3); d.text((x+padx,y+pady-2),text,font=f,fill=col)
    return bh
def wrap_lines(d,maxw,text,f):
    # 본문 안 줄바꿈(\n)은 강제 줄넘김. 공백으로만 자르면 '답했습니다.\n교과'가 한 단어로 남아
    # PIL이 다음 줄에 겹쳐 그린다(9/17 카드 2번 사고).
    lines=[]
    for part in str(text).split("\n"):
        line=""
        for w in part.split(" "):
            if tw(d,(line+" "+w).strip(),f)>maxw and line: lines.append(line); line=w
            else: line=(line+" "+w).strip()
        lines.append(line)
    return lines
def wrap(d,x,y,maxw,text,f,fill,lh):
    for ln in wrap_lines(d,maxw,text,f): d.text((x,y),ln,font=f,fill=fill); y+=lh
    return y
def rich(d,x,y,maxw,tokens,size,base,lh):
    med=F("med",size); bd=F("bd",size); cy=y; cx=x
    for word,b in tokens:
        if word=="\n":   # 강제 줄넘김(toks가 본문 줄바꿈을 따로 뗀 토큰)
            if cx!=x: cx=x; cy+=lh
            continue
        glue=word.endswith("⁠"); word=word.rstrip("⁠")
        f=bd if b else med; ww=tw(d,word if glue else word+" ",f)
        if cx+ww>x+maxw: cx=x; cy+=lh
        d.text((cx,cy),word,font=f,fill=INK if b else base); cx+=ww
    return cy
GLUE="⁠"   # 토큰 끝 표식 = 다음 토큰과 띄우지 않음(rich만 읽고 지운다)
def toks(s):
    # 별표 경계가 공백 없이 붙어 있으면('*진정성*'이, '*…*') 앞 토큰에 GLUE를 달아 붙여 그린다.
    # 전에는 경계마다 공백이 생겨 "이유는 ' 진정성이 … 않아서 '였습니다"로 나갔다(9/17 카드 4번).
    out=[]; prev=""
    for i,seg in enumerate(s.split("*")):
        b=(i%2==1)
        ws=[w for w in seg.replace("\n"," \n ").split(" ") if w!=""]
        if out and ws and prev and prev[-1] not in " \n" and seg[0] not in " \n" and out[-1][0]!="\n":
            out[-1]=(out[-1][0]+GLUE,out[-1][1])
        out+=[(w,b) for w in ws]
        if seg: prev=seg
    return out
def arrow_btn(c,ax,ay,ar=44,col=INK):
    d=ImageDraw.Draw(c); d.ellipse([ax-ar,ay-ar,ax+ar,ay+ar],outline=col,width=4)
    d.line([(ax-8,ay-11),(ax+9,ay)],fill=col,width=5); d.line([(ax+9,ay),(ax-8,ay+11)],fill=col,width=5)

__all__=["ROOT","FONT_DIR","FD","ORANGE","INK","WHITE","PAPER","GRAYT","ORTINT","GRAYCARD",
         "THEME","THEME_DIR","HANDLE","CTA_TITLE","CTA_ITEMS","CTA_CHIP",
         "W","H","M","F","tw","ctext","LOGO","LOGO_W","logo_at","fit","smoothstep","grain",
         "scrim","tshadow","cshadow","obadge","wrap","wrap_lines","rich","toks","arrow_btn"]
