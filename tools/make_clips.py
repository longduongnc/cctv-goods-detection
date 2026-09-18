"""Encode small, web-playable clips with the annotation burned in.

RetailAction: rank0 | rank1 side by side, contact-point marker on each view,
and a border that lights up over the labelled action window so you can see
*when* the take happens, not just where.
"""
import json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
from ra_timing import action_window

T = 264                      # tile size per camera
OUT = 'clips'
os.makedirs(f'{OUT}/ra', exist_ok=True)
os.makedirs('clips_clean/ra', exist_ok=True)
os.makedirs(f'{OUT}/shop', exist_ok=True)

RED = 'red@0.95'
CLEAN = os.environ.get('CLEAN') == '1'   # no annotation burned in


def marker(nx, ny, off):
    """Hollow box + outward ticks — leaves the product itself unobscured."""
    X, Y = nx * T + off, ny * T
    b = 13                                     # half box
    parts = [f"drawbox=x={X-b}:y={Y-b}:w={2*b}:h={2*b}:color={RED}:t=2"]
    for dx, dy, w, h in [(-b - 9, -1, 9, 2), (b, -1, 9, 2),
                         (-1, -b - 9, 2, 9), (-1, b, 2, 9)]:
        parts.append(f"drawbox=x={X+dx}:y={Y+dy}:w={w}:h={h}:color={RED}:t=fill")
    return ','.join(parts)


def build_ra(sid):
    src = f'raw/ra_labeled/test/{sid}'
    dst = ('clips_clean' if CLEAN else OUT) + f'/ra/{sid}.mp4'
    d = json.load(open(f'{src}/metadata.json'))['content']
    a = (d['labels']['action'] or [])

    chain = [f"[0:v]scale={T}:{T},setsar=1[a]", f"[1:v]scale={T}:{T},setsar=1[b]",
             "[a][b]hstack=inputs=2[s]"]
    ov = []
    if CLEAN:
        a = []
    if a and a[0].get('spatial'):
        sp = a[0]['spatial']['action_cam']
        if sp.get('rank0'): ov.append(marker(sp['rank0']['x'], sp['rank0']['y'], 0))
        if sp.get('rank1'): ov.append(marker(sp['rank1']['x'], sp['rank1']['y'], T))
    if a:
        # video time, via frame timestamps — NOT start*duration (see ra_timing)
        s, e, _ = action_window(d, a[0])
        ov.append(f"drawbox=x=0:y=0:w={2*T}:h={T}:color={RED}:t=3"
                  f":enable='between(t,{s:.3f},{e:.3f})'")
    chain.append("[s]" + ','.join(ov) + "[o]" if ov else "[s]null[o]")

    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-i', f'{src}/rank0_video.mp4',
         '-i', f'{src}/rank1_video.mp4', '-filter_complex', ';'.join(chain),
         '-map', '[o]', '-an', '-c:v', 'libx264', '-crf', '31', '-preset', 'slow',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst],
        capture_output=True, text=True)
    return (sid, dst, os.path.getsize(dst)) if r.returncode == 0 else (sid, None, 0)


def build_shop(path):
    name = os.path.splitext(os.path.basename(path))[0]
    dst = f'{OUT}/shop/{name}.mp4'
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-t', '9', '-i', path,
         '-vf', 'scale=416:-2,fps=12', '-an', '-c:v', 'libx264', '-crf', '32',
         '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', dst],
        capture_output=True, text=True)
    return (name, dst, os.path.getsize(dst)) if r.returncode == 0 else (name, None, 0)


if __name__ == '__main__':
    ra_ids = [r['sid'] for r in json.load(open('meta/ra_previews.json'))]
    with ThreadPoolExecutor(8) as ex:
        ra = [x for x in ex.map(build_ra, ra_ids) if x[1]]
    print(f'retail_action: {len(ra)} clips, {sum(x[2] for x in ra)/1e6:.2f} MB')

    shop_names = [r['name'] for r in json.load(open('meta/shop_previews.json'))][:10]
    paths = [f'raw/shoplifting_34data/{n}.mp4' for n in shop_names]
    paths = [p for p in paths if os.path.exists(p)]
    with ThreadPoolExecutor(8) as ex:
        sh = [x for x in ex.map(build_shop, paths) if x[1]]
    print(f'shoplifting: {len(sh)} clips, {sum(x[2] for x in sh)/1e6:.2f} MB')

    json.dump({'ra': {s: p for s, p, _ in ra}, 'shop': {s: p for s, p, _ in sh}},
              open('meta/clips.json', 'w'), indent=1)
    print('total', round((sum(x[2] for x in ra) + sum(x[2] for x in sh)) / 1e6, 2), 'MB')
