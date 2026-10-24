# HOANG-P05 — Benchmark kiến trúc transformer cho bước gọi tên SKU: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một bộ benchmark chấm mọi model gọi tên SKU trên cùng các hộp thật của 39 khung mẫu, cho ra bảng 6 chỉ số của P05 (kèm khoảng tin cậy và McNemar so với mốc).

**Architecture:** Code nằm trong repo ở `experiments/p05_transformer_bench/`, được đẩy sang máy GPU của long (`~/Desktop/Datagent/arch_bench/`) để chạy. Mọi model nhận cùng một hàm cắt hộp (`crop_unit`), trả về vector đã chuẩn hoá, rồi gọi tên SKU bằng kNN trên một kho ảnh mẫu. Ngưỡng loại hàng lạ đặt trên ảnh mô phỏng. Kết quả từng hộp được lưu, để `report.py` tính Wilson và McNemar.

**Tech Stack:** Python 3.12.3, torch 2.11.0+cu128, timm 1.0.29, numpy 2.3.5, OpenCV 4.10.0, lancedb 0.40.0 (đã có trên máy long); `transformers` bản mới có `Siglip2Model` và `Qwen2_5_VLForConditionalGeneration`, `accelerate`, `pytest`, `huggingface_hub` cài vào venv riêng của bench.

