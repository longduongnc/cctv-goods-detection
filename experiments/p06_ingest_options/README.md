# HOANG-P06 — so sánh phương án đưa dữ liệu từ tiệm lên cloud

Đo và tính cho plan HOANG-P06 trên Confluence. Kế hoạch thực hiện ở `docs/superpowers/plans/2026-10-27-p06-ingest-options.md`. Mọi giá và thông số nằm ở `inputs/sources.csv`, mỗi dòng có nguồn và ngày tra.

Phần tính toán chạy trên máy hoang. Phần cần ffmpeg, model hay clip (E1 video, E2, E4) chạy trên máy GPU của long, trong `~/Desktop/Datagent/ingest_bench/`. Ảnh và video không vào repo.

## Đẩy code, chạy job và lấy kết quả

```bash
export LONG_HOST=<ssh host của máy long>          # không ghi vào repo
tools/sync.sh push                                # code, inputs, test → ingest_bench/
tools/remote_job.sh NAME 'lệnh chạy trong ingest_bench/'   # systemd-run, 8 GB RAM, nice 10; log ở results/NAME.log
tools/sync.sh pull                                # ingest_bench/results/ → results/
```

## Venv trên máy long

Không cài gì vào môi trường của long. Venv kế thừa các gói có sẵn trên máy (kiểm 27/10: Python 3.12.3, numpy 2.3.5, OpenCV 4.10.0, ultralytics 8.4.47, torch 2.11.0+cu128) và chỉ cài thêm gói trong `requirements.txt`. `requirements.lock` chỉ ghim các gói cài trong venv (`--local`): `pip freeze` đầy đủ có cả đường dẫn tới dự án riêng của long, mà repo này public.

```bash
cd ~/Desktop/Datagent/ingest_bench
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip freeze --local > requirements.lock
```

## Chạy test

```bash
python -m pytest tests -q -m "not remote"                                                  # máy hoang
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/ingest_bench && .venv/bin/python -m pytest tests -q'   # máy long
```

## Dữ liệu trên máy long (chỉ đọc)

| Đường dẫn | Nội dung |
|---|---|
| `~/Desktop/Datagent/cv_output_sample/images/` | 39 khung thật, 1920×1080, đã làm mờ mặt |
| `~/Desktop/Datagent/challenge_videos/vid_milk/IMG_0798.MOV` … `IMG_0804.MOV` | 7 clip điện thoại gốc, HEVC 1080p, quay cầm tay |
| `~/Desktop/Datagent/carton_recognition/checked_videos_types/*.json` | kết quả từng khung của 10 clip |
| `~/Desktop/Datagent/yolo/yolo26s.pt`, `best_types.pt` | YOLO26s bản COCO gốc; YOLO 12 loại |
| `ingest_bench/data/merl/` | 3 clip MERL chép từ `media/` trong repo |
| `ingest_bench/data/models/` | model YuNet tìm mặt (tải từ opencv_zoo) |
