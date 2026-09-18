#!/usr/bin/env python3
"""Ask NVIDIA LocateAnything-3B to find things in any clip, by name.

  python3 locate.py raw/ra_labeled/test/000095/rank0_video.mp4 --at 2.5 \
      --find "bottle,person,snack packet"

  python3 locate.py --batch            # rebuild the set shown in the report

Unlike a fixed-class detector, you type what you want in words and it returns one
box per instance. Output is a side-by-side JPEG: raw frame left, detections right.

Model: mlx-community/LocateAnything-3B-4bit (Apple-Silicon build of
nvidia/LocateAnything-3B). NOTE: NVIDIA's licence is research / non-commercial only.

Why 4-bit and why single frames: this Mac has 8 GB of unified memory. The 8-bit
build OOMs the GPU, and inference runs 3-60 s per frame, so whole-video runs are
not practical here. A CUDA box would do both.
"""
import argparse, gc, io, json, os, re, subprocess, time

from PIL import Image, ImageDraw

MODEL_ID = 'mlx-community/LocateAnything-3B-4bit'
OUT_DIR = 'located'
MAX_SIDE = 640           # above this the Metal buffer limit is exceeded
MAX_TOKENS = 450         # dense queries can otherwise exhaust GPU memory

PALETTE = [(255, 70, 70), (60, 200, 255), (190, 120, 255), (255, 190, 40),
           (120, 255, 150), (255, 130, 200), (120, 190, 255), (230, 230, 120)]

_m = _p = None


def load_model():
    global _m, _p
    if _m is None:
        from mlx_vlm import load
        _m, _p = load(MODEL_ID)
    return _m, _p