**Spec:** [HOANG-P05](https://traditional-milk.atlassian.net/wiki/spaces/~7120204f8c1fdfbeb646c882494b9ab507ea3f/pages/12255234) (Confluence content id `12255234`, trạng thái `approved` 24/10).

## Global Constraints

Chép nguyên văn từ P05 và quy tắc dự án; mọi task đều phải tuân theo:

- "Không train trên ảnh kiểm."
- "Ảnh thô không đưa lên Confluence hay repo (mục 9 Claude rule)."
- "Thư mục riêng `~/Desktop/Datagent/arch_bench/`; không sửa `carton_recognition/`, `yolo/` hay model đang dùng."
- "Mỗi job chạy bằng `systemd-run --user`, giới hạn RAM, nice 10, OOMScoreAdjust 1000 (thiếu RAM thì job của mình bị dừng trước job của long). Crop lớn ghi ra đĩa (memmap) như lần sửa `grey` ngày 24/10."
- "Job dài hơn 30 phút ghi vào `document_vault/RESOURCES.md`."
- "Model tải về cache Hugging Face trên máy long."
- "Code và CSV kết quả commit vào `experiments/p05_transformer_bench/` trong repo (như P04); không có ảnh."
- "ngưỡng chấp nhận đặt trên ảnh mô phỏng sao cho giữ 99% hộp thật (cách của `evaluate.py`). Không đặt ngưỡng trên bộ kiểm."
- "fine-tune bằng công thức hiện tại đã sửa `grey`, cùng dữ liệu (239.920 crop), cùng 10 epoch"
- "bỏ 3 SKU khỏi dữ liệu fine-tune — TH-02 (cặp khó), VNM-09 (nhóm Sữa hạt), VNM-05 (dễ)"
- "Theo cỡ hộp: dưới 40, 40–60, 60–90, trên 90 px."
- "Mỗi tỷ lệ kèm khoảng tin cậy 95% (Wilson). Hai model so trên cùng các hộp bằng kiểm định McNemar; "hơn rõ" nghĩa là p < 0,05 ở chỉ số 1."
- Repo public: "Không ghi IP, hostname, tên tài khoản, hay bất cứ thứ gì dùng để vào máy vào các file trong repo." Máy long được gọi qua biến môi trường `LONG_HOST`.
- Mốc giờ trên Confluence và recap: "lấy giờ từ đồng hồ hệ thống tại đúng thời điểm ghi (chạy `date`)", dạng `YYYY-MM-DD HH:MM +07:00`.
- Commit message không có dòng `Co-Authored-By` hay `Generated with` (ý của hoang).

## Review Focus

Những điều spec ngầm đòi hỏi mà dễ hỏng âm thầm. Mỗi dòng có test ở task sở hữu:

1. **Thứ tự kênh màu.** `cv2` đọc BGR, model Hugging Face cần RGB; đảo sai thì mọi model kém đi mà không báo lỗi. Test ở Task 2.
2. **Định dạng khung.** `bounding_box` trong CSV là `[x, y, w, h]`, không phải `[x0, y0, x1, y1]`. Test ở Task 2.
3. **Ánh xạ mã SKU.** Tên loại của dataset (`vinamilk_banana`…), mã `TMP-MLK-…` và nhãn tay (CĐ, ÍĐ, VNM-05…) phải khớp `SKUS` trong `carton_recognition/cv_output.py`; lệch một dòng là sai cả bảng. Test ở Task 1.
4. **Hộp không có câu trả lời** (kNN ra `none`, dưới ngưỡng, VLM nói "KHÔNG CHẮC") phải tính là sai ở chỉ số 1, không được bỏ khỏi mẫu số. Test ở Task 6 và Task 8.
5. **Job bị dừng giữa chừng** trên máy dùng chung (OOM, long khởi động lại máy). Chạy lại phải bỏ qua các dòng (encoder, kho) đã có kết quả. Test ở Task 6.

Thêm một điều về rò rỉ: VLM chỉ được biết nhóm ứng viên từ dự đoán của YOLO, không từ nhãn. Test ở Task 8.

---

## Bối cảnh cho người thực hiện

- **Hai máy.** Repo nằm trên máy hoang (Windows, Git Bash): `cctv-goods-detection/`, nhánh `docs/vault-and-recap-skill`. Mọi thứ chạy trên máy GPU của long (Ubuntu, RTX 5090 32 GB, 125 GB RAM, thường chỉ còn khoảng 35 GB trống vì long chạy máy ảo và job optuna). Gọi lệnh bằng `ssh "$LONG_HOST" '<lệnh>'`.
- **Thứ có sẵn trên máy long** (chỉ đọc, không sửa):
  - `~/Desktop/Datagent/cv_output_sample/`: `images/` (39 khung, đã làm mờ mặt), `cv_output.csv`, `cv_output_units.csv` (495 hộp: `capture_id`, `bounding_box` dạng `[x,y,w,h]`, `detector_sku_id`, `database_sku_id`…).
  - `~/Desktop/Datagent/carton_recognition_greyfix/`: `th_labels_2026-10-24.csv` (164 hộp TH đã gán nhãn), `train_embedder.py` và `data.py` đã sửa (có memmap qua `CROPS_MEMMAP_DIR`), `embedder_types.pt` và `db_types/` của bản sửa `grey`, `cv_output_greyfix/cv_output_units.csv`.
  - `~/Desktop/Datagent/carton_recognition/`: code và model của long (`embedder.py` có `CartonNet`, `crop_box`; `data.py` có `sample_objects`, `background_boxes`, `other_cartons`, `reference_views`; `cv_output.py` có `SKUS`).
  - `~/Desktop/Datagent/cctv_dataset/dataset_hard_types/`: ảnh mô phỏng, `meta/objects.csv`, `meta/others.csv`, split `train` / `val`; `carton_renderer.py`, `build_dataset.py` (`CLASSES`, `MODELS`).
  - `~/Desktop/Datagent/yolo/best_types.pt`.
- **Trên máy hoang:** 84 ảnh iPhone ở `D:\Milkkkk-20261013T075004Z-1-001\Milkkkk\`; texture mặt trước ở `C:\Users\huyho\OneDrive\Desktop\blender\milk_resource\<Folder>\front.png` (riêng TH_ID là `left.png`).
- **Quy trình nhãn mù** đã dùng cho 164 hộp TH (24/10). Mỗi hộp mang mã ngẫu nhiên; tấm ảnh có ảnh ngữ cảnh, ảnh cắt sát và ảnh tăng tương phản, kèm ảnh mẫu thu nhỏ; nhãn có mức chắc `chắc / khá / thấp`. Gán xong mới mở bảng nối mã với dự đoán. Script gốc: `make_sheets.py` trong thư mục tạm của phiên 24/10, chuyển vào repo ở Task 3.

## File Structure

```
experiments/p05_transformer_bench/
  README.md               cách đẩy code, chạy job, chỗ để dữ liệu (không có IP)
  requirements.txt        gói thêm cho venv bench; requirements.lock = pip freeze sau khi cài
  tools/sync.sh           push: đẩy code sang máy long; pull: lấy results/ về
  tools/make_label_sheets.py   tấm ảnh nhãn mù (từ script 24/10)
  tools/iphone_boxes.py   tìm khung hộp trong 84 ảnh iPhone
  labels/                 th_labels_2026-10-24.csv, vnm_labels_*.csv, iphone_photos.csv, iphone_boxes.csv
  bench/skus.py           mã SKU, tên, nhóm, chuẩn hoá nhãn
  bench/stats.py          Wilson, McNemar, nhóm cỡ hộp
  bench/testset.py        Unit, đọc nhãn, cắt hộp
  bench/gallery.py        kho ảnh mẫu: render, iPhone, kho kiểu build_db
  bench/encoders.py       wrapper encoder (zero-shot và fine-tune)
  bench/knn.py            gọi tên bằng kNN có phiếu "none"
  bench/calibrate.py      tập val mô phỏng, ngưỡng 99%
  bench/licenses.py       license lấy từ model card
  bench/metrics.py        chỉ số từng nhóm
  bench/run_zeroshot.py   bước 1 (và chấm checkpoint fine-tune)
  bench/finetune.py       bước 2
  bench/vlm.py, bench/run_vlm.py   bước 3
  bench/report.py         bảng tổng hợp
  results/                CSV, preds/, summary.md
  tests/
```

---

### Task 1: Khung bench, venv và bảng SKU

**Files:**
- Create: `experiments/p05_transformer_bench/README.md`, `requirements.txt`, `tools/sync.sh`, `bench/__init__.py`, `bench/skus.py`, `bench/stats.py`
- Test: `tests/test_skus.py`, `tests/test_stats.py`

**Interfaces:**
- Produces: `skus.SKU_CODES: tuple[str, ...]` (12 mã, thứ tự VNM-01…10, TH-01, TH-02); `skus.KIND_TO_SKU: dict[str, str]`; `skus.NAME_VI: dict[str, str]` (tên in trên bao bì, lấy từ `SKUS`); `skus.TH_PAIR = ("TMP-MLK-TH-01", "TMP-MLK-TH-02")`; `skus.SUA_HAT = ("TMP-MLK-VNM-07", "TMP-MLK-VNM-08", "TMP-MLK-VNM-09", "TMP-MLK-VNM-10")`; `skus.HOLDOUT = ("TMP-MLK-TH-02", "TMP-MLK-VNM-09", "TMP-MLK-VNM-05")`; `skus.HILO = "TMP-MLK-TH-HILO"`; `skus.normalize_label(raw: str) -> str` (trả về mã SKU, hoặc `"NEG"`, `"AMBIG"`, `"SKIP"`).
- Produces: `stats.wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]`; `stats.mcnemar_exact(b: int, c: int) -> float` (hai phía, nhị thức chính xác); `stats.height_bin(h: int) -> str` trả về một trong `"<40"`, `"40–60"`, `"60–90"`, `"≥90"`.

- [ ] **Step 1: Viết `tools/sync.sh`.** `push` đóng gói thư mục bench (trừ `results/`, `.venv/`) bằng `tar` rồi giải nén qua `ssh "$LONG_HOST"` vào `~/Desktop/Datagent/arch_bench/`; `pull` chép `arch_bench/results/` về. Không dùng `rsync` vì Git Bash không có. Chạy `tools/sync.sh push`, rồi `ssh "$LONG_HOST" 'ls ~/Desktop/Datagent/arch_bench'` phải thấy `bench/ tools/ tests/`.

- [ ] **Step 2: Tạo venv bench trên máy long, không đụng môi trường của long.**

```bash
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && python3 -m venv --system-site-packages .venv && .venv/bin/pip install -U transformers accelerate pytest huggingface_hub qwen-vl-utils && .venv/bin/pip freeze > requirements.lock'
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && .venv/bin/python -c "import torch, timm; from transformers import Siglip2Model, Qwen2_5_VLForConditionalGeneration; print(torch.__version__, torch.cuda.is_available(), timm.__version__)"; python3 -c "import transformers; print(transformers.__version__)"'
```

Expected: `2.11.0+cu128 True 1.0.29`, sau đó `4.46.3`. Dòng thứ hai là `transformers` của long, phải giữ nguyên. Nếu venv không thấy torch thì cài torch cu128 từ index của PyTorch vào venv và ghi lại vào README.

- [ ] **Step 3: Viết test fail.** `test_skus.py`:
  - `KIND_TO_SKU` bằng ánh xạ đọc từ `~/Desktop/Datagent/carton_recognition/cv_output.py` bằng `ast` (lấy literal `SKUS`, không import file).
  - `normalize_label`: `"CĐ"` → `"TMP-MLK-TH-01"`; `"ÍĐ"` → `"TMP-MLK-TH-02"`; `"VNM-09"` → `"TMP-MLK-VNM-09"`; `"TMP-MLK-VNM-05"` → chính nó; `"TH-khác"` và `"khác"` → `"NEG"`; `"?"` → `"AMBIG"`; `"x"` và `"lệch"` → `"SKIP"`; giá trị lạ → `ValueError`.
  - `len(SKU_CODES) == 12`; `HOLDOUT` đúng như trên.

  `test_stats.py`:
  - `wilson(114, 164)` làm tròn 3 số → `(0.621, 0.760)`; `wilson(0, 10)[0] == 0.0`.
  - `round(mcnemar_exact(14, 6), 3) == 0.115`; `mcnemar_exact(0, 0) == 1.0`.
  - `height_bin`: 39 → `"<40"`, 40 → `"40–60"`, 59 → `"40–60"`, 60 → `"60–90"`, 89 → `"60–90"`, 90 → `"≥90"`.

- [ ] **Step 4: Chạy để thấy fail.** `tools/sync.sh push && ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && .venv/bin/python -m pytest tests/test_skus.py tests/test_stats.py -q'` → báo lỗi import (`bench.skus` chưa có).

