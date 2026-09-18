import json, html, os, io, base64
LITE = os.environ.get('LITE') == '1'

D = json.load(open('meta/ui_data.json'))
S = D['summary']
ra, shop, imgs, intel = D['ra'], D['shop'], D['img'], D['intel']
loc = D.get('loc', [])
merl = D.get('merl', [])
ms = D.get('merl_stats', {})
openc = D.get('open', [])
cls = S['retail_action']['cls']
if LITE:
    from PIL import Image
    def _shrink(u, w=300, q=52):
        try:
            raw = base64.b64decode(u.split(',', 1)[1])
            im = Image.open(io.BytesIO(raw)).convert('RGB')
            if im.width > w:
                im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
            b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True)
            return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
        except Exception:
            return u
    loc[:] = [_r for _r in loc if _r.get('img')]      # video-only entries have no still
    merl[:] = [_r for _r in merl if _r.get('img')]
    for _grp in (ra, shop, imgs, intel, loc, merl):
        for _r in _grp:
            _r.pop('vid', None)
            if _r.get('img'):
                _r['img'] = _shrink(_r['img'])

H = S.get('header', {})

CSS = """
:root{
  color-scheme: light;
  --bg:#eef1f5; --surface:#ffffff; --surface-2:#e5eaf0; --sunk:#f6f8fa;
  --ink:#0f1418; --ink-2:#48545f; --ink-3:#78848f; --line:#d5dde5;
  --accent:#2a78d6; --accent-2:#184f95; --accent-soft:#cde2fb;
  --good:#0ca30c; --warn:#fab219; --serious:#ec835a; --crit:#d03b3b;
  --shadow:0 1px 2px rgba(15,25,40,.06),0 8px 24px rgba(15,25,40,.06);
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --bg:#0d1115; --surface:#161b21; --surface-2:#1e262d; --sunk:#11161b;
    --ink:#e9eef3; --ink-2:#a5b1bc; --ink-3:#74808c; --line:#28323a;
    --accent:#3987e5; --accent-2:#86b6ef; --accent-soft:#184f95;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.34);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#0d1115; --surface:#161b21; --surface-2:#1e262d; --sunk:#11161b;
  --ink:#e9eef3; --ink-2:#a5b1bc; --ink-3:#74808c; --line:#28323a;
  --accent:#3987e5; --accent-2:#86b6ef; --accent-soft:#184f95;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.34);
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:var(--sans); font-size:15px; line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1140px;margin:0 auto;padding:40px 24px 96px}
h1,h2,h3{text-wrap:balance;margin:0}
h1{font-size:clamp(28px,4.2vw,42px);line-height:1.12;letter-spacing:-.025em;font-weight:660}
h2{font-size:23px;letter-spacing:-.017em;font-weight:640}
h3{font-size:15px;letter-spacing:-.005em;font-weight:640}
p{margin:0}
a{color:var(--accent)}
.eyebrow{
  font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);font-weight:500;
}
.lede{font-size:17px;color:var(--ink-2);max-width:66ch;line-height:1.62}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}

header.top{display:flex;flex-direction:column;gap:14px;padding-bottom:28px;border-bottom:1px solid var(--line)}
.topmeta{display:flex;flex-wrap:wrap;gap:8px 22px;font-family:var(--mono);font-size:12.5px;color:var(--ink-3)}
.topmeta b{color:var(--ink-2);font-weight:600}

section{margin-top:52px;scroll-margin-top:20px}
.shead{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:6px}
.sdesc{color:var(--ink-2);max-width:72ch;margin-top:8px}

/* verdict cards */
.verdicts{display:grid;grid-template-columns:repeat(auto-fit,minmax(238px,1fr));gap:12px;margin-top:22px}
.vcard{
  background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 16px 14px;
  box-shadow:var(--shadow);display:flex;flex-direction:column;gap:9px;position:relative;overflow:hidden;
}
.vcard::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--cstripe,var(--line))}
.vcard h3{font-size:14.5px}
.vcard .num{font-family:var(--mono);font-size:25px;font-weight:600;letter-spacing:-.02em;line-height:1}
.vcard .sub{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);line-height:1.5}
.chip{
  display:inline-flex;align-items:center;gap:6px;align-self:flex-start;
  font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;
  font-weight:600;padding:3px 8px;border-radius:99px;border:1px solid;
}
.chip .dot{width:6px;height:6px;border-radius:99px;background:currentColor;flex:none}
.c-good{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,transparent);background:color-mix(in srgb,var(--good) 10%,transparent)}
.c-warn{color:var(--serious);border-color:color-mix(in srgb,var(--serious) 44%,transparent);background:color-mix(in srgb,var(--serious) 12%,transparent)}
.c-crit{color:var(--crit);border-color:color-mix(in srgb,var(--crit) 42%,transparent);background:color-mix(in srgb,var(--crit) 11%,transparent)}

/* callout */
.callout{
  display:flex;gap:13px;background:var(--surface);border:1px solid var(--line);
  border-left:3px solid var(--cstripe,var(--crit));border-radius:8px;padding:14px 16px;margin-top:18px;
}
.callout .ico{font-family:var(--mono);font-weight:700;color:var(--cstripe,var(--crit));flex:none;font-size:13px;padding-top:1px}
.callout p{font-size:14.2px;color:var(--ink-2)}
.callout b{color:var(--ink);font-weight:620}

/* stat row */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-top:20px}
.stat{background:var(--surface);padding:13px 14px;display:flex;flex-direction:column;gap:3px}
.stat .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3)}
.stat .v{font-family:var(--mono);font-size:19px;font-weight:600;letter-spacing:-.02em}
.stat .n{font-size:11.5px;color:var(--ink-3);line-height:1.4}

/* charts */
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px 20px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px;align-items:start}
@media(max-width:860px){.grid2{grid-template-columns:1fr}}
.ctitle{font-size:14px;font-weight:620;letter-spacing:-.005em}
.csub{font-size:12.5px;color:var(--ink-3);margin-top:3px;line-height:1.5}
.bars{margin-top:15px;display:flex;flex-direction:column;gap:9px}
.brow{display:grid;grid-template-columns:96px 1fr auto;align-items:center;gap:10px}
.blab{font-family:var(--mono);font-size:12px;color:var(--ink-2);text-align:right;white-space:nowrap}
.btrack{background:var(--sunk);border-radius:3px;height:16px;position:relative;overflow:hidden}
.bfill{height:100%;background:var(--accent);border-radius:0 4px 4px 0;min-width:3px;transition:filter .12s}
.brow:hover .bfill{filter:brightness(1.12)}
.bval{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink-2);
  display:grid;grid-template-columns:auto 60px;gap:10px}
.bval .p{text-align:right;font-weight:600;color:var(--ink)}
.bval .s{text-align:left;color:var(--ink-3);font-size:11.5px;white-space:nowrap}

/* filter + grid */
.filters{display:flex;flex-wrap:wrap;gap:7px;margin:20px 0 14px;align-items:center}
.fbtn{
  font-family:var(--mono);font-size:12px;padding:5px 11px;border-radius:99px;cursor:pointer;
  border:1px solid var(--line);background:var(--surface);color:var(--ink-2);
}
.fbtn[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.fbtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(252px,1fr));gap:12px;align-items:start}
.card{
  background:var(--surface);border:1px solid var(--line);border-radius:9px;overflow:hidden;
  box-shadow:var(--shadow);cursor:zoom-in;display:flex;flex-direction:column;
}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card img{width:100%;display:block;background:#0c0f12}
.thumb{position:relative;line-height:0}
.play{
  position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  width:38px;height:38px;border-radius:99px;display:grid;place-items:center;
  background:rgba(8,12,16,.62);border:1.5px solid rgba(255,255,255,.72);
  color:#fff;font-size:13px;padding-left:3px;
  backdrop-filter:blur(2px);transition:transform .13s,background .13s;
}
.card:hover .play{transform:translate(-50%,-50%) scale(1.09);background:rgba(8,12,16,.78)}
.card:has(.play){cursor:pointer}
.cmeta{padding:8px 10px;display:flex;align-items:center;justify-content:space-between;gap:8px;
  font-family:var(--mono);font-size:11px;color:var(--ink-3)}
.tag{font-family:var(--mono);font-size:10px;letter-spacing:.07em;text-transform:uppercase;font-weight:650;
  padding:2px 7px;border-radius:99px;border:1px solid}
.t-take{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 42%,transparent);background:color-mix(in srgb,var(--accent) 10%,transparent)}
.t-put{color:var(--good);border-color:color-mix(in srgb,var(--good) 42%,transparent);background:color-mix(in srgb,var(--good) 10%,transparent)}
.t-touch{color:var(--serious);border-color:color-mix(in srgb,var(--serious) 46%,transparent);background:color-mix(in srgb,var(--serious) 12%,transparent)}
.t-none{color:var(--ink-3);border-color:var(--line);background:var(--sunk)}
.t-dup{color:var(--crit);border-color:color-mix(in srgb,var(--crit) 42%,transparent);background:color-mix(in srgb,var(--crit) 10%,transparent)}

/* legend */
.legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:16px;padding:11px 14px;
  background:var(--sunk);border:1px solid var(--line);border-radius:8px;
  font-family:var(--mono);font-size:12px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:7px}
.mk{width:12px;height:12px;border-radius:99px;border:2.5px solid;flex:none}

/* table */
.twrap{overflow-x:auto;margin-top:18px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:620px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);font-weight:600;background:var(--sunk)}
tr:last-child td{border-bottom:none}
td.mono{font-family:var(--mono);font-size:12.5px;white-space:nowrap;color:var(--ink-2)}

pre{
  margin:16px 0 0;background:var(--sunk);border:1px solid var(--line);border-radius:8px;
  padding:14px 16px;overflow-x:auto;font-family:var(--mono);font-size:12.5px;line-height:1.62;color:var(--ink-2)
}
pre b{color:var(--accent);font-weight:600}
.cap{font-size:12.5px;color:var(--ink-3);line-height:1.55;padding:9px 11px;border-top:1px solid var(--line)}

/* picker */
.picker{display:grid;grid-template-columns:186px 1fr;gap:14px;margin-top:20px;align-items:start}
@media(max-width:820px){.picker{grid-template-columns:1fr}}
.plist{display:flex;flex-direction:column;gap:3px;max-height:560px;overflow-y:auto;
  background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:8px}
.pgrp{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-3);padding:9px 6px 3px}
.mbtn{font-family:var(--mono);font-size:11.5px;text-align:left;padding:5px 9px;border-radius:6px;border:1px solid transparent;background:transparent;color:var(--ink-2);cursor:pointer}
.mbtn:hover{background:var(--sunk)}
.mbtn[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:650}
.mbtn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.pbtn{font-family:var(--mono);font-size:11.5px;text-align:left;padding:5px 9px;border-radius:6px;
  border:1px solid transparent;background:transparent;color:var(--ink-2);cursor:pointer}
.pbtn:hover{background:var(--sunk)}
.pbtn[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:650}
.pbtn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.pstage{display:flex;flex-direction:column;gap:9px;min-width:0}
[hidden]{display:none!important}
.pstage video,.pstage img{width:100%;border-radius:9px;border:1px solid var(--line);background:#0a0d10;display:block}
.lbtn{font-family:var(--mono);font-size:11.5px;text-align:left;padding:5px 9px;border-radius:6px;border:1px solid transparent;background:transparent;color:var(--ink-2);cursor:pointer}
.lbtn:hover{background:var(--sunk)}
.lbtn[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:650}
.lbtn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.pmeta{font-size:12px;color:var(--ink-3);background:var(--surface);border:1px solid var(--line);
  border-radius:8px;padding:9px 12px;line-height:1.7}
.pmeta b{color:var(--ink)}
.pcls{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap}
.pcls i{width:9px;height:9px;border-radius:2px;display:inline-block;font-style:normal}

/* lightbox */
.lb{position:fixed;inset:0;background:rgba(6,9,12,.86);display:none;align-items:center;justify-content:center;
  z-index:50;padding:28px;backdrop-filter:blur(3px)}
.lb[open]{display:flex}
.lbstage{display:flex;align-items:center;justify-content:center;max-width:100%}
.lb img,.lb video{max-width:100%;max-height:80vh;border-radius:8px;box-shadow:0 20px 60px rgba(0,0,0,.5);
  background:#0a0d10;image-rendering:auto}
.lb video{width:min(920px,92vw)}
.lb .cx{position:absolute;top:18px;right:22px;font-family:var(--mono);font-size:13px;color:#dfe6ed;
  background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.22);border-radius:7px;padding:6px 12px;cursor:pointer}
.lbcap{position:absolute;bottom:22px;left:0;right:0;text-align:center;font-family:var(--mono);font-size:12.5px;color:#c3ccd5}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

def chip(kind, text):
    k = {'good': 'c-good', 'warn': 'c-warn', 'crit': 'c-crit'}[kind]
    return f'<span class="chip {k}"><span class="dot"></span>{text}</span>'


def vcard(stripe, title, num, sub, ch):
    return f"""<div class="vcard" style="--cstripe:{stripe}">
      {ch}<h3>{title}</h3><div class="num">{num}</div><div class="sub">{sub}</div></div>"""


def bars(rows, maxv):
    """rows: (label, value, primary readout, secondary readout or '')"""
    out = []
    for lab, val, prim, sec in rows:
        w = max(0.6, 100 * val / maxv)
        out.append(f"""<div class="brow"><div class="blab">{lab}</div>
        <div class="btrack"><div class="bfill" style="width:{w:.2f}%"></div></div>
        <div class="bval"><span class="p">{prim}</span><span class="s">{sec}</span></div></div>""")
    return '<div class="bars">' + ''.join(out) + '</div>'


# ---------- gallery cards ----------
def thumb(src, alt, has_video):
    badge = '<span class="play" aria-hidden="true">&#9654;</span>' if has_video else ''
    return (f'<div class="thumb"><img loading="lazy" src="{src}" alt="{alt}">{badge}</div>')


ra_cards = []
for r in sorted(ra, key=lambda x: {'take': 0, 'put': 1, 'touch': 2, 'no-action': 3}[x['label']]):
    lab = r['label']
    t = {'take': 't-take', 'put': 't-put', 'touch': 't-touch', 'no-action': 't-none'}[lab]
    span = f"{r['start']:.2f}–{r['end']:.2f}" if r['start'] is not None else 'no action'
    v = r.get('vid', '')
    ra_cards.append(
        f'<figure class="card" data-lab="{lab}" tabindex="0" data-src="{r["img"]}" '
        f'data-vid="{v}" '
        f'data-cap="sample {r["sid"]} &middot; {lab} &middot; left camera 1 / right camera 2 &middot; '
        f'red marks the labelled contact point, the border lights up over the action">'
        f'{thumb(r["img"], f"RetailAction sample {r['sid']}, two synchronized ceiling views, {lab}", bool(v))}'
        f'<figcaption class="cmeta"><span>{r["sid"]}</span>'
        f'<span class="tag {t}">{lab}</span></figcaption></figure>')

shop_cards = []
for r in shop:
    d = '<span class="tag t-dup">dup</span>' if r['dup'] else ''
    v = r.get('vid', '')
    cap = (f'{r["name"]} &middot; first 9 seconds of the clip' if v
           else f'{r["name"]} &middot; frames at 20% / 50% / 80% of the clip')
    shop_cards.append(
        f'<figure class="card" tabindex="0" data-src="{r["img"]}" data-vid="{v}" data-cap="{cap}">'
        f'{thumb(r["img"], f"Three frames from shoplifting clip {r['name']}", bool(v))}'
        f'<figcaption class="cmeta"><span>{html.escape(r["name"])[:22]}</span>{d}</figcaption></figure>')

img_cards = []
for r in imgs:
    wild = r['name'].upper().startswith('IMG_')
    tag = ('<span class="tag t-dup">apparel</span>' if wild
           else '<span class="tag t-touch">NC-ND</span>')
    what = 'Clothing shop photograph' if wild else 'Grocery shelf photograph'
    img_cards.append(
        f'<figure class="card" tabindex="0" data-src="{r["img"]}" '
        f'data-cap="{html.escape(r["name"])} &middot; '
        f'{"retail-in-the-wild (apparel, Apache-2.0)" if wild else "UniDataPro grocery-shelves (CC BY-NC-ND)"}">'
        f'<img loading="lazy" src="{r["img"]}" alt="{what} {html.escape(r["name"])}">'
        f'<figcaption class="cmeta"><span>{html.escape(r["name"])}</span>{tag}</figcaption></figure>')

intel_cards = []
for r in intel:
    cap = html.escape(r['cap'][:210]) + ('…' if len(r['cap']) > 210 else '')
    intel_cards.append(
        f'<figure class="card" tabindex="0" data-src="{r["img"]}" data-cap="{html.escape(r["name"])}">'
        f'<img loading="lazy" src="{r["img"]}" alt="Frame from Intel retail clip {r["name"]}">'
        f'<div class="cap">{cap}</div></figure>')

joint_rows = [('top_of_head', 99, '99%', ''), ('right_hand', 85, '85%', ''), ('left_hand', 85, '85%', ''),
              ('right_wrist', 84, '84%', ''), ('left_wrist', 84, '84%', ''),
              ('nose', 45, '45%', 'face blurred'), ('right_eye', 29, '29%', 'face blurred')]

cls_rows = [('take', cls['take'], f"{cls['take']:,}", '97.7%'),
            ('put', cls['put'], f"{cls['put']:,}", '2.0%'),
            ('touch', cls['touch'], f"{cls['touch']:,}", '0.3%')]

HTML = f"""<title>CCTV grocery data — round 2, MERL Shopping added</title>
<style>{CSS}</style>
<div class="wrap">

