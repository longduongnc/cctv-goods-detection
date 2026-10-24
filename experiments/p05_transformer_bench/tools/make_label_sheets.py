"""Blind labelling sheets for the units of one brand in the 39-frame sample (the protocol used for the TH units, 24/10).

Every unit gets a random id. A sheet shows only the id, a context crop with the unit outlined, a tight crop and a
contrast-stretched copy of it, plus reference fronts shrunk to sample size. key.csv (id -> unit) is written apart
and is not looked at until the labels are done. Standalone (PIL only) so it runs on the labeller's machine.

    python -I tools/make_label_sheets.py --sample DIR --brand VNM --prefix N --out DIR --ref VNM-01=front.png ...
"""
import argparse
import csv
import json
import pathlib
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageOps


def reference_strip(refs, height):
    tiles = []
    for name, path in refs:
        im = Image.open(path).convert("RGB")
        small = im.resize((max(1, round(im.width * 60 / im.height)), 60), Image.LANCZOS)
        big = small.resize((round(small.width * height / small.height), height), Image.LANCZOS)
        tile = Image.new("RGB", (big.width + 8, height + 16), "white")
        tile.paste(big, (4, 16))
        ImageDraw.Draw(tile).text((4, 2), name, fill="black")
        tiles.append(tile)
    strip = Image.new("RGB", (sum(t.width for t in tiles), height + 16), "white")
    x = 0
    for t in tiles:
        strip.paste(t, (x, 0))
        x += t.width
    return strip


def tile(frame, unit, height):
    x, y, w, h = json.loads(unit["bounding_box"])
    cx0, cy0 = max(x - int(1.2 * w), 0), max(y - int(0.5 * h), 0)
    cx1, cy1 = min(x + w + int(1.2 * w), frame.width), min(y + h + int(0.5 * h), frame.height)
    s = min(height / (cy1 - cy0), 5.0)
    ctx = frame.crop((cx0, cy0, cx1, cy1)).resize((max(1, round((cx1 - cx0) * s)), max(1, round((cy1 - cy0) * s))), Image.LANCZOS)
    ImageDraw.Draw(ctx).rectangle([(x - cx0) * s - 2, (y - cy0) * s - 2, (x + w - cx0) * s + 1, (y + h - cy0) * s + 1],
                                  outline=(255, 0, 255), width=1)
    m = int(0.1 * h)
    tight = frame.crop((max(x - m, 0), max(y - m, 0), min(x + w + m, frame.width), min(y + h + m, frame.height)))
    tight = tight.resize((max(1, round(tight.width * height / tight.height)), height), Image.LANCZOS)
    enh = ImageEnhance.Color(ImageOps.autocontrast(tight, cutoff=2)).enhance(1.8)
    out = Image.new("RGB", (ctx.width + 2 * tight.width + 12, max(ctx.height, height) + 16), "white")
    out.paste(ctx, (0, 16))
    out.paste(tight, (ctx.width + 4, 16))
    out.paste(enh, (ctx.width + tight.width + 8, 16))
    ImageDraw.Draw(out).text((2, 2), f"{unit['id']}  h={h}px  {unit['image_filename'][6:9]}", fill="black")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=pathlib.Path, required=True, help="folder with cv_output.csv, cv_output_units.csv, images/")
    ap.add_argument("--brand", required=True, choices=["VNM", "TH"])
    ap.add_argument("--prefix", required=True, help="first letter of the random ids, e.g. N for Vinamilk")
    ap.add_argument("--ref", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--seed", type=int, default=20261024)
    ap.add_argument("--per-sheet", type=int, default=16)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--height", type=int, default=140)
    args = ap.parse_args()

    with open(args.sample / "cv_output.csv", encoding="utf-8-sig", newline="") as f:
        image_of = {r["reading_id"]: r["image_filename"] for r in csv.DictReader(f)}
    with open(args.sample / "cv_output_units.csv", encoding="utf-8-sig", newline="") as f:
        units = [u for u in csv.DictReader(f) if f"-{args.brand}-" in u["detector_sku_id"]]
    rng = random.Random(args.seed)
    for u, i in zip(units, rng.sample(range(1, len(units) + 1), len(units))):
        u["id"] = f"{args.prefix}{i:03d}"
        u["image_filename"] = image_of[u["reading_id"]]
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "key.csv", "w", encoding="utf-8", newline="") as f:       # not looked at while labelling
        w = csv.writer(f)
        w.writerow(["id", "capture_id", "bounding_box", "image_filename"])
        for u in units:
            w.writerow([u["id"], u["capture_id"], u["bounding_box"], u["image_filename"]])

    units.sort(key=lambda u: (u["image_filename"], json.loads(u["bounding_box"])[1] // 80, json.loads(u["bounding_box"])[0]))
    refs = reference_strip([r.split("=", 1) for r in args.ref], args.height) if args.ref else None
    frames = {}
    for n in range(0, len(units), args.per_sheet):
        tiles = []
        for u in units[n:n + args.per_sheet]:
            frame = frames.setdefault(u["image_filename"], Image.open(args.sample / "images" / u["image_filename"]).convert("RGB"))
            tiles.append(tile(frame, u, args.height))
        rows = [tiles[i:i + args.cols] for i in range(0, len(tiles), args.cols)]
        width = max([refs.width if refs else 0] + [sum(t.width + 10 for t in r) for r in rows])
        top = refs.height + 8 if refs else 0
        sheet = Image.new("RGB", (width, top + sum(max(t.height for t in r) + 8 for r in rows)), (235, 235, 235))
        if refs:
            sheet.paste(refs, (0, 0))
        yo = top
        for r in rows:
            xo = 0
            for t in r:
                sheet.paste(t, (xo, yo))
                xo += t.width + 10
            yo += max(t.height for t in r) + 8
        sheet.save(args.out / f"sheet_{n // args.per_sheet + 1:02d}.png")
    print(len(units), "units on", (len(units) + args.per_sheet - 1) // args.per_sheet, "sheets in", args.out)


if __name__ == "__main__":
    main()