- [ ] **Step 5: Viết `bench/skus.py` và `bench/stats.py`** theo các interface trên. `NAME_VI` lấy chuỗi tên tiếng Việt từ `SKUS` của `cv_output.py`, chép vào file (không import lúc chạy).

- [ ] **Step 6: Chạy lại test.** Cùng lệnh → `PASS`.

- [ ] **Step 7: Commit.** `git add experiments/p05_transformer_bench && git commit -m "P05: khung bench, venv, bang SKU va thong ke"`

---

### Task 2: Bộ kiểm — đọc nhãn và cắt hộp

**Files:**
- Create: `bench/testset.py`, `labels/th_labels_2026-10-24.csv` (chép từ `carton_recognition_greyfix/`)
- Test: `tests/test_testset.py`

**Interfaces:**
- Consumes: `skus.normalize_label`.
- Produces: `@dataclass(frozen=True) class Unit: uid: str; image: str; capture_id: str; box: tuple[int, int, int, int]  # x, y, w, h; store: str; label: str; confidence: str; yolo_sku: str; db_old_sku: str | None; db_fixed_sku: str | None`.
- Produces: `load_units(paths: list[Path]) -> list[Unit]` (đọc CSV dạng `th_labels_2026-10-24.csv`, `utf-8-sig`; `store` lấy từ tên ảnh, ví dụ `PHONE-S01-A_…` → `S01`); `scored(units, confident_only: bool = True) -> list[Unit]` (nhãn là mã SKU; nếu `confident_only` thì mức chắc là `khá` hoặc `chắc`); `negatives(units) -> list[Unit]` (nhãn `NEG`); `read_frame(sample_dir: Path, image: str) -> np.ndarray` (BGR); `crop_unit(img_bgr: np.ndarray, box: tuple[int, int, int, int], size: int = 384) -> np.ndarray` (RGB uint8 `(size, size, 3)`; lề 6% của cạnh dài, đặt vào hình vuông nền xám 124, `INTER_AREA` khi thu nhỏ, `INTER_CUBIC` khi phóng to — giống `embedder.crop_box`, khác ở chỗ trả RGB).