<header class="top">
  <div class="eyebrow">Data collection · round 2 · MERL Shopping added</div>
  <h1>Store CCTV footage of goods being picked up and put down</h1>
  <p class="lede"><b>Round 2.</b> Five sources now, aimed at one thing: video where a product visibly
  moves — off a shelf, into a hand, into a basket. The newest and best is <b>MERL Shopping</b>, added
  after the first haul came back weak; it leads the page below. Everything here is on disk and playable.</p>
  <div class="topmeta">
    <span><b>{H.get('total_gb', S['total_gb'])} GB</b> on disk</span>
    <span><b>{H.get('files', 0):,}</b> video files</span>
    <span><b>{H.get('actions', 0):,}</b> labelled actions</span>
    <span><b>~{H.get('hours', 0)} h</b> of footage</span>
    <span class="mono">~/cctv-grocery-data</span>
  </div>
</header>

<section>
  <div class="shead"><h2>What each source is worth</h2></div>
  <p class="sdesc">My read after inspecting the actual frames, not the dataset descriptions. Detail and
  evidence for each verdict is in the sections below.</p>
  <div class="verdicts">
    {vcard('var(--good)', 'MERL Shopping', f"{ms.get('videos',0)}", 'continuous videos, 30 fps<br>5,377 balanced actions<br>41 people, subject-split', chip('good', 'New &mdash; best balance'))}
    {vcard('var(--good)', 'RetailAction', f"{S['retail_action']['samples']:,}", 'clips, dual camera<br>take / put / touch labels<br>10 US convenience stores', chip('good', 'Build on this'))}
    {vcard('var(--crit)', 'Shoplifting CCTV', f"{S['shoplifting']['clips']:,}", 'clips, no labels<br>one camera, one day<br>no licence declared', chip('crit', 'Delete it'))}
    {vcard('var(--serious)', 'Intel retail', '16', 'clips, 1080p<br>text summaries only<br>CC BY-SA share-alike', chip('warn', 'Too small'))}
    {vcard('var(--crit)', 'Shelf stills', '34', 'photos, no movement<br>15 grocery, non-commercial<br>19 are clothing shops', chip('crit', 'Drop both'))}
  </div>
  <div class="callout" style="--cstripe:var(--good)">
    <div class="ico">→</div>
    <p><b>Short version.</b> RetailAction is the real find and it is the only source here that matches
    what you are building — ceiling cameras, real stores, and a labelled point on the product at the
    moment a hand reaches it. The shoplifting set looked promising at 855 clips but is one camera in
    one shop on one day, with no labels and no licence &mdash; I would delete it. Start with
    RetailAction, treat the rest as spare parts, and read the licence table before any of this reaches
    something you sell: RetailAction is free only up to $10,000 of revenue.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>MERL Shopping — the one I should have pulled first</h2>{chip('good', 'New')}</div>
  <p class="sdesc">You were right that the first haul was weak, so I went back out. This is the best thing
  I found, from Mitsubishi Electric Research Labs: <b>106 continuous videos</b>, about two minutes each,
  from a fixed overhead camera in a grocery aisle, with <b>5,377 labelled actions</b> across five classes
  that are precisely your problem — <span class="mono">Reach To Shelf</span>,
  <span class="mono">Retract From Shelf</span>, <span class="mono">Hand In Shelf</span>,
  <span class="mono">Inspect Product</span>, <span class="mono">Inspect Shelf</span>. It is on disk.</p>

  <div class="stats">
    <div class="stat"><div class="k">Videos</div><div class="v">106</div><div class="n">~2 min each, continuous</div></div>
    <div class="stat"><div class="k">Footage</div><div class="v">4.0 h</div><div class="n">not 5-second crops</div></div>
    <div class="stat"><div class="k">Frame</div><div class="v">920&times;680</div><div class="n">30 fps</div></div>
    <div class="stat"><div class="k">Actions</div><div class="v">5,377</div><div class="n">frame-accurate spans</div></div>
    <div class="stat"><div class="k">People</div><div class="v">41</div><div class="n">splits are subject-disjoint</div></div>
    <div class="stat"><div class="k">Size</div><div class="v">1.8 GB</div><div class="n">videos + labels</div></div>
  </div>

  <div class="callout" style="--cstripe:var(--good)">
    <div class="ico">&rarr;</div>
    <p><b>Why it beats RetailAction on the things that were hurting you.</b> The class balance is real
    — 32/30/15/13/10% across five classes, against RetailAction&rsquo;s 97.7% <span class="mono">take</span>
    which left <span class="mono">touch</span> with eight examples in the entire split. It is
    <b>30 fps continuous video</b>, not 6 fps motion-sampled crops, so you can track a hand
    through a reach rather than classifying a stack of stills. The train/val/test split is
    <b>by person</b>, so you cannot leak a subject across it — the honest-split problem I flagged
    on RetailAction is already solved here. And there is a published baseline to measure against:
    81.9 mAP.</p>
  </div>

  <div class="picker">
    <div class="plist" role="group" aria-label="Choose a MERL clip">
      {''.join(f'<button class="mbtn" data-i="{i}" aria-pressed="{str(i == 0).lower()}">subject {v["subject"]} &middot; {v["name"]}</button>' for i, v in enumerate(merl))}
    </div>
    <div class="pstage">
      <video id="merlv" controls autoplay loop muted playsinline></video>
      <div class="pmeta mono" id="merlm"></div>
    </div>
  </div>
  <p class="sdesc" style="margin-top:14px">Eight different people, spread across the subject range. Each
  clip is cut around a labelled <span class="mono">Inspect Product</span> — watch the hand go into
  the shelf, come out with something, and hold it up. That is the event you are trying to detect, at a
  frame rate where you can actually see it happen.</p>

  <div class="grid2">
    <div class="panel">
      <div class="ctitle">MERL: five classes, usably balanced</div>
      <div class="csub">Labelled action instances. Every class has hundreds of examples.</div>
      {bars([(k, v, f'{v:,}', '') for k, v in ms.get('actions', {}).items()], max(ms.get('actions', {1:1}).values()))}
    </div>
    <div class="panel">
      <div class="ctitle">RetailAction: one class, effectively</div>
      <div class="csub">The same chart for the dataset I brought you first. This is the contrast that
      matters — two of its three classes are untrainable.</div>
      {bars([('take', cls['take'], f"{cls['take']:,}", '97.7%'), ('put', cls['put'], f"{cls['put']:,}", '2.0%'), ('touch', cls['touch'], f"{cls['touch']:,}", '0.3%')], cls['take'])}
    </div>
  </div>

  <div class="callout">
    <div class="ico">!</div>
    <p><b>It does not fix everything, and you should know what it is.</b> It is <b>one fixed camera on
    one staged shelf</b> — every video has identical framing. That is the same scene-diversity problem
    that killed the shoplifting set, so a model trained only on this learns one aisle. The people are
    also <b>participants, not real customers</b>: they were asked to shop, so the behaviour is cleaner
    and more deliberate than a real store. And it is from 2016, so the footage is dated. Treat it as the
    place to learn <i>the motion</i>, with RetailAction&rsquo;s 10 real stores as the thing you
    generalise to.</p>
  </div>

  <div class="callout" style="--cstripe:var(--serious)">
    <div class="ico">?</div>
    <p><b>On the licence, be careful.</b> MERL&rsquo;s own download page states no licence at all —
    it just asks you to cite the CVPR 2016 paper. The HuggingFace mirror I pulled from is tagged
    Apache-2.0, but that is <b>the uploader&rsquo;s tag, not MERL&rsquo;s</b>, and it binds nobody. For
    research you are fine; before anything commercial, email MERL and get it in writing. The official
    copy is at <span class="mono">merl.com/pub/tmarks/MERL_Shopping_Dataset/</span>, open, no signup.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>RetailAction — the one to build on</h2>{chip('good', 'Build on this')}</div>
  <p class="sdesc">Ceiling-mounted fisheye cameras in 10 US convenience stores, from Standard AI
  (ICCV 2025 Retail Vision workshop). Every clip is filmed by two synchronized cameras at once, and
  every action carries a point marking exactly where on the shelf the product was touched. Faces are
  blurred at source. I pulled the labelled test split in full plus 400 extra clips.</p>
  <div class="callout" style="--cstripe:var(--accent)">
    <div class="ico">i</div>
    <p><b>These labels are theirs, not mine.</b> The <span class="mono">take</span> /
    <span class="mono">put</span> / <span class="mono">touch</span> class, the time span and the contact
    point are Standard AI&rsquo;s human annotation, shipped with the data &mdash; all I did was measure
    them and draw them onto the footage. One thing inside the same file is <i>not</i> human-annotated:
    the 21-joint poses carry per-joint confidence values like <span class="mono">0.4165</span>, which is a
    pose model&rsquo;s output, not a person&rsquo;s. So the 85% hand figure below is that model&rsquo;s
    reliability, not label quality &mdash; treat the contact points as ground truth and the skeletons as
    a helpful extra.</p>
  </div>

  <div class="stats">
    <div class="stat"><div class="k">Clips</div><div class="v">{S['retail_action']['samples']:,}</div><div class="n">×2 cameras = {S['retail_action']['clips']:,} files</div></div>
    <div class="stat"><div class="k">Actions</div><div class="v">{S['retail_action']['actions']:,}</div><div class="n">with time + position</div></div>
    <div class="stat"><div class="k">Frame</div><div class="v">600²</div><div class="n">square crop, fisheye</div></div>
    <div class="stat"><div class="k">Rate</div><div class="v">6 fps</div><div class="n">32 frames per clip</div></div>
    <div class="stat"><div class="k">Pose</div><div class="v">21 pts</div><div class="n">per person per frame</div></div>
    <div class="stat"><div class="k">Size</div><div class="v">{S['retail_action']['size_gb']} GB</div><div class="n">test split, labelled</div></div>
  </div>

  <h3 style="margin-top:32px">The footage, unlabelled</h3>
  <p class="sdesc"><b>Click any card to play it</b> &mdash; all {len([r for r in ra if r.get('vid')])} below
  are real video, both cameras running in sync, with <b>no annotation drawn on them</b>. This is the raw
  footage as a model would receive it. To check the labels against it instead, open the local player,
  which draws the contact point, action window and pose skeleton over the video with toggles &mdash;
  <span class="mono">python3 -m http.server 8000</span> in the data folder, then
  <span class="mono">localhost:8000/player.html</span>. That also gets you all
  {S['retail_action']['samples']:,} clips rather than this sample. The footage is 6 fps, so it will look
  stepped; that is the data, not the player.</p>
  
  <div class="filters" role="group" aria-label="Filter samples by action">
    <button class="fbtn" data-f="all" aria-pressed="true">all {len(ra)}</button>
    <button class="fbtn" data-f="take" aria-pressed="false">take {sum(1 for r in ra if r['label'] == 'take')}</button>
    <button class="fbtn" data-f="put" aria-pressed="false">put {sum(1 for r in ra if r['label'] == 'put')}</button>
    <button class="fbtn" data-f="touch" aria-pressed="false">touch {sum(1 for r in ra if r['label'] == 'touch')}</button>
    <button class="fbtn" data-f="no-action" aria-pressed="false">no action {sum(1 for r in ra if r['label'] == 'no-action')}</button>
  </div>
  <div class="gal" id="ragal">{''.join(ra_cards)}</div>

  <div class="grid2">
    <div class="panel">
      <div class="ctitle">Almost every action is a “take”</div>
      <div class="csub">The {S['retail_action']['actions']:,} labelled actions, by type. The bars are to
      scale — that is the finding. <b>touch</b> has 8 examples in total, so it cannot be trained as its
      own class. Separately, {S['retail_action']['zero']} clips (9.2%) contain no action at all — those
      are deliberate negatives.</div>
      {bars(cls_rows, cls['take'])}
    </div>
    <div class="panel">
      <div class="ctitle">Pose reliability, by joint</div>
      <div class="csub">Share of frames where the joint is detected with confidence above 0.3. Hands —
      the joints that matter for you — land around 85%. Face joints are low because faces are blurred.</div>
      {bars(joint_rows, 100)}
    </div>
  </div>

  <h3 style="margin-top:32px">What a label looks like</h3>
  <p class="sdesc">One JSON file per clip. The part you care about is <span class="mono">labels.action</span>:
  a time span, and an <span class="mono">x,y</span> point per camera at the product. Note where the time
  span is measured from &mdash; see the warning below.</p>
  <pre>{{
  "labels": {{ "action": [ {{
      "start": 0.469,          <b>// fraction of the SEGMENT, not of the video</b>
      "end":   0.688,
      "label": "take",         <b>// take | put | touch</b>
      "spatial": {{ "action_cam": {{
          "rank0": {{ "x": 0.389, "y": 0.255 }},   <b>// contact point, camera 1</b>
          "rank1": {{ "x": 0.212, "y": 0.536 }} }} }}  <b>// same event, camera 2</b>
  }} ] }},
  "action_cam": {{ "rank0": {{
      "poses": [ /* per frame: 21 joints, each [x,y] + confidence */ ],
      "face_positions": [ /* per frame */ ],
      "frame_timestamps": [ <b>/* when each frame really happened — the key to timing */</b> ] }} }},
  "segment_info": {{ "sampled_at_start": ..., "sampled_at_end": ... }}
}}</pre>

  <div class="callout">
    <div class="ico">!</div>
    <p><b>The trap in this dataset &mdash; action times are not video times.</b>
    Every clip is encoded as up to 32 frames at 6 fps, but the segment it came from runs anywhere from
    0.9 s to 49.8 s, and the frames are picked by motion scoring rather than evenly &mdash;
    <b>86% of clips are non-uniformly sampled</b>. The <span class="mono">start</span> and
    <span class="mono">end</span> in the label are fractions of the <b>segment</b>, not of the video, so
    mapping them straight onto the video timeline puts the action in the wrong place: off by more than
    half a second in <b>18.7%</b> of actions, up to 1.58 s, against a median action that lasts only 1.2 s.
    The fix is <span class="mono">frame_timestamps</span>, which says when each encoded frame really
    happened &mdash; I wrote it up as <span class="mono">ra_timing.py</span>, and the overlays here and in
    the local player both go through it. I had this wrong on my first pass; the clips above are corrected.
    319 samples carry no frame timestamps at all, so those can only be approximated.</p>
  </div>

  <div class="callout" style="--cstripe:var(--serious)">
    <div class="ico">!</div>
    <p><b>Three more things to know before you train on it.</b>
    The clips are 6 fps square crops, already cut around motion — good for classifying an action,
    but you cannot do continuous tracking across the store on them.
    <b>put</b> and <b>touch</b> are too rare to learn as separate classes; treat this as take-vs-nothing
    for now, or merge put into take as “interaction”.
    And the stores are uneven — store 1 alone is 36% of the data, so a random split will flatter your numbers.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>Shoplifting CCTV — looks big, is not</h2>{chip('crit', 'Nearly unusable')}</div>
  <p class="sdesc">855 clips, which is why it looked worth pulling. It is not: I checked the frames and
  almost all of it is a single camera in a single shop, recorded on one day. There are no labels of any kind.</p>

  <div class="stats">
    <div class="stat"><div class="k">Clips</div><div class="v">{S['shoplifting']['clips']}</div><div class="n">no annotations</div></div>
    <div class="stat"><div class="k">Unique files</div><div class="v">{S['shoplifting']['unique']}</div><div class="n">218 exact duplicates</div></div>
    <div class="stat"><div class="k">Distinct views</div><div class="v">~1</div><div class="n">99% one camera</div></div>
    <div class="stat"><div class="k">Footage</div><div class="v">{S['shoplifting']['minutes']} min</div><div class="n">all dated 2024-02-23</div></div>
    <div class="stat"><div class="k">Frame</div><div class="v">704×576</div><div class="n">25 fps, true CCTV</div></div>
  </div>

  <div class="callout">
    <div class="ico">✕</div>
    <p><b>Two independent problems.</b> First, <b>218 clips are byte-for-byte copies</b> of another clip in
    the set — same file, different name — so the real count is {S['shoplifting']['unique']}, not 855.
    Second, and worse: measuring every frame against the average background, <b>99% of clips sit within
    normal variation of one single camera view</b>, and the burnt-in timestamps all read 2024-02-23.
    A model trained here would learn this one shop's shelves, not what taking a product looks like.</p>
  </div>

  <p class="sdesc" style="margin-top:22px">Play a few and you will see it immediately — every clip is
  the same aisle from the same angle. The first {len([r for r in shop if r.get('vid')])} cards play;
  the rest show three moments from the clip so you can still see the movement.
  <span class="tag t-dup">dup</span> marks a file with an identical twin.</p>
  <div class="gal">{''.join(shop_cards)}</div>
  <p class="sdesc" style="margin-top:14px">One thing it is genuinely good for: it is real surveillance
  hardware at a realistic 704×576, so it is a fair test of whether a model still works at CCTV quality
  rather than on clean HD. Keep it as a sanity check, not as training data.</p>
