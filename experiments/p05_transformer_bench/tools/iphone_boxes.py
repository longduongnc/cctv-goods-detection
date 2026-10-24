"""Find the carton in each iPhone photo with yolo/best_types.pt (conf 0.25). The held carton is about 2500 px tall,
far bigger than the 20-120 px cartons YOLO learned from, so on the photo shrunk to 1280 px YOLO finds the cartons on the
shelf behind instead. The photo is therefore shrunk to 160-288 px on its long side (the held carton becomes 60-130 px)
and pasted in the middle of a grey 1280 square; of the boxes whose centre lies in the middle of the photo and whose long
side is over 15% of the photo's, the most confident is kept. No such box means the middle of the photo (20-80% across,
10-90% down). Boxes are [x, y, w, h] in the full-size photo as cv2 reads it (EXIF rotation applied).

A sheet with every box drawn is written to check them by eye; a wrong box is fixed by hand in the CSV with
method=manual, and a rerun keeps the manual rows.

    python tools/iphone_boxes.py --photos data/iphone --model ~/Desktop/Datagent/yolo/best_types.pt \
        --out labels/iphone_boxes.csv --sheet results/iphone_boxes.png
"""
import argparse
import csv
import json
import pathlib

import cv2
import numpy as np

SIDES = (160, 192, 224, 256, 288)


def find_box(model, img_bgr, sides=SIDES, canvas=1280, conf=0.25):
    """(box, method, conf) for one photo; box is [x, y, w, h] in img_bgr."""
    h, w = img_bgr.shape[:2]
    best = None
    for side in sides:
        s = side / max(h, w)
        small = cv2.resize(img_bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        pad = np.full((canvas, canvas, 3), 124, np.uint8)
        oy, ox = (canvas - small.shape[0]) // 2, (canvas - small.shape[1]) // 2
        pad[oy:oy + small.shape[0], ox:ox + small.shape[1]] = small
        r = model.predict(pad, imgsz=canvas, conf=conf, verbose=False)[0]
        for (x0, y0, x1, y1), c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
            x0, x1 = np.clip([(x0 - ox) / s, (x1 - ox) / s], 0, w)
            y0, y1 = np.clip([(y0 - oy) / s, (y1 - oy) / s], 0, h)
            central = 0.25 < (x0 + x1) / 2 / w < 0.75 and 0.2 < (y0 + y1) / 2 / h < 0.8
            if central and max(x1 - x0, y1 - y0) > 0.15 * max(h, w) and (best is None or c > best[1]):
                best = ([round(x0), round(y0), round(x1 - x0), round(y1 - y0)], float(c))
    if best:
        return best[0], "yolo", round(best[1], 3)
    return [round(0.2 * w), round(0.1 * h), round(0.6 * w), round(0.8 * h)], "center", ""


def sheet(photos, rows, path, height=260, cols=8):
    tiles = []
    for p, r in zip(photos, rows):
        img = cv2.imread(str(p))
        s = height / img.shape[0]
        t = cv2.resize(img, (round(img.shape[1] * s), height), interpolation=cv2.INTER_AREA)
        x, y, w, h = (round(v * s) for v in json.loads(r["bounding_box"]))
        cv2.rectangle(t, (x, y), (x + w, y + h), (255, 0, 255), 3)
        cv2.putText(t, f"{p.stem[4:]} {r['method']}", (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        tiles.append(t)
    width = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, 0, 0, width - t.shape[1] + 6, cv2.BORDER_CONSTANT, value=(230, 230, 230)) for t in tiles]
    tiles += [np.full_like(tiles[0], 230)] * (-len(tiles) % cols)
    cv2.imwrite(str(path), np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photos", type=pathlib.Path, required=True)
    ap.add_argument("--model", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--sheet", type=pathlib.Path, required=True)
    args = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(str(args.model))
    photos = sorted(args.photos.glob("IMG_*.jpeg"))
    manual = {}
    if args.out.exists():
        with open(args.out, encoding="utf-8", newline="") as f:
            manual = {r["photo"]: r for r in csv.DictReader(f) if r["method"] == "manual"}
    rows = []
    for p in photos:
        if p.name in manual:
            rows.append(manual[p.name])
            continue
        box, method, conf = find_box(model, cv2.imread(str(p)))
        rows.append(dict(photo=p.name, bounding_box=json.dumps(box, separators=(",", ":")), method=method, conf=conf))
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo", "bounding_box", "method", "conf"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    args.sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet(photos, rows, args.sheet)
    print(len(rows), "photos:", {m: sum(r["method"] == m for r in rows) for m in ("yolo", "center", "manual")})


if __name__ == "__main__":
    main()