- [ ] **Step 1: Viết test fail.**
  - `load_units([th])` trả 164 hộp; `len(scored(units)) == 37`; mọi nhãn trong `scored` thuộc `TH_PAIR`; `len(negatives(units)) == 16`.
  - Kênh màu: ảnh `np.zeros((100, 200, 3), uint8)`, vùng `x=10..29, y=20..59` đặt BGR `(255, 0, 0)`; `out = crop_unit(img, (10, 20, 20, 40), size=64)` → `out.shape == (64, 64, 3)`, `out[32, 32].tolist() == [0, 0, 255]` (xanh dương ở RGB), `out[32, 2].tolist() == [124, 124, 124]` (dải xám hai bên vì hộp đứng).
  - Định dạng khung: với ảnh trên, `crop_unit(img, (10, 20, 20, 40))` có hơn 80% điểm ảnh ngoài dải xám là màu xanh dương. Nếu hiểu nhầm `[x0, y0, x1, y1]` thì test này fail.
- [ ] **Step 2: Chạy để thấy fail.** `ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && .venv/bin/python -m pytest tests/test_testset.py -q'` → lỗi import.
- [ ] **Step 3: Viết `bench/testset.py`.**
- [ ] **Step 4: Chạy lại test → PASS.**
- [ ] **Step 5: Commit.** `git commit -m "P05: doc nhan va cat hop"`

---

### Task 3: Gán nhãn mù 331 hộp Vinamilk

**Files:**
- Create: `tools/make_label_sheets.py`, `labels/vnm_labels_<YYYY-MM-DD>.csv`, `labels/vnm_recheck_<YYYY-MM-DD>.csv`
- Test: `tests/test_labels_complete.py`

**Interfaces:**
- Consumes: `testset.load_units`, `testset.crop_unit`.
- Produces: file nhãn VNM cùng cột với `th_labels_2026-10-24.csv` (`id, image_filename, capture_id, bounding_box, label, confidence, note, yolo_sku_id, db_old_sku_id, db_fixed_sku_id`). Nhãn thô hợp lệ: `VNM-01` … `VNM-10`, `CĐ`, `ÍĐ`, `TH-khác`, `khác`, `?`, `x`, `lệch`.

- [ ] **Step 1: Viết test fail.**
  - Mỗi hộp trong `cv_output_units.csv` (mẫu của long) có `detector_sku_id` bắt đầu bằng `TMP-MLK-VNM` xuất hiện đúng một lần trong file VNM (331 dòng). Mỗi hộp TH xuất hiện đúng một lần trong file TH. Khoá là `(capture_id, bounding_box)`.
  - Mọi nhãn thô hợp lệ; mức chắc thuộc `{"chắc", "khá", "thấp", ""}`.
  - File recheck có ít nhất 33 dòng.
- [ ] **Step 2: Chạy để thấy fail** (thiếu file).
- [ ] **Step 3: Đưa `make_sheets.py` của phiên 24/10 vào `tools/make_label_sheets.py`.** Thêm tham số `--brand VNM|TH`. Dải ảnh mẫu VNM lấy `front.png` của 10 thư mục Vinamilk trong `blender/milk_resource` (EST=VNM-01, Blue=02, Green=03, Chocolate=04, Bannana=05, Orange=06, Bean=07, HN=08, Grey=09, Seed9=10), thu về cao 60 px rồi phóng lên.
- [ ] **Step 4: Chép tạm 39 khung về thư mục tạm của phiên.** Tạo tấm ảnh, gán nhãn cả 331 hộp theo đúng quy trình nhãn mù của TH.
- [ ] **Step 5: Kiểm lần hai.** Gán lại 33 hộp ngẫu nhiên (không lấy hộp `x`), mã mới, chỉ ảnh cắt. Hộp nào hai lần khác nhau thì đổi thành `?`, riêng khung vắt hai sản phẩm thì đổi thành `lệch`. Ghi tỷ lệ trùng vào note đầu file recheck.
- [ ] **Step 6: Nối với bảng mã và dự đoán.** Nối từ `cv_output_units.csv` của long và của bản greyfix, ra file VNM đủ cột. Xoá các khung đã chép tạm.
- [ ] **Step 7: Chạy test → PASS.**
- [ ] **Step 8: Commit** file nhãn và tool: `git commit -m "P05: nhan mu 331 hop Vinamilk"`

---

### Task 4: Kho ảnh mẫu — render và iPhone

**Files:**
- Create: `bench/gallery.py`, `tools/iphone_boxes.py`, `labels/iphone_photos.csv`, `labels/iphone_boxes.csv`
- Test: `tests/test_gallery.py`