</section>

<section>
  <div class="shead"><h2>Intel retail clips — right idea, too small</h2>{chip('warn', 'Too small')}</div>
  <p class="sdesc">16 clips of 1080p overhead footage, each with a written description of what the
  shoppers do, including whether they took anything off the shelf. The descriptions are unusually
  detailed. The catch is the size — 1.5 minutes in total, one aisle, and it is a hardware store rather
  than a grocery.</p>
  <div class="stats">
    <div class="stat"><div class="k">Clips</div><div class="v">16</div><div class="n">1920×1080, 24 fps</div></div>
    <div class="stat"><div class="k">Footage</div><div class="v">1.5 min</div><div class="n">~5 s each</div></div>
    <div class="stat"><div class="k">Labels</div><div class="v">Text</div><div class="n">prose, not boxes</div></div>
    <div class="stat"><div class="k">Views</div><div class="v">1</div><div class="n">single aisle</div></div>
  </div>
  <div class="gal" style="margin-top:20px">{''.join(intel_cards)}</div>
</section>

<section>
  <div class="shead"><h2>Shelf stills — neither half survives</h2>{chip('crit', 'Drop both')}</div>
  <p class="sdesc">I pulled these to cover a later need: a detector that recognises <i>which</i> product
  was taken, not just that something was. Neither half holds up, for two unrelated reasons, and you can
  see both in the grid below.</p>
  <div class="callout">
    <div class="ico">✕</div>
    <p><b>The 15 grocery photos are licence-blocked</b> — CC BY-NC-ND, meaning non-commercial and no
    derivatives. They are a teaser for a dataset UniDataPro sells; if you want that data, licence it
    properly. <b>The other 19 are not grocery at all.</b> Despite the name &ldquo;retail in the
    wild&rdquo;, they are phone photos of clothing in Zara and Pull&amp;Bear — jackets on hangers,
    mannequins, one pair of shoes. Wrong domain entirely. I should have looked at them before counting
    them as 34 shelf photos in my first summary; only 15 ever were.</p>
  </div>
  <div class="gal" style="margin-top:20px">{''.join(img_cards)}</div>
