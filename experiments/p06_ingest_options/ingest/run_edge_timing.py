"""E2 on long's machine: milliseconds per frame for the box's filter step (person check, face blur, sharpness) and for
the current counting pipeline (cv_output.timed_units), on 4 CPU threads. Run it pinned to 4 CPUs:

    taskset -c 0-3 env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m ingest.run_edge_timing \
        --images ~/Desktop/Datagent/cv_output_sample/images --person-model ~/Desktop/Datagent/yolo/yolo26s.pt \
        --face-model data/models/face_detection_yunet_2023mar.onnx --datagent ~/Desktop/Datagent --out results/edge_timing_raw.csv
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import cv2

from ingest.edge_filter import blur_faces, configure_threads, sharpness

IMAGE_TYPES = (".jpg", ".jpeg", ".png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--person-model", type=Path, required=True, help="YOLO26s COCO weights")
    ap.add_argument("--face-model", type=Path, required=True, help="OpenCV YuNet ONNX")
    ap.add_argument("--datagent", type=Path, required=True, help="~/Desktop/Datagent, for carton_recognition and yolo/")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    configure_threads(4)
    from ultralytics import YOLO
    sys.path.insert(0, str(args.datagent / "carton_recognition"))
    import cv_output                                              # long's pipeline, read only

    person = YOLO(str(args.person_model))
    faces = cv2.FaceDetectorYN.create(str(args.face_model), "", (320, 320), 0.6)
    rec = cv_output.Recognizer(device="cpu", types=True)          # built as in cv_output.main()
    yolo = YOLO(str(args.datagent / "yolo" / "best_types.pt"))

    def filter_step(image):
        person.predict(image, classes=[0], imgsz=640, conf=0.4, device="cpu", verbose=False)
        blur_faces(image, faces)
        sharpness(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))

    paths = sorted(p for p in args.images.iterdir() if p.suffix.lower() in IMAGE_TYPES)
    warm = cv2.imread(str(paths[0]))
    filter_step(warm.copy())                                      # first calls load the models; keep them out of the timing
    cv_output.timed_units(warm, yolo, rec, 0.25, 1280)
    rows = []
    for p in paths:
        image = cv2.imread(str(p))
        start = time.perf_counter()
        filter_step(image.copy())
        rows.append(dict(image=p.name, step="filter", ms=round((time.perf_counter() - start) * 1000, 2)))
        _, ms = cv_output.timed_units(image, yolo, rec, 0.25, 1280)
        rows.append(dict(image=p.name, step="count", ms=round(ms, 2)))
        print(p.name, rows[-2]["ms"], rows[-1]["ms"], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "step", "ms"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