**Interfaces:**
- Consumes: `testset.crop_unit`, `skus.KIND_TO_SKU`, `skus.HILO`.
- Produces: `@dataclass class Gallery: name: str; crops: np.ndarray  # (n, 384, 384, 3) uint8 RGB, có thể là memmap; sku: np.ndarray  # str, "none" cho mẫu âm; source: np.ndarray  # str`.
- Produces: `render_gallery(per_kind: int = 160, seed: int = 7, height: int = 170, size: int = 384) -> Gallery`. Tư thế và seed giống hệt `carton_recognition/data.reference_views(per_kind=160)`; chỉ khác cỡ ảnh cắt. Renderer import từ `../cctv_dataset`.
- Produces: `iphone_gallery(faces: set[str] | None, include_hilo: bool) -> Gallery` (`faces=None` lấy cả 6 mặt; `{"front"}` chỉ lấy mặt trước); `save_gallery(g, path)`, `load_gallery(path) -> Gallery` (`.npz` và `.npy` memmap).

- [ ] **Step 1: Chép 84 ảnh iPhone sang `arch_bench/data/iphone/`** bằng `scp`. Ảnh này không vào repo.
- [ ] **Step 2: Viết `labels/iphone_photos.csv`** (`photo, sku, face`), xem ảnh nhỏ để điền mặt (`front/back/left/right/top/bottom`). Theo ảnh nhỏ ngày 24/10, các nhóm là *(cần kiểm bằng mắt)*:
  - 0624–0630 VNM-01 · 0631–0636 VNM-02 · 0637–0642 VNM-03 · 0643–0648 VNM-04 · 0649–0654 VNM-05 · 0655–0660 VNM-06
  - 0661–0666 VNM-07 · 0667–0672 VNM-10 · 0673–0678 VNM-08 · 0679–0684 VNM-09
  - 0685–0690 TH-01 · 0691–0696 TH-02 · 0697–0708 HILO

  Ảnh 0628 không có.
- [ ] **Step 3: Viết `tools/iphone_boxes.py`.** Chạy `yolo/best_types.pt` trên ảnh thu về cạnh dài 1280, `conf=0.25`, lấy khung lớn nhất. Không có khung nào thì lấy vùng giữa (20–80% chiều ngang, 10–90% chiều dọc), cột `method` ghi `yolo` hoặc `center`. Làm một tấm ảnh nhỏ tổng hợp để soát; khung nào sai thì sửa tay và ghi `method=manual`.
- [ ] **Step 4: Viết test fail.**
  - `render_gallery(per_kind=2)`: 24 ảnh, 12 mã SKU khác nhau, `crops.shape == (24, 384, 384, 3)`.
  - `iphone_photos.csv` có 84 dòng và 13 mã; mỗi mã có đúng một dòng `face == "front"`.
  - `iphone_gallery({"front"}, include_hilo=False)` có 12 ảnh; `include_hilo=True` có 13 ảnh.
- [ ] **Step 5: Chạy để thấy fail → viết `bench/gallery.py` → chạy lại → PASS.**
- [ ] **Step 6: Commit** (chỉ CSV và code): `git commit -m "P05: kho anh mau render va iPhone"`

---

### Task 5: Encoder, kNN và ngưỡng

**Files:**
- Create: `bench/encoders.py`, `bench/knn.py`, `bench/calibrate.py`, `bench/licenses.py`
- Test: `tests/test_encoders.py`, `tests/test_knn.py`, `tests/test_calibrate.py`

**Interfaces:**
- Produces: giao thức `Encoder` với `name: str`, `embed(crops: np.ndarray) -> np.ndarray`. Đầu vào uint8 RGB `(n, S, S, 3)`; đầu ra float32 `(n, d)` đã chuẩn hoá L2; chia lô 64; dùng fp16 autocast trên CUDA.
- Produces: `make_encoder(name: str, device: str) -> Encoder` với các tên:

  | Tên | Model | Pooling |
  |---|---|---|
  | `dinov2_s`, `dinov2_b`, `dinov2_l` | timm `vit_{small,base,large}_patch14_reg4_dinov2.lvd142m`, `img_size=224` | nối CLS với trung bình token patch (giống `CartonNet`, bỏ lớp chiếu) |
  | `siglip2_b` | `google/siglip2-base-patch16-224` | `get_image_features` |
  | `siglip2_so400m` | `google/siglip2-so400m-patch14-384` | `get_image_features` |
  | `clip_l` | `openai/clip-vit-large-patch14` | `get_image_features` |
  | `long_ft` | `carton_recognition/embedder_types.pt` | `CartonNet` |
  | `greyfix_ft` | `carton_recognition_greyfix/embedder_types.pt` | `CartonNet` |
  | `ft:<đường dẫn>` | checkpoint của Task 7 | theo checkpoint |

- Produces: `knn_predict(q: np.ndarray, g: np.ndarray, g_sku: np.ndarray, k: int = 10) -> tuple[np.ndarray, np.ndarray]` trả về `(pred, top1)`. Phiếu của k láng giềng được cân theo độ tương đồng (cắt dưới ở 0), giống `recognize.lookup`. Nếu tổng phiếu `"none"` ≥ phiếu của SKU thắng thì `pred` là `None`. `top1` là độ tương đồng cao nhất với một mẫu không phải `none`.
- Produces: `synthetic_val(per_kind: int = 2000, seed: int = 11) -> tuple[np.ndarray, np.ndarray]`. Crop lấy từ split `val` của `dataset_hard_types` bằng `data.sample_objects(..., per_kind=True)` và `testset.crop_unit`, cùng mẫu với `evaluate.py --types`.
- Produces: `synthetic_threshold(top1_pos: np.ndarray, keep: float = 0.99) -> float` bằng `np.quantile(top1_pos, 1 - keep)`.
- Produces: `license_of(hf_id: str) -> str`, đọc `huggingface_hub.model_info(hf_id).card_data.license` và lưu đệm vào `results/licenses.json`.