</section>

<section>
  <div class="shead"><h2>Locate anything, by name</h2>{chip('good', 'Closest fit')}</div>
  <p class="sdesc">You wanted a locate-everything model, and the right one exists:
  <span class="mono">nvidia/LocateAnything-3B</span>, released May 2026. It is not a fixed-class
  detector &mdash; you type what you want in plain words and it returns one box per instance. That is a
  much better match for your problem than pixel-wise segmentation, which I also tried and dropped &mdash;
  it found a person in <b>every single clip</b> here, which the segmentation model did not.</p>

  <div class="picker">
    <div class="plist" role="group" aria-label="Choose a frame">
      {''.join(
        (f'<div class="pgrp">{v["source"]}</div>' if i == 0 or loc[i-1]["source"] != v["source"] else '') +
        f'<button class="lbtn" data-i="{i}" aria-pressed="{str(i == 0).lower()}">{v["name"]}</button>'
        for i, v in enumerate(loc))}
    </div>
    <div class="pstage">
      <video id="locv" controls autoplay loop muted playsinline hidden></video>
      <img id="locimg" alt="LocateAnything detections">
      <div class="pmeta mono" id="locm"></div>
    </div>
  </div>
  <div class="callout" style="--cstripe:var(--accent)">
    <div class="ico">i</div>
    <p><b>How the three video entries were made.</b> Inference is seconds per frame, so detecting every
    frame is not possible on this Mac. Instead the shelf stock (<span class="mono">product</span>) is
    detected <b>once</b> on the first frame and held &mdash; it barely moves &mdash; while the shopper and
    the held item are re-detected <b>every 12th frame</b>, about 2.5&times; a second, each box held until
    the next detection. So these are real detections refreshed a few times a second, not a tracker. Where
    a box lags the person slightly, that is the sampling gap. Each 7-second clip took about
    <b>7 minutes</b> to annotate.</p>
  </div>

  <p class="sdesc" style="margin-top:14px">Raw frame left, what it found right. Nothing was trained for
  this footage &mdash; every box comes from words I typed. The phrases differ by source because the
  wording has to match what is actually on the shelf:
  <span class="mono">person / item in hand / product</span> on MERL,
  <span class="mono">person / bottle / cardboard box</span> on the rest.</p>

  <div class="callout" style="--cstripe:var(--good)">
    <div class="ico">&rarr;</div>
    <p><b>The MERL frames are the best result in this whole exercise &mdash; start with those.</b> On
    <span class="mono">21_1</span> it boxes the shopper, puts a tight box on the <b>item in her raised
    hand</b>, and separates <b>45 individual packets</b> on the shelf behind her. That is all three
    things you need at once: who, what they are holding, and what is still on the shelf. It works here
    and not on your other footage for one reason &mdash; 920&times;680 pointed straight down at a
    well-lit shelf gives each packet enough pixels to be its own object. Clearest evidence yet that the
    camera, not the model, decides whether this approach works.</p>
  </div>

  <div class="callout" style="--cstripe:var(--good)">
    <div class="ico">&rarr;</div>
    <p><b>What it gets right.</b> <span class="mono">person</span> was found in <b>8 of 8</b> frames,
    including the 704&times;576 CCTV where the segmentation model missed the person entirely. <span class="mono">cardboard box</span> landed exactly on the two white cartons on
    the Intel shelf. And asking for <span class="mono">bottle</span> on a stocked rack returns dozens of
    separate boxes rather than one region &mdash; individual goods, which is the thing you actually need.</p>
  </div>

  <div class="callout">
    <div class="ico">!</div>
    <p><b>What it gets wrong, and the catches.</b> The dense results are rougher than they look: on the
    shoplifting frame the 71 <span class="mono">bottle</span> boxes tile the shelf in uniform strips
    rather than sitting tightly on each bottle, and one <span class="mono">cardboard box</span> landed on
    a sink. The wording matters more than it should &mdash; &ldquo;bottle&rdquo; found products where
    &ldquo;snack packet&rdquo; returned a single blob, and asking for several categories at once made it
    return whole-frame boxes for all of them. Some of that is the 4-bit build; see the limits below.</p>
  </div>

  <div class="callout" style="--cstripe:var(--crit)">
    <div class="ico">&#10005;</div>
    <p><b>Two hard limits before you build on it.</b> First, the licence: NVIDIA releases LocateAnything
    for <b>research and non-commercial use only</b> &mdash; explicitly not for commercial products. Given
    RetailAction already caps you at $10,000 of revenue, that is now two of your main components blocked
    for a paid product. Second, this Mac: the model is 7.7&nbsp;GB in bfloat16 and you have 8&nbsp;GB of
    memory total. The 8-bit build OOMs the GPU outright, so everything here ran on the <b>4-bit</b> build,
    which is where some of the sloppiness comes from. Inference is 3&ndash;60&nbsp;s per frame, so these
    are <b>single frames, not video</b>. On a CUDA box you would run the full-precision model over whole
    clips and get materially better boxes.</p>
  </div>

  <h3 style="margin-top:32px">Does it locate everything if you do not tell it what to look for?</h3>
  <p class="sdesc">No. Despite the name it is a <b>grounding</b> model: it needs a noun to ground. Give it
  a concrete one and it is excellent. Ask it for &ldquo;everything&rdquo;, &ldquo;objects&rdquo; or
  &ldquo;every object in the frame&rdquo; and it either boxes the whole picture or falls apart.
  All counts below are <b>distinct</b> boxes, after removing repeats &mdash; which matters, see the
  warning underneath.</p>
  <div class="twrap"><table>
    <thead><tr><th>What I asked for</th><th>RetailAction 600px</th><th>Shoplifting 704px</th><th>Intel 1080p</th></tr></thead>
    <tbody>
      <tr><td class="mono">Locate every object in the frame.</td>
          <td>2 coarse boxes</td>
          <td class="mono" style="color:var(--crit)">1 &mdash; looped 148&times;</td>
          <td class="mono" style="color:var(--crit)">0 &mdash; whole frame</td></tr>
      <tr><td class="mono">everything</td><td>3 coarse boxes</td>
          <td class="mono" style="color:var(--crit)">0 &mdash; whole frame</td>
          <td class="mono" style="color:var(--crit)">0 &mdash; whole frame</td></tr>
      <tr><td class="mono">objects</td><td>3 coarse boxes</td><td>63, one shelf only</td>
          <td class="mono" style="color:var(--crit)">0 &mdash; whole frame</td></tr>
      <tr><td class="mono">product</td><td>2 coarse boxes</td><td>9 scattered</td><td><b>142</b></td></tr>
      <tr><td class="mono">bottle</td><td><b>47</b></td><td><b>140</b></td>
          <td class="mono" style="color:var(--crit)">1 &mdash; looped 149&times;</td></tr>
    </tbody>
  </table></div>

  <div class="callout">
    <div class="ico">!</div>
    <p><b>The failure mode that fools you: it loops.</b> Asked to locate every object in the shoplifting
    frame, the model emitted <b>148 boxes that were all the identical box</b> &mdash; the same
    <span class="mono">(0, 0, 59, 89)</span> corner rectangle, repeated until it hit the token cap. Count
    the output naively and you get a triumphant 148; deduplicate and you get <b>1</b>. The same trap
    caught <span class="mono">bottle</span> on the Intel frame: 149 emitted, 1 distinct. I reported
    inflated numbers for both before I checked, and the figures in this table are the corrected ones.
    <span class="mono">locate.py</span> now deduplicates and prints a warning whenever the output is
    mostly repeats &mdash; if you build on this model, count distinct boxes, never emitted ones.</p>
  </div>

  <div class="gal" style="grid-template-columns:1fr;margin-top:16px">
    {''.join(f'<figure class="card" tabindex="0" data-src="{v["img"]}" data-vid="" data-cap="{v["name"]} &middot; the same frame asked three ways">'
             f'<div class="thumb"><img loading="lazy" src="{v["img"]}" alt="Unconditioned versus named queries on {v["name"]}"></div>'
             f'<figcaption class="cmeta"><span>{v["name"]}</span><span class="tag t-none">everything / objects / product</span></figcaption></figure>'
             for v in openc)}
  </div>
  <p class="sdesc" style="margin-top:14px">So there is no &ldquo;point it at the camera and it finds the
  goods&rdquo; mode. <b>You have to know what you are looking for</b> &mdash; which for a grocery store
  means maintaining a vocabulary of product nouns and querying each one. That is a real piece of work,
  and it is the strongest argument for the alternative: detect the <i>interaction</i> from hand position
  and motion using RetailAction&rsquo;s contact points, and never name the product at all.</p>

  <div class="callout" style="--cstripe:var(--accent)">
    <div class="ico">&rarr;</div>
    <p><b>Try your own words.</b>
    <span class="mono">python3 locate.py &lt;clip&gt; --at 2.5 --find "bottle,person,hand"</span>
    runs the model on any frame of any clip and writes a side-by-side like these. Single phrases work far
    better than lists.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>Where this came from</h2></div>
  <p class="sdesc">Every file traced back to its origin, with the licence that governs it. I did not
  create any labels &mdash; each source shipped its own, and I only measured them and drew them onto the
  footage. The licence column is the part to read before you build anything you intend to sell.</p>

  <div class="twrap"><table>
    <thead><tr><th>Source</th><th>Where I got it</th><th>Licence</th><th>What that means for you</th></tr></thead>
    <tbody>
      <tr>
        <td><b>RetailAction</b><br><span class="mono" style="font-size:11.5px">labelled test split</span></td>
        <td class="mono">huggingface.co/datasets/<br>standard-cognition/RetailAction<br><span style="color:var(--ink-3)">data/test.tar</span></td>
        <td class="mono">Standard.AI<br>Dataset Licence</td>
        <td>Usable, with strings. Credit Standard Cognition, ship a copy of the licence, never try to
        re-identify anyone &mdash; and <b>once a product using it earns over $10,000, you must go back to
        Standard for a separate licence</b>, which they grant at their discretion.</td>
      </tr>
      <tr>
        <td><b>RetailAction</b><br><span class="mono" style="font-size:11.5px">400 extra clips</span></td>
        <td class="mono">huggingface.co/datasets/<br>Voxel51/RetailAction</td>
        <td class="mono">Standard.AI<br>Dataset Licence</td>
        <td>A re-hosted subset of the same data with the same licence, but <b>no label files</b> &mdash;
        video only.</td>
      </tr>
      <tr>
        <td><b>Shoplifting CCTV</b></td>
        <td class="mono">huggingface.co/datasets/<br>34data/shoplifting-videos<br><span style="color:var(--ink-3)">data_001.zip</span></td>
        <td class="mono" style="color:var(--crit)">none declared</td>
        <td><b>No licence at all.</b> Real surveillance footage of identifiable people, re-uploaded with
        no stated terms and no consent basis. You have no right to use it and no way to establish one.</td>
      </tr>
      <tr>
        <td><b>Intel retail</b></td>
        <td class="mono">huggingface.co/datasets/<br>Intel/Video_Summarization_For_Retail</td>
        <td class="mono">CC BY-SA 4.0</td>
        <td>Free to use commercially, but <b>share-alike</b>: anything derived from it has to be released
        under the same licence. That can reach further than you want if it touches a model you ship.</td>
      </tr>
      <tr>
        <td><b>Shelf stills</b><br><span class="mono" style="font-size:11.5px">15 annotated</span></td>
        <td class="mono">huggingface.co/datasets/<br>UniDataPro/grocery-shelves</td>
        <td class="mono" style="color:var(--crit)">CC BY-NC-ND 4.0</td>
        <td><b>Non-commercial and no-derivatives.</b> You cannot use it in a commercial product and
        cannot distribute anything modified &mdash; which training on it arguably is. A teaser for a paid
        dataset; licence the real one if you want it.</td>
      </tr>
      <tr>
        <td><b>Shelf stills</b><br><span class="mono" style="font-size:11.5px">19 in-the-wild</span></td>
        <td class="mono">huggingface.co/datasets/<br>merve/retail-in-the-wild</td>
        <td class="mono" style="color:var(--good)">Apache 2.0</td>
        <td>Permissive. Use it however you like, including commercially.</td>
      </tr>
    </tbody>
  </table></div>

  <div class="callout">
    <div class="ico">!</div>
    <p><b>The licences change two of my earlier calls.</b> The shelf stills I filed under &ldquo;side use
    only&rdquo; are <b>CC BY-NC-ND</b> &mdash; non-commercial, no derivatives &mdash; so if this project is
    ever a product, the 15 annotated ones are off the table regardless of how useful they look. And the
    shoplifting set carries <b>no licence whatsoever</b>: I was already recommending you drop it for being
    one camera on one day with no labels, and the lack of any usage rights settles it. I would delete
    that 1.8 GB rather than leave it in the project.</p>
  </div>

  <div class="callout" style="--cstripe:var(--good)">
    <div class="ico">&rarr;</div>
    <p><b>Cite it like this.</b> RetailAction was published at the ICCV 2025 Retail Vision workshop:
    Mazzini, Raimondi, Abbate, Fischetti and Woollard, <i>&ldquo;RetailAction: Dataset for Multi-View
    Spatio-Temporal Localization of Human&ndash;Object Interactions in Retail&rdquo;</i>, Standard AI. The
    licence text is on disk at <span class="mono">raw/retail_action/LICENSE</span> &mdash; keep it there,
    since redistributing any part of the data means shipping that file with it.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>Every check I ran</h2></div>
  <p class="sdesc">So you can see what the verdicts are based on, and re-run anything you doubt.</p>
  <div class="twrap"><table>
    <thead><tr><th>Check</th><th>Result</th><th>What it means</th></tr></thead>
    <tbody>
      <tr><td>Duplicate files</td><td class="mono">218 of 855</td><td>Shoplifting set is 25% redundant; found by hashing every file</td></tr>
      <tr><td>Camera diversity</td><td class="mono">99% one view</td><td>Each frame compared to the average background — the spread is one tight cluster, not many</td></tr>
      <tr><td>Recording dates</td><td class="mono">1 day</td><td>Burnt-in timestamps all read 2024-02-23</td></tr>
      <tr><td>Class balance</td><td class="mono">97.7 / 2.0 / 0.3</td><td>take / put / touch — only take has usable volume</td></tr>
      <tr><td>Empty clips</td><td class="mono">229 (9.2%)</td><td>Deliberate negatives in RetailAction, not an error</td></tr>
      <tr><td>Contact points</td><td class="mono">2466, 0 bad</td><td>Every action has a point on both cameras, all inside the frame</td></tr>
      <tr><td>Label&ndash;video timing</td><td class="mono">18.7% off &gt;0.5 s</td><td>Action times are fractions of the segment, not the video; 86% of clips are non-uniformly sampled</td></tr>
      <tr><td>Missing frame times</td><td class="mono">319 of 2,501</td><td>No <span class="mono">frame_timestamps</span>, so their action timing can only be approximated</td></tr>
      <tr><td>Clip length</td><td class="mono">16&ndash;32 frames</td><td>Not always 32 &mdash; assume variable length when batching</td></tr>
      <tr><td>Pose gaps</td><td class="mono">1.8% empty</td><td>Frames where no person was detected at all</td></tr>
      <tr><td>Hand detection</td><td class="mono">85%</td><td>Hands are found in most frames — the joint you need most</td></tr>
      <tr><td>Broken downloads</td><td class="mono">2, refetched</td><td>Two truncated files, re-pulled and verified</td></tr>
      <tr><td>Video integrity</td><td class="mono">871 / 871</td><td>Every file opens and decodes</td></tr>
    </tbody>
  </table></div>
  <div class="callout" style="--cstripe:var(--warn)">
    <div class="ico">?</div>
    <p><b>One caveat on my own method.</b> I tried to group the shoplifting clips into distinct scenes
    automatically and the result was not trustworthy — on dark, low-contrast CCTV, two unrelated frames
    score about as similar as two related ones. So the “one camera” finding rests on the background
    measurement and on looking at the frames directly, both of which agree. Take the exact duplicate
    count as solid and the scene count as a judgement call.</p>
  </div>
