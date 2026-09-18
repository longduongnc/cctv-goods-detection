#!/usr/bin/env python3
"""Run NVIDIA SegFormer over any clip in this project and render the result.

  python3 segment.py raw/ra_labeled/test/000095/rank0_video.mp4
  python3 segment.py --list                     # what you can run it on
  python3 segment.py --batch 14                 # precompute a set for the UI

Output is a side-by-side video: clean footage on the left, the model's
pixel-wise segmentation on the right. No ground-truth labels are drawn — this
is only what the model sees, so you can judge it on its own.

Model: nvidia/segformer-b4-finetuned-ade-512-512 (150 ADE20K classes).
"""
import argparse, glob, json, os, subprocess, sys, time
import numpy as np
import torch
from PIL import Image, ImageDraw

MODEL_ID = 'nvidia/segformer-b4-finetuned-ade-512-512'
OUT_DIR = 'segmented'

# Classes that would matter for goods moving around a store. Everything else is
# rendered in grey so the relevant classes stand out.
FOCUS = {
    12:  ('person',       (232,  74,  74)),
    24:  ('shelf',        ( 58, 140, 232)),
    98:  ('bottle',       ( 34, 190, 140)),
    120: ('food',         (240, 176,  38)),
    41:  ('box',          (168, 118, 232)),
    112: ('basket',       ( 86, 206, 232)),
    115: ('bag',          (232, 128, 196)),
    50:  ('refrigerator', (120, 170,  90)),
    45:  ('counter',      (200, 140,  90)),
    55:  ('case',         (150, 150, 240)),
    62:  ('bookcase',     ( 90, 160, 200)),
    137: ('tray',         (210, 200, 110)),
}

_model = _proc = _dev = None


def load():
    global _model, _proc, _dev
    if _model is None:
        from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor
        _proc = SegformerImageProcessor.from_pretrained(MODEL_ID)
        _model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID)
        _dev = 'mps' if torch.backends.mps.is_available() else 'cpu'
        _model.to(_dev).eval()
    return _model, _proc, _dev


def read_frames(path, max_side=512, max_frames=64, cap_fps=8.0):
    """Decode a clip to RGB frames, downsampling long ones so this stays tractable."""
    pr = subprocess.run(['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                         '-show_entries', 'stream=width,height,avg_frame_rate',
                         '-of', 'json', path], capture_output=True, text=True).stdout
    st = json.loads(pr)['streams'][0]
    w, h = st['width'], st['height']
    n, d = st['avg_frame_rate'].split('/')
    fps = float(n) / float(d) if float(d) else 12.0
    out_fps = min(fps, cap_fps)
    sc = min(1.0, max_side / max(w, h))
    ow, oh = int(w * sc) // 2 * 2, int(h * sc) // 2 * 2
    vf = f'fps={out_fps},scale={ow}:{oh}'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', vf,
                          '-frames:v', str(max_frames),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, oh, ow, 3)
    return arr, out_fps, (ow, oh)


def segment(frames, batch=4):
    model, proc, dev = load()
    outs = []
    for i in range(0, len(frames), batch):
        chunk = [Image.fromarray(f) for f in frames[i:i+batch]]
        with torch.no_grad():
            inp = proc(images=chunk, return_tensors='pt').to(dev)
            lg = model(**inp).logits
            up = torch.nn.functional.interpolate(
                lg, size=frames.shape[1:3], mode='bilinear', align_corners=False)
            outs.append(up.argmax(1).cpu().numpy().astype(np.uint8))
    return np.concatenate(outs, 0)


def colorise(frame, seg):
    """Grey base + saturated colour on the classes that matter here."""
    grey = frame.mean(2, keepdims=True).repeat(3, 2).astype(np.float32)
    canvas = grey * 0.45 + 30
    for cid, (_, col) in FOCUS.items():
        m = seg == cid
        if m.any():
            canvas[m] = np.array(col, np.float32) * 0.78 + grey[m] * 0.22
    return canvas.clip(0, 255).astype(np.uint8)