- [ ] **Step 1: Viết test fail.**
  - `test_encoders.py` (đánh dấu `gpu`, chạy cho mọi tên trừ `ft:`): `embed` 4 crop ngẫu nhiên cố định seed cho ra shape `(4, d)`, dtype float32, chuẩn L2 lệch 1 không quá `1e-3`. Gọi hai lần trên cùng đầu vào thì chênh lệch tuyệt đối lớn nhất nhỏ hơn `1e-3`.
  - `test_knn.py`: kho `[e1→"A", e2→"B", e2→"B"]`; truy vấn `e2` cho `pred == "B"`, `top1 == 1.0`. Truy vấn `(e1 + e2)/√2` với `k=3` cho `"B"`. Kho có 2 vector `"none"` trùng truy vấn và 1 vector `"A"` xa hơn thì `pred` là `None`.
  - `test_calibrate.py`: `synthetic_threshold(np.linspace(0, 1, 101)) == pytest.approx(0.01)`.
- [ ] **Step 2: Chạy để thấy fail → viết code → chạy lại → PASS.** Lần đầu sẽ tải model về cache HF trên máy long (khoảng vài GB).
- [ ] **Step 3: Commit.** `git commit -m "P05: encoder, kNN, nguong mo phong"`

---

### Task 6: Bước 1 — encoder nguyên bản và các mốc

**Files:**
- Create: `bench/metrics.py`, `bench/run_zeroshot.py`, `results/zeroshot.csv`, `results/preds/<encoder>__<kho>.csv`
- Test: `tests/test_metrics.py`, `tests/test_run_zeroshot.py`

**Interfaces:**
- Consumes: Task 1–5.
- Produces: `unit_report(units: list[Unit], pred: dict[str, str | None]) -> dict`. Kết quả gồm `acc` dạng `(k, n, lo, hi)`, `th_pair`, `sua_hat`, `by_height` (theo `height_bin`), và `neg_rejected` nếu có mẫu âm. Dự đoán `None` hoặc thiếu tính là sai.
- Produces: CLI `run_zeroshot.py --encoders <tên,…> --galleries renders,iphone_all,iphone_front --out results/zeroshot.csv`. Mỗi cặp (encoder, kho) ghi một dòng gồm: số liệu `unit_report` trên `scored(confident_only=True)`; tỷ lệ mẫu âm bị loại ở ngưỡng mô phỏng; tỷ lệ hộp thật được nhận ở cùng ngưỡng; `threshold`; `ms_gpu` (trung vị mỗi crop, lô 64, bỏ lô đầu); `ms_cpu` (100 crop, lô 16, `torch.set_num_threads(8)`); `license`; hai cột HILO (`hilo_reject_before`: ảnh HILO bị loại hoặc bị gọi khác TH-01/02 khi kho chưa có HILO; `hilo_acc_after`: thêm 6 ảnh HILO 0697–0702 vào kho, truy vấn bằng 0703–0708). Dự đoán từng hộp ghi vào `results/preds/`. Cặp đã có dòng trong `--out` thì bỏ qua.
- Tên kho trong `--galleries`: `renders` → `render_gallery()`; `iphone_all` → `iphone_gallery(None, include_hilo=False)`; `iphone_front` → `iphone_gallery({"front"}, include_hilo=False)`; `db` → `db_gallery(())`; `db_holdout` → `db_gallery(HOLDOUT)` (hai kho cuối có từ Task 7).
- Ba mốc của pipeline đang chạy lấy thẳng từ cột nhãn, không chạy model: `yolo` (`yolo_sku_id`), `db_long` (`db_old_sku_id`), `db_greyfix` (`db_fixed_sku_id`).

- [ ] **Step 1: Viết test fail.**
  - `unit_report`: hộp nhãn TH-01 được đếm vào `th_pair`; hộp cao 40 px vào nhóm `40–60`; `pred=None` làm `k` giảm nhưng `n` giữ nguyên.
  - `test_run_zeroshot.py`: với file CSV tạm đã có dòng `dinov2_s,renders`, hàm `pending_pairs(["dinov2_s"], ["renders", "iphone_all"], csv)` chỉ trả `[("dinov2_s", "iphone_all")]`.
- [ ] **Step 2: Chạy để thấy fail → viết code → chạy lại → PASS.**
- [ ] **Step 3: Chạy job trên máy long.** Lấy giờ bằng `date`; nếu ước tính quá 30 phút thì ghi dòng vào `RESOURCES.md`.

```bash
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/arch_bench && systemd-run --user --unit=p05-zeroshot --collect -p MemoryMax=20G -p OOMScoreAdjust=1000 -p Nice=10 -p WorkingDirectory=$PWD --setenv=PATH="$PATH" /bin/bash -c ".venv/bin/python -m bench.run_zeroshot --encoders dinov2_s,dinov2_b,dinov2_l,siglip2_b,siglip2_so400m,clip_l,long_ft,greyfix_ft --galleries renders,iphone_all,iphone_front --out results/zeroshot.csv > results/zeroshot.log 2>&1"'
```

