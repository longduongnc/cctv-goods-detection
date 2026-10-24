# HOANG-P05 — benchmark gọi tên SKU

Bộ chấm chung cho mọi model gọi tên SKU trên các hộp thật của 39 khung mẫu (plan HOANG-P05 trên Confluence, kế hoạch thực hiện ở `docs/superpowers/plans/2026-10-24-p05-transformer-bench.md`).

Code nằm ở đây; mọi thứ chạy trên máy GPU của long trong `~/Desktop/Datagent/arch_bench/`. Ảnh và model không vào repo.

## Đẩy code và lấy kết quả

```bash
export LONG_HOST=<ssh host của máy long>   # không ghi vào repo
tools/sync.sh push        # code, nhãn, test → arch_bench/
tools/sync.sh pull        # arch_bench/results/ → results/
```

## Venv riêng của bench

Không cài gì vào môi trường của long. Venv kế thừa torch 2.11.0+cu128 và timm 1.0.29 có sẵn trên máy, chỉ cài thêm gói trong `requirements.txt`; bản đã cài thật ghi trong `requirements.lock`.

```bash
cd ~/Desktop/Datagent/arch_bench
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -U -r requirements.txt
.venv/bin/pip freeze > requirements.lock
```

## Chạy test

```bash
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && .venv/bin/python -m pytest tests -q'
```

## Dữ liệu trên máy long

| Đường dẫn | Nội dung |
|---|---|
| `~/Desktop/Datagent/cv_output_sample/` | 39 khung mẫu (đã làm mờ mặt), `cv_output_units.csv` |
| `~/Desktop/Datagent/carton_recognition_greyfix/` | bản sửa lỗi `grey`, nhãn mù 164 hộp TH |
| `~/Desktop/Datagent/cctv_dataset/dataset_hard_types/` | ảnh mô phỏng |
| `arch_bench/data/iphone/` | 84 ảnh iPhone của 12 SKU và HILO (chép từ máy hoang) |