def legend(img, seg, id2label):
    """Write the classes actually present, with their share of the frame."""
    d = ImageDraw.Draw(img, 'RGBA')
    u, c = np.unique(seg, return_counts=True)
    order = np.argsort(-c)
    rows = []
    for i in order:
        cid, pct = int(u[i]), 100 * c[i] / seg.size
        if pct < 0.4:
            continue
        name = FOCUS[cid][0] if cid in FOCUS else id2label.get(cid, str(cid))
        col = FOCUS[cid][1] if cid in FOCUS else (150, 150, 150)
        rows.append((name, pct, col))
        if len(rows) >= 7:
            break
    if not rows:
        return img
    d.rectangle([0, 0, 150, 10 + 15 * len(rows)], fill=(8, 11, 14, 190))
    for i, (name, pct, col) in enumerate(rows):
        y = 6 + 15 * i
        d.rectangle([7, y + 2, 16, y + 11], fill=col + (255,))
        d.text((22, y), f'{name}  {pct:.0f}%', fill=(232, 238, 244, 255))
    return img


def run(path, out=None, keep_stats=True):
    model, proc, dev = load()
    id2label = model.config.id2label
    frames, fps, (w, h) = read_frames(path)
    t0 = time.time()
    seg = segment(frames)
    dt = time.time() - t0

    panes = []
    for f, s in zip(frames, seg):
        right = Image.fromarray(colorise(f, s))
        right = legend(right, s, id2label)
        comb = Image.new('RGB', (w * 2 + 4, h), (12, 15, 18))
        comb.paste(Image.fromarray(f), (0, 0))
        comb.paste(right, (w + 4, 0))
        panes.append(np.asarray(comb))

    out = out or os.path.join(OUT_DIR, os.path.basename(os.path.dirname(path))
                              + '_' + os.path.splitext(os.path.basename(path))[0] + '.mp4')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    p = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{w*2+4}x{h}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
         '-crf', '30', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
        stdin=subprocess.PIPE)
    p.communicate(np.stack(panes).tobytes())

    stats = {}
    if keep_stats:
        tot = seg.size
        u, c = np.unique(seg, return_counts=True)
        for cid, cnt in zip(u.tolist(), c.tolist()):
            name = FOCUS[cid][0] if cid in FOCUS else id2label.get(cid, str(cid))
            stats[name] = round(100 * cnt / tot, 2)
    return dict(src=path, out=out, frames=len(frames), secs=round(dt, 2),
                fps_infer=round(len(frames) / dt, 1), classes=stats)


def candidates():
    c = []
    c += [(f'RetailAction {os.path.basename(os.path.dirname(p))}', p)
          for p in sorted(glob.glob('raw/ra_labeled/test/*/rank0_video.mp4'))]
    c += [(f'Shoplifting {os.path.basename(p)}', p)
          for p in sorted(glob.glob('raw/shoplifting_34data/*.mp4'))]
    c += [(f'Intel {os.path.basename(p)}', p)
          for p in sorted(glob.glob('raw/intel_retail/VideoSumForRetailData/clips/*.mp4'))]
    return c


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video', nargs='?')
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--batch', type=int)
    a = ap.parse_args()

    if a.list:
        for name, p in candidates():
            print(f'{name:38} {p}')
        sys.exit()

    if a.batch:
        cands = candidates()
        ra = [p for n, p in cands if n.startswith('RetailAction')]
        sh = [p for n, p in cands if n.startswith('Shoplifting')]
        it = [p for n, p in cands if n.startswith('Intel')]
        step = max(1, len(ra) // max(1, a.batch - 6))
        pick = ra[::step][:a.batch - 6] + sh[:3] + it[:3]
        res = []
        for i, p in enumerate(pick, 1):
            r = run(p)
            res.append(r)
            print(f'[{i}/{len(pick)}] {p} -> {r["out"]}  {r["fps_infer"]} fps')
        json.dump(res, open('meta/segmented.json', 'w'), indent=1)
        print('wrote meta/segmented.json')
        sys.exit()

    if not a.video:
        ap.error('give a video path, or --list / --batch N')
    r = run(a.video, a.out)
    print(json.dumps(r, indent=1))