def grab(video, at, max_side=MAX_SIDE):
    raw = subprocess.run(['ffmpeg', '-v', 'quiet', '-ss', str(at), '-i', video,
                          '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True).stdout
    if not raw:
        raise SystemExit(f'could not read a frame from {video} at {at}s')
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    if max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((int(im.width * s) // 2 * 2, int(im.height * s) // 2 * 2), Image.LANCZOS)
    return im


def locate(img, phrase, max_tokens=MAX_TOKENS):
    """Return [[x1,y1,x2,y2], ...] in 0-1000 space for one phrase."""
    import mlx.core as mx
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, proc = load_model()
    tmp = '/tmp/_locate_in.png'
    img.save(tmp)
    q = f'Locate all the instances that matches the following description: {phrase}.'
    prompt = apply_chat_template(proc, model.config, q, num_images=1)
    try:
        out = generate(model, proc, prompt, [tmp], max_tokens=max_tokens, verbose=False)
    except Exception as e:
        print(f'   ! {phrase}: {str(e)[:70]}')
        return []
    finally:
        mx.clear_cache()
        gc.collect()
    txt = out if isinstance(out, str) else getattr(out, 'text', str(out))
    boxes = [tuple(int(v) for v in re.findall(r'<(\d+)>', b))
             for b in re.findall(r'<box>((?:<\d+>){4})</box>', txt)]
    # The 4-bit model frequently falls into a loop, emitting one box over and over
    # until the token cap. Count distinct boxes, and say so when it happens.
    uniq = list(dict.fromkeys(boxes))
    if boxes and len(uniq) <= max(1, len(boxes) // 10):
        print(f'   ~ {phrase}: degenerate — {len(boxes)} boxes emitted, only '
              f'{len(uniq)} distinct (looped until the token cap)')
    return [list(b) for b in uniq]


def draw(img, found, out_path):
    """found: {phrase: [boxes]} -> side-by-side JPEG. Returns kept-count per phrase."""
    W, H = img.size
    canvas = img.copy()
    d = ImageDraw.Draw(canvas)
    kept, seen = {}, set()
    for i, (phrase, boxes) in enumerate(found.items()):
        col = PALETTE[i % len(PALETTE)]
        n = 0
        for b in boxes:
            key = (phrase,) + tuple(b)
            if key in seen:
                continue
            seen.add(key)
            x1, y1, x2, y2 = b[0]/1000*W, b[1]/1000*H, b[2]/1000*W, b[3]/1000*H
            if x2 - x1 < 3 or y2 - y1 < 3:
                continue
            if x2 - x1 > W * .97 and y2 - y1 > H * .97:    # whole-frame answer = no answer
                continue
            d.rectangle([x1, y1, x2, y2], outline=col, width=2)
            n += 1
        kept[phrase] = n
    # legend
    d.rectangle([0, 0, 132, 8 + 15 * len(found)], fill=(8, 11, 14))
    for i, phrase in enumerate(found):
        y = 5 + 15 * i
        d.rectangle([6, y + 2, 15, y + 11], fill=PALETTE[i % len(PALETTE)])
        d.text((21, y), f'{phrase[:15]}  {kept[phrase]}', fill=(232, 238, 244))
    comb = Image.new('RGB', (W * 2 + 4, H), (12, 15, 18))
    comb.paste(img, (0, 0))
    comb.paste(canvas, (W + 4, 0))
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    comb.save(out_path, quality=88, optimize=True)
    return kept


def run(video, at, phrases, out=None):
    img = grab(video, at)
    found, times = {}, {}
    for ph in phrases:
        t0 = time.time()
        found[ph] = locate(img, ph)
        times[ph] = round(time.time() - t0, 1)
        print(f'   {ph:<20} {len(found[ph]):>3} boxes  {times[ph]:>5}s')
    out = out or os.path.join(OUT_DIR, os.path.splitext(os.path.basename(video))[0] + '.jpg')
    kept = draw(img, found, out)
    return dict(video=video, at=at, out=out, size=list(img.size), kept=kept, secs=times)


BATCH = [
    ('raw/ra_labeled/test/000095/rank0_video.mp4', 2.5, 'RetailAction'),
    ('raw/ra_labeled/test/000250/rank0_video.mp4', 2.5, 'RetailAction'),
    ('raw/ra_labeled/test/001750/rank0_video.mp4', 2.5, 'RetailAction'),
    ('raw/ra_labeled/test/002250/rank0_video.mp4', 2.5, 'RetailAction'),
    ('raw/intel_retail/VideoSumForRetailData/clips/clip1.mp4', 2.0, 'Intel'),
    ('raw/intel_retail/VideoSumForRetailData/clips/clip10.mp4', 2.0, 'Intel'),
    ('raw/shoplifting_34data/shop_lifter_1.mp4', 3.0, 'Shoplifting'),
    ('raw/shoplifting_34data/shop_lifter_10.mp4', 4.0, 'Shoplifting'),
]
PHRASES = ['person', 'bottle', 'cardboard box']


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video', nargs='?')
    ap.add_argument('--at', type=float, default=2.5, help='seconds into the clip')
    ap.add_argument('--find', default=','.join(PHRASES), help='comma-separated phrases')
    ap.add_argument('--out')
    ap.add_argument('--batch', action='store_true')
    a = ap.parse_args()

    if a.batch:
        # One clip per subprocess: 8 GB of unified memory fragments badly if several
        # dense queries share a process, and the GPU OOMs part-way through.
        import sys
        res = []
        for i, (v, at, src) in enumerate(BATCH, 1):
            name = os.path.basename(os.path.dirname(v)) if 'ra_labeled' in v \
                else os.path.splitext(os.path.basename(v))[0]
            out = f'{OUT_DIR}/{src}_{name}.jpg'
            tmp = f'/tmp/_locate_{i}.json'
            print(f'[{i}/{len(BATCH)}] {name}', flush=True)
            p = subprocess.run([sys.executable, __file__, v, '--at', str(at),
                                '--find', ','.join(PHRASES), '--out', out],
                               capture_output=True, text=True)
            if p.returncode != 0 or not os.path.exists(out):
                print(f'   failed: {(p.stderr or "").strip().splitlines()[-1][:90] if p.stderr else "?"}')
                continue
            try:
                r = json.loads(p.stdout[p.stdout.index('{'):])
            except Exception:
                r = dict(video=v, at=at, out=out, kept={}, secs={})
            r['source'], r['name'] = src, name
            print('   ' + ', '.join(f'{k}:{val}' for k, val in r.get('kept', {}).items()))
            res.append(r)
        json.dump(res, open('meta/located.json', 'w'), indent=1)
        print(f'wrote meta/located.json ({len(res)}/{len(BATCH)} ok)')
    else:
        if not a.video:
            ap.error('give a video path, or --batch')
        r = run(a.video, a.at, [p.strip() for p in a.find.split(',') if p.strip()], a.out)
        print(json.dumps(r, indent=1))