Expected: `results/zeroshot.csv` có 8 × 3 = 24 dòng, cộng 3 dòng mốc.
- [ ] **Step 4: Lấy kết quả về** (`tools/sync.sh pull`) và gửi hoang bảng chỉ số 1 kèm khoảng tin cậy. **Chọn 2–3 encoder để fine-tune:** xếp theo chỉ số 1 trên kho `renders`, hoà thì xét cặp TH, không lấy model có license cấm thương mại. Ghi lựa chọn vào Nhật ký P05 (mốc giờ lấy bằng `date`).
- [ ] **Step 5: Commit** code và `results/`: `git commit -m "P05: buoc 1 encoder nguyen ban"`

---

### Task 7: Bước 2 — fine-tune và bài SKU mới

**Files:**
- Create: `bench/finetune.py`, `results/finetune.csv`
- Modify: `bench/encoders.py` (thêm nạp `ft:<đường dẫn>`), `bench/gallery.py` (thêm `db_gallery`)
- Test: `tests/test_finetune.py`

**Interfaces:**
- Produces: `train(backbone: str, holdout: tuple[str, ...], epochs: int = 10, out_dir: Path) -> Path`. Trả về đường dẫn checkpoint `embedder.pt` trong cùng định dạng với `train_embedder.py`, có thêm khoá `backbone_kind` (`"timm"` hoặc `"hf"`).
- Produces: `db_gallery(holdout: tuple[str, ...]) -> Gallery`. Ghép ảnh mẫu render, 60.000 crop dataset (`per_kind`, seed 101), 15.000 khung nền (seed 103) và 20.000 hộp hãng khác (seed 105, gán `"none"`), giống `build_db.py --types`. Crop dataset của các SKU trong `holdout` bị bỏ, nên những SKU đó chỉ còn ảnh mẫu. Dùng memmap.
- **Công thức (cố định):** giống `carton_recognition_greyfix/train_embedder.py --types`:
  - loss CosFace `s=30`, `m=0.3`; AdamW `weight_decay=0.05`; lr backbone `3e-5`, đầu chiếu và tâm lớp `9e-4`;
  - khởi động 300 bước, sau đó cosine giảm về 2% trên tổng số bước của **10 epoch** (không theo thời gian);
  - lô 192, nếu tràn VRAM thì micro-batch 96 × 2 bước tích luỹ;
  - augmentation dùng `to_input(..., grey=0.0)` của bản đã sửa;
  - dữ liệu: 168.000 hộp (`per_kind`, seed 1), 30.000 nền (seed 3), 40.000 hãng khác (seed 5), 1.920 ảnh mẫu; crop 224 ghi ra memmap qua `CROPS_MEMMAP_DIR`;
  - lớp chiếu: nối đặc trưng gộp với trung bình token → 768 → 256. Encoder HF dùng `pooler_output` làm đặc trưng gộp; SigLIP 2 so400m chạy ở 224 với `interpolate_pos_encoding=True`.
- **Bỏ SKU (`holdout`):** bỏ các SKU trong `HOLDOUT` khỏi crop train và khỏi ảnh mẫu dùng để train.

- [ ] **Step 1: Viết test fail.**
  - Smoke test trên CPU: `train("vit_tiny_patch16_224", (), epochs=1, ...)` với dataset giả 16 crop ngẫu nhiên (truyền qua tham số `_fake_rows` dành cho test) tạo ra file checkpoint. `make_encoder("ft:<path>", "cpu").embed(...)` trả shape `(n, 256)` đã chuẩn hoá.
  - Lọc SKU bỏ ra: hàm chọn mẫu `training_rows(rows, holdout=HOLDOUT)` không trả dòng nào có kind ánh xạ vào `HOLDOUT`.
  - `db_gallery(HOLDOUT)` không có crop `dataset` của SKU bỏ ra, nhưng vẫn có crop `reference` của chúng.
- [ ] **Step 2: Chạy để thấy fail → viết code → chạy lại → PASS.**
- [ ] **Step 3: Chạy job.** Mỗi encoder đã chọn chạy hai lần, `holdout=()` và `holdout=HOLDOUT`, nối tiếp nhau, mỗi lần một `systemd-run` (`MemoryMax=22G`, `Nice=10`, `OOMScoreAdjust=1000`). Trước mỗi lần ghi một dòng `RESOURCES.md`, giờ lấy bằng `date`.
- [ ] **Step 4: Chấm.** `run_zeroshot --encoders ft:<…> --galleries renders,db,db_holdout`. Bổ sung vào `results/finetune.csv`:
  - độ đúng trên hộp thật của 3 SKU bỏ ra (với checkpoint `holdout`);
  - độ đúng trên ảnh mô phỏng val của 3 SKU đó.

  Mỗi checkpoint ghi thêm thời gian train thực và số epoch.
- [ ] **Step 5: Commit** code và `results/`: `git commit -m "P05: buoc 2 fine-tune va bai SKU moi"`

---

### Task 8: Bước 3 — VLM ý kiến thứ hai

**Files:**
- Create: `bench/vlm.py`, `bench/run_vlm.py`, `results/vlm.csv`
- Test: `tests/test_vlm.py`

