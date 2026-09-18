#!/usr/bin/env python3
"""Run LocateAnything across a clip and render an annotated video.

  python3 locate_video.py <clip> --start 8 --dur 8 --out out.mp4 \
      --moving "person,item in hand" --static "product"

Inference is seconds per frame, so detecting every frame is not realistic on this
Mac. Two things make it tractable:

  * "static" phrases (the shelf stock) are detected ONCE on the first frame and
    held for the whole clip - that stock barely moves.
  * "moving" phrases (the shopper, the item in their hand) are detected on a
    sampled subset, and each box is held until the next sample.

So the boxes are real detections, refreshed a few times a second, not a tracker.
Where a box lags the person slightly, that is the sampling gap, not a model error.
"""
import argparse, gc, io, json, os, re, subprocess, sys, time

import numpy as np
from PIL import Image, ImageDraw

MODEL_ID = 'mlx-community/LocateAnything-3B-4bit'
MAX_SIDE = 640
MAX_TOKENS = 450
PALETTE = [(255, 70, 70), (60, 200, 255), (190, 120, 255), (255, 190, 40), (120, 255, 150)]

_m = _p = None


def load_model():
    global _m, _p
    if _m is None:
        from mlx_vlm import load
        _m, _p = load(MODEL_ID)
    return _m, _p


def locate(img, phrase):
    import mlx.core as mx
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, proc = load_model()
    img.save('/tmp/_lv.png')
    q = f'Locate all the instances that matches the following description: {phrase}.'
    prompt = apply_chat_template(proc, model.config, q, num_images=1)
    try:
        out = generate(model, proc, prompt, ['/tmp/_lv.png'], max_tokens=MAX_TOKENS, verbose=False)
    except Exception as e:
        print(f'   ! {phrase}: {str(e)[:60]}', flush=True)
        return []
    finally:
        mx.clear_cache()
        gc.collect()
    txt = out if isinstance(out, str) else getattr(out, 'text', str(out))
    boxes = [tuple(int(v) for v in re.findall(r'<(\d+)>', b))
             for b in re.findall(r'<box>((?:<\d+>){4})</box>', txt)]
    uniq = list(dict.fromkeys(boxes))
    keep = [b for b in uniq
            if b[2] - b[0] > 4 and b[3] - b[1] > 4 and not (b[2] - b[0] > 970 and b[3] - b[1] > 970)]
    return keep


def read(video, start, dur, max_side=MAX_SIDE):
    pr = subprocess.run(['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries',
                         'stream=width,height,avg_frame_rate', '-of', 'json', video],
                        capture_output=True, text=True).stdout
    st = json.loads(pr)['streams'][0]
    w, h = st['width'], st['height']
    n, d = st['avg_frame_rate'].split('/')
    fps = float(n) / float(d) if float(d) else 30.0
    sc = min(1.0, max_side / max(w, h))
    ow, oh = int(w * sc) // 2 * 2, int(h * sc) // 2 * 2
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(dur), '-i', video,
                          '-vf', f'scale={ow}:{oh}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, oh, ow, 3), fps, (ow, oh)


def probe_subproc(png, phrase):
    """One detection in a fresh process - 8 GB fragments badly otherwise."""
    p = subprocess.run([sys.executable, __file__, '--probe', png, '--phrase', phrase],
                       capture_output=True, text=True)
    try:
        return [tuple(b) for b in json.loads(p.stdout.strip().splitlines()[-1])]
    except Exception:
        return []


def run(video, start, dur, moving, static, out, every=10):
    frames, fps, (w, h) = read(video, start, dur)
    n = len(frames)
    print(f'   {n} frames at {fps:.0f} fps, detecting every {every}th', flush=True)

    held = {ph: [] for ph in moving + static}
    per_frame, counts = [], {ph: 0 for ph in moving + static}
    t0 = time.time()
    for i in range(n):
        im = Image.fromarray(frames[i])
        if i == 0:
            im.save('/tmp/_lv_frame.png')
            for ph in static:
                held[ph] = probe_subproc('/tmp/_lv_frame.png', ph)
                counts[ph] = len(held[ph])
                print(f'   static {ph}: {len(held[ph])} boxes', flush=True)
        if i % every == 0:
            im.save('/tmp/_lv_frame.png')
            for ph in moving:
                held[ph] = probe_subproc('/tmp/_lv_frame.png', ph)
                counts[ph] = max(counts[ph], len(held[ph]))
        per_frame.append({ph: list(held[ph]) for ph in held})
    dt = time.time() - t0

    panes = []
    for i in range(n):
        im = Image.fromarray(frames[i]).copy()
        d = ImageDraw.Draw(im)
        for j, ph in enumerate(moving + static):
            col = PALETTE[j % len(PALETTE)]
            for b in per_frame[i][ph]:
                d.rectangle([b[0]/1000*w, b[1]/1000*h, b[2]/1000*w, b[3]/1000*h],
                            outline=col, width=2 if ph in static else 3)
        d.rectangle([0, 0, 150, 8 + 15 * len(held)], fill=(8, 11, 14))
        for j, ph in enumerate(moving + static):
            y = 5 + 15 * j
            d.rectangle([6, y + 2, 15, y + 11], fill=PALETTE[j % len(PALETTE)])
            d.text((21, y), f'{ph[:16]}  {len(per_frame[i][ph])}', fill=(232, 238, 244))
        panes.append(np.asarray(im))

    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                          '-s', f'{w}x{h}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
                          '-crf', '30', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                          '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    p.communicate(np.stack(panes).tobytes())
    return dict(video=video, out=out, frames=n, fps=round(fps, 1), every=every,
                secs=round(dt, 1), counts=counts, size_mb=round(os.path.getsize(out) / 1e6, 2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe'); ap.add_argument('--phrase')
    ap.add_argument('video', nargs='?')
    ap.add_argument('--start', type=float, default=0)
    ap.add_argument('--dur', type=float, default=8)
    ap.add_argument('--moving', default='person,item in hand')
    ap.add_argument('--static', default='product')
    ap.add_argument('--every', type=int, default=10)
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.probe:
        print(json.dumps(locate(Image.open(a.probe).convert('RGB'), a.phrase)))
        sys.exit()
    if not a.video or not a.out:
        ap.error('need a video and --out')
    mv = [x.strip() for x in a.moving.split(',') if x.strip()]
    stc = [x.strip() for x in a.static.split(',') if x.strip()]
    print(json.dumps(run(a.video, a.start, a.dur, mv, stc, a.out, a.every), indent=1))
