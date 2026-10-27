"""E1 measurements: megabytes per JPEG picture, and megabits per second of re-encoded video.

    python -m ingest.encode jpeg --images DIR --megapixels 2 8 --label L --machine M --out results/bandwidth_jpeg.csv [--append]
    python -m ingest.encode video --clips FILE... --label L --codecs libx265 libx264 --crf 23 28 --fps 15 \
        --out results/bandwidth_video.csv [--append]

Videos are re-encoded into data/encoded/ (never into the repo); only the sizes are written out.
"""
import argparse
import csv
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

IMAGE_TYPES = (".jpg", ".jpeg", ".png")


def jpeg_mb(image_bgr: np.ndarray, megapixels: float, quality: int = 90) -> float:
    """Size in MB of the picture shrunk (keeping its shape) to that many megapixels and saved as JPEG.
    A picture smaller than the target is refused: enlarging it would invent detail a real camera has to record."""
    h, w = image_bgr.shape[:2]
    if megapixels * 1e6 > h * w * 1.01:
        raise ValueError(f"{w}x{h} is {h * w / 1e6:.1f} MP, smaller than the {megapixels} MP asked for")
    scale = math.sqrt(megapixels * 1e6 / (h * w))
    if scale < 1:
        image_bgr = cv2.resize(image_bgr, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return len(buf) / 1e6


def ffmpeg_cmd(src: Path, dst: Path, codec: str, crf: int, fps: int) -> list[str]:
    """Re-encode without sound at a fixed quality (CRF) and frame rate, 8-bit 4:2:0 like a CCTV stream."""
    return ["ffmpeg", "-y", "-i", str(src), "-an", "-c:v", codec, "-crf", str(crf), "-r", str(fps),
            "-pix_fmt", "yuv420p", "-preset", "medium", str(dst)]


def measure_mbps(path: Path) -> float:
    """Average bitrate of a video file: its size in bits over its duration (frames ÷ frame rate)."""
    cap = cv2.VideoCapture(str(path))
    frames, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if not frames or not fps:
        raise ValueError(f"cannot read the duration of {path}")
    return path.stat().st_size * 8 / (frames / fps) / 1e6


def _write(out: Path, rows: list[dict], append: bool) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    new = not (append and out.exists())
    with open(out, "w" if new else "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerows(rows)


def jpeg_rows(images: Path, megapixels: list[float], label: str, machine: str) -> list[dict]:
    """One row per target size. Pictures smaller than the target are left out and counted in n_skipped: the 39 store
    frames mix 1920×1080 pictures with 480×854 frames cut from low-resolution clips."""
    pictures = [img for p in sorted(images.iterdir()) if p.suffix.lower() in IMAGE_TYPES
                if (img := cv2.imread(str(p))) is not None]
    rows = []
    for mp in megapixels:
        big = [img for img in pictures if mp * 1e6 <= img.shape[0] * img.shape[1] * 1.01]
        sizes = [jpeg_mb(img, mp) for img in big]
        rows.append(dict(label=label, megapixels=mp, n_images=len(sizes), n_skipped=len(pictures) - len(big),
                         mb_median=round(float(np.median(sizes)), 3), mb_p90=round(float(np.percentile(sizes, 90)), 3),
                         machine=machine))
    return rows


def video_rows(clips: list[Path], label: str, codecs: list[str], crfs: list[int], fps: int, workdir: Path) -> list[dict]:
    workdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for clip in clips:
        cap = cv2.VideoCapture(str(clip))
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        for codec in codecs:
            for crf in crfs:
                dst = workdir / f"{clip.stem}_{codec}_crf{crf}_{fps}fps.mp4"
                subprocess.run(ffmpeg_cmd(clip, dst, codec, crf, fps), check=True, capture_output=True)
                rows.append(dict(clip=clip.name, label=label, width=width, height=height, codec=codec, crf=crf, fps=fps,
                                 mbps=round(measure_mbps(dst), 3)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("jpeg")
    j.add_argument("--images", type=Path, required=True)
    j.add_argument("--megapixels", type=float, nargs="+", required=True)
    j.add_argument("--label", required=True)
    j.add_argument("--machine", required=True)
    v = sub.add_parser("video")
    v.add_argument("--clips", type=Path, nargs="+", required=True)
    v.add_argument("--label", required=True)
    v.add_argument("--codecs", nargs="+", default=["libx265", "libx264"])
    v.add_argument("--crf", type=int, nargs="+", default=[23, 28])
    v.add_argument("--fps", type=int, default=15)
    v.add_argument("--workdir", type=Path, default=Path("data/encoded"))
    for p in (j, v):
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--append", action="store_true")
    args = ap.parse_args()
    if args.cmd == "jpeg":
        rows = jpeg_rows(args.images, args.megapixels, args.label, args.machine)
    else:
        rows = video_rows(args.clips, args.label, args.codecs, args.crf, args.fps, args.workdir)
    _write(args.out, rows, args.append)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