**Interfaces:**
- Produces: `candidates_for(unit: Unit) -> tuple[str, ...] | None`. Nếu `yolo_sku` thuộc `TH_PAIR` thì trả `TH_PAIR`, thuộc `SUA_HAT` thì trả `SUA_HAT`, còn lại `None`. **Không dùng `unit.label`.**
- Produces: `parse_answer(text: str, candidates: tuple[str, ...]) -> str | None`. So với `NAME_VI`, không phân biệt hoa thường và dấu. "KHÔNG CHẮC" hoặc tên không thuộc ứng viên thì trả `None`.
- Produces: `sku_from_ocr(text: str, candidates: tuple[str, ...]) -> str | None`. Từ khoá được bỏ dấu trước khi so, và xét theo thứ tự: `HANH NHAN`→VNM-08, `ME DEN`→VNM-09, `9 LOAI HAT`→VNM-10, `DAU NANH`→VNM-07, `IT DUONG`→TH-02, `CO DUONG`→TH-01. Kết quả chỉ được nhận nếu thuộc `candidates`.
- Produces: `QwenVL(model_id="Qwen/Qwen2.5-VL-7B-Instruct").choose(crop, candidates) -> tuple[str | None, str, float]` (SKU, câu trả lời gốc, ms); `Florence(model_id="microsoft/Florence-2-large").ocr(crop) -> tuple[str, float]` (task `<OCR>`).
- **Prompt cố định:** "Đây là ảnh cắt một hộp sữa trên kệ cửa hàng. Đây là sản phẩm nào trong danh sách sau? Trả lời đúng một dòng trong danh sách, hoặc KHÔNG CHẮC nếu không đọc được." rồi liệt kê tên `NAME_VI` của từng ứng viên, mỗi tên một dòng. Ảnh cắt được phóng sao cho cạnh ngắn ít nhất 448 px.

- [ ] **Step 1: Viết test fail.**
  - `candidates_for`: một hộp có `label="TMP-MLK-TH-02"`, `yolo_sku="TMP-MLK-VNM-03"` cho kết quả `None`.
  - `parse_answer("th true milk sữa tươi tiệt trùng ít đường 180ml", TH_PAIR) == "TMP-MLK-TH-02"`; `parse_answer("KHÔNG CHẮC", TH_PAIR) is None`.
  - `sku_from_ocr("SỮA HẠT ĐẬU NÀNH MÈ ĐEN", SUA_HAT) == "TMP-MLK-VNM-09"`; `sku_from_ocr("SỮA ĐẬU NÀNH CAO CANXI", SUA_HAT) == "TMP-MLK-VNM-07"`; `sku_from_ocr("TH true MILK ÍT ĐƯỜNG", TH_PAIR) == "TMP-MLK-TH-02"`.
- [ ] **Step 2: Chạy để thấy fail → viết code → chạy lại → PASS.**
- [ ] **Step 3: Chạy trên các hộp có nhãn chắc mà `candidates_for` khác `None`.** Trước khi chạy, kiểm còn ít nhất 20 GB VRAM trống (`nvidia-smi`). Nếu Florence-2 không nạp được với `transformers` của venv bench, bỏ Florence-2 và ghi vào Nhật ký P05.
- [ ] **Step 4: Ghi kết quả.** `results/vlm.csv` có các cột: model, n, số câu trả lời, số đúng trong các câu trả lời, độ đúng tính cả câu không trả lời là sai, ms mỗi crop. Ghi thêm `results/preds/vlm_*.csv`.
- [ ] **Step 5: Commit.** `git commit -m "P05: buoc 3 VLM y kien thu hai"`

---

### Task 9: Tổng hợp, research và cập nhật P05

**Files:**
- Create: `bench/report.py`, `results/summary.md`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `results/*.csv`, `results/preds/*.csv`, `stats.wilson`, `stats.mcnemar_exact`.
- Produces: `summarize(results_dir: Path) -> str`. Kết quả là markdown: một bảng 6 chỉ số cho mỗi model, mỗi tỷ lệ viết dạng `xx,x% (lo–hi)`; cột McNemar so với `yolo` và với `db_greyfix`, ghi `b`, `c`, `p`, và đánh dấu "hơn rõ" khi `p < 0,05`.

- [ ] **Step 1: Viết test fail.** Với hai file preds giả trên 5 hộp (A đúng 4, B đúng 2, hai bên khác nhau ở 3 hộp), bảng phải có `b` và `c` đúng, và chuỗi `80,0% (` cho A.
- [ ] **Step 2: Chạy để thấy fail → viết code → chạy lại → PASS.**
- [ ] **Step 3: Sinh `results/summary.md`, kéo về, commit.** `git commit -m "P05: bang tong hop"`
- [ ] **Step 4: Viết trang research trong Hoàng_Research** (folder `328026`).
  - Đọc trang "Cách dùng — Research" (`98546`) trước, theo đúng mẫu.
  - Bảng số lấy từ `summary.md`; mỗi số dẫn về file trong `experiments/p05_transformer_bench/results/`.
  - Thêm dòng vào bảng chỉ mục của trang Cách dùng — Research.
- [ ] **Step 5: Cập nhật P05.** Thêm dòng Nhật ký có link research. Đổi `status` theo bảng "Khi nào đóng plan": `done` nếu có model hơn rõ mốc ở chỉ số 1, ngược lại `closed-fail`. Cập nhật `updated` và dòng chỉ mục ở Cách dùng — RoadMap. Sửa theo local-id, chạy thử (dryRun) trước.
- [ ] **Step 6: Xoá các dòng giữ máy** của P05 trong `RESOURCES.md`, viết recap (skill `recap`), commit và push.