</section>

<section>
  <div class="shead"><h2>Where it is, and what I would do next</h2></div>
  <pre>cctv-grocery-data/
  <b>player.html</b>                  <b>review every clip, with live annotation overlay</b>
  ra_timing.py                 <b>the label-to-video time mapping — use this, not a linear one</b>
  raw/ra_labeled/test/&lt;id&gt;/   <b>2,501 clips · rank0+rank1 mp4 + metadata.json</b>
  raw/retail_action/           <b>400 extra clips, no labels</b>
  raw/shoplifting_34data/      <b>855 clips, one camera</b>
  raw/intel_retail/            <b>16 clips + written summaries</b>
  raw/grocery_shelves/         <b>shelf photos + box outlines</b>
  meta/                        <b>all measurements as json</b>
  clips/, previews/            <b>the compressed clips and frames on this page</b></pre>
  <p class="sdesc" style="margin-top:18px"><b>To review the whole library:</b>
  <span class="mono">cd ~/cctv-grocery-data &amp;&amp; python3 -m http.server 8000</span>, then open
  <span class="mono">localhost:8000/player.html</span>. It lists all 2,501 RetailAction clips plus the
  855 shoplifting ones, plays both cameras in sync, and draws the contact point, the action window and
  the pose skeleton live over the video. Arrow keys move through the list,
  <span class="mono">,</span> and <span class="mono">.</span> step one frame.</p>
  <p class="sdesc" style="margin-top:20px">If RetailAction looks right to you, the obvious next step is
  to pull its training split — the test split I took is {S['retail_action']['size_gb']} GB, and train is
  another 26 GB with roughly eight times the clips. Worth doing once, not twice, so I would rather you
  confirm the data is what you want first. Two things I would want your call on: whether to merge
  <b>put</b> into <b>take</b> as a single “interaction” class given how few puts there are, and whether
  to split by store rather than at random so the numbers stay honest.</p>
</section>

</div>

<div class="lb" id="lb" role="dialog" aria-modal="true" aria-label="Clip player">
  <button class="cx" id="lbx">close ✕</button>
  <div class="lbstage">
    <video id="lbv" controls autoplay loop playsinline muted hidden></video>
    <img id="lbi" alt="" hidden>
  </div>
  <div class="lbcap mono" id="lbc"></div>
</div>

<script>
(function(){{
  var gal = document.getElementById('ragal');
  document.querySelectorAll('.fbtn').forEach(function(b){{
    b.addEventListener('click', function(){{
      var f = b.dataset.f;
      document.querySelectorAll('.fbtn').forEach(function(o){{
        o.setAttribute('aria-pressed', String(o === b));
      }});
      gal.querySelectorAll('.card').forEach(function(c){{
        c.style.display = (f === 'all' || c.dataset.lab === f) ? '' : 'none';
      }});
    }});
  }});
  var lb = document.getElementById('lb'), li = document.getElementById('lbi'),
      lv = document.getElementById('lbv'), lc = document.getElementById('lbc');
  function open(c){{
    var v = c.dataset.vid;
    lc.textContent = c.dataset.cap || '';
    if(v){{
      li.hidden = true; li.removeAttribute('src');
      lv.hidden = false; lv.src = v; lv.play().catch(function(){{}});
    }} else {{
      lv.hidden = true; lv.pause(); lv.removeAttribute('src');
      li.hidden = false; li.src = c.dataset.src;
      var im = c.querySelector('img'); li.alt = im ? im.alt : '';
    }}
    lb.setAttribute('open',''); document.getElementById('lbx').focus();
  }}
  function close(){{
    lb.removeAttribute('open');
    lv.pause(); lv.removeAttribute('src'); li.removeAttribute('src');
  }}
  document.querySelectorAll('.card').forEach(function(c){{
    c.addEventListener('click', function(){{ open(c); }});
    c.addEventListener('keydown', function(e){{
      if(e.key === 'Enter' || e.key === ' '){{ e.preventDefault(); open(c); }}
    }});
  }});


  var LOC = %%LOCJSON%%;
  var LCOL = ['#ff4646','#3cc8ff','#be78ff','#ffbe28'];
  var locimg = document.getElementById('locimg'), locv = document.getElementById('locv'), locm = document.getElementById('locm');
  function showLoc(i){{
    var v = LOC[i]; if(!v) return;
    document.querySelectorAll('.lbtn').forEach(function(b){{
      b.setAttribute('aria-pressed', String(+b.dataset.i === i)); }});
    if (v.vid) {{
      locimg.hidden = true; locimg.removeAttribute('src');
      locv.hidden = false; locv.src = v.vid; locv.play().catch(function(){{}});
    }} else {{
      locv.hidden = true; locv.pause(); locv.removeAttribute('src');
      locimg.hidden = false; locimg.src = v.img;
      locimg.alt = 'LocateAnything detections on ' + v.name;
    }}
    var rows = Object.keys(v.kept).map(function(k, j){{
      return '<span class="pcls"><i style="background:' + LCOL[j % LCOL.length] + '"></i>' +
             k + ' ' + v.kept[k] + '</span>'; }}).join('');
    var zero = Object.keys(v.kept).filter(function(k){{ return !v.kept[k]; }});
    locm.innerHTML = '<b>' + v.name + '</b> &middot; ' + v.source + ' &middot; ' +
      (v.vid ? 'video &middot; ' + Math.round(v.secs) + 's to annotate' : v.secs.toFixed(1) + 's for three queries') + '<br>' + rows +
      (v.note ? '<br><span style="color:' + (/misfire|only fires/.test(v.note) ? 'var(--crit)' : 'var(--ink-3)') + '">' + v.note + '</span>' : '') +
      (zero.length ? '<br><span style="color:var(--crit)">nothing found for: ' + zero.join(', ') + '</span>' : '');
  }}
  document.querySelectorAll('.lbtn').forEach(function(b){{
    b.addEventListener('click', function(){{ showLoc(+b.dataset.i); }}); }});
  if (LOC.length) showLoc(0);

  var MERL = %%MERLJSON%%;
  var merlv = document.getElementById('merlv'), merlm = document.getElementById('merlm');
  function showMerl(i){{
    var v = MERL[i]; if(!v) return;
    document.querySelectorAll('.mbtn').forEach(function(b){{
      b.setAttribute('aria-pressed', String(+b.dataset.i === i)); }});
    merlv.src = v.vid; merlv.poster = v.img; merlv.play().catch(function(){{}});
    merlm.innerHTML = '<b>' + v.name + '</b> &middot; subject ' + v.subject +
      ' &middot; 920x680 at 30 fps &middot; cut around a labelled Inspect Product';
  }}
  document.querySelectorAll('.mbtn').forEach(function(b){{
    b.addEventListener('click', function(){{ showMerl(+b.dataset.i); }}); }});
  if (MERL.length) showMerl(0);



  document.getElementById('lbx').addEventListener('click', close);
  lb.addEventListener('click', function(e){{ if(e.target === lb) close(); }});
  document.addEventListener('keydown', function(e){{ if(e.key === 'Escape') close(); }});
}})();
</script>
"""

# The artifact wrapper supplies <head>, so we cannot declare a charset. Encode every
# non-ASCII character as a numeric entity instead — renders correctly under any charset.
HTML = HTML.replace('%%LOCJSON%%', json.dumps(loc)).replace('%%MERLJSON%%', json.dumps(merl))
SAFE = HTML.encode('ascii', 'xmlcharrefreplace').decode('ascii')
_out = '' + ('review-lite.html' if LITE else 'review.html')
open(_out, 'w').write(SAFE)
print('wrote', _out.split('/')[-1], round(len(SAFE) / 1e6, 2), 'MB',
      '| non-ascii remaining:', sum(1 for c in SAFE if ord(c) > 127))
