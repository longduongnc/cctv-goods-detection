# HOANG-P06 — So sánh phương án đưa dữ liệu từ tiệm lên cloud: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một bộ script đo và tính, cho ra bảng chi phí 12 tuần và 12 tháng của các tổ hợp phương án (A–D) × camera × hộp cho 30 tiệm, kèm ba điều kiện G1–G3, và quyết định `done` / `closed-fail` theo đúng luật của P06.

**Architecture:** Code nằm ở `experiments/p06_ingest_options/` (gói `ingest`). Mọi giá và thông số đi qua một file có nguồn (`inputs/sources.csv`) và một hàm đọc có kiểm tra. Phần tính toán thuần (độ nét, dung lượng, rớt mạng, chi phí, quyết định) chạy và có test trên máy hoang. Phần cần ffmpeg, model và clip (E1 video, E2, E4) chạy trên máy long trong `~/Desktop/Datagent/ingest_bench/`. Mô hình chi phí dùng lại `estimate()` của P03 bằng cách nạp file `docs/architecture/cost_model.py`, không sửa file đó.

**Tech Stack:** Máy hoang: Python 3.10.11, numpy 1.26.4, OpenCV 4.13.0, pytest 9.0.3. Máy long: Python 3.12.3, numpy 2.3.5, OpenCV 4.10.0 (có `cv2.FaceDetectorYN`), ultralytics 8.4.47, ffmpeg 6.1.1 (libx264, libx265); pytest cài vào venv riêng.

**Spec:** [HOANG-P06](https://traditional-milk.atlassian.net/wiki/spaces/~7120204f8c1fdfbeb646c882494b9ab507ea3f/pages/12976131) (Confluence content id `12976131`, `approved` lúc 2026-10-27 12:46 +07:00).

## Global Constraints

Chép nguyên văn từ P06 và quy tắc dự án; mọi task đều phải tuân theo:

- "Mỗi giá có link và ngày tra. Quy đổi VND sang USD theo tỷ giá bán của Vietcombank ngày tra."
- "**G1 · Vừa gói 4G:** dung lượng gửi lên không quá 2 GB/ngày/tiệm (gói SD100), tính ở mức cao của khoảng ước lượng. Tiệm có WiFi không bị giới hạn này, nhưng thiết kế phải chạy được ở tiệm chỉ có 4G."
- "**G2 · Mặt người không rời tiệm:** P03 đã chốt làm mờ mặt trước khi ảnh rời tiệm (rủi ro R24–R26, Luật 91/2025)."
- "**G3 · Hộp đủ nét:** hộp sữa 180 ml cao ít nhất 60 px trên ảnh khi camera cách kệ 2 m."
- "**Cách quyết:** xếp các tổ hợp qua cả G1–G3 theo tổng 12 tháng. Tổ hợp trượt điều kiện vẫn ghi đủ số vào research, để Datagent thấy cái giá của từng điều kiện."
- "`done`: C (với ít nhất một hạng camera và một hộp) qua G1–G3, và tổng 12 tháng không quá 110% tổ hợp rẻ nhất cũng qua G1–G3 → đề xuất C kèm số." "`closed-fail`: C trượt một điều kiện, hoặc đắt hơn quá 10% → đề xuất tổ hợp thắng, ghi lý do."
- "Mọi hộp tính như chỉ có CPU, không dùng GPU hay NPU (cách tính thận trọng)."
- "**Máy long:** chỉ đọc clip, ảnh và model có sẵn. Job chạy bằng `systemd-run --user`, nice 10, giới hạn RAM, như P05. Job dài hơn 30 phút ghi vào `document_vault/RESOURCES.md`."
- "**Repo:** code và CSV kết quả vào `experiments/p06_ingest_options/`. Không có ảnh hay video của tiệm (mục 9 Claude rule)."
- "**Không làm:** mua thiết bị; dựng thử trên AWS; đổi model đếm; tính công người."
- "**Thất bại dù chạy được:** giá không có nguồn hoặc không ghi ngày tra; so các phương án với giả định khác nhau mà không ghi rõ; lấy số đo trên máy mạnh làm số của hộp mà không quy đổi; đưa dung lượng đo từ clip điện thoại ra như số của camera cố định."
- Repo public: không ghi IP, hostname hay tài khoản vào file nào trong repo. Máy long được gọi qua biến môi trường `LONG_HOST`.
- Mốc giờ trên Confluence và recap: chạy `date` đúng lúc ghi, dạng `YYYY-MM-DD HH:MM +07:00`.
- Commit message không có dòng `Co-Authored-By` hay `Generated with` (ý của hoang).

## Review Focus

Những chỗ dễ hỏng âm thầm mà người dùng bảng số sẽ chịu. Mỗi dòng có test ở task sở hữu:

1. **Lẫn đơn vị.** Mbps với MB/s, MB với GB, VND với USD. Sai một bậc là đảo kết luận về B. Test ở Task 4 (2 Mbps × 14 giờ = 12,6 GB) và Task 8 (quy đổi tỷ giá).
2. **Tiền 4G và router tính cho cả 30 tiệm** thay vì chỉ phần tiệm không có WiFi. Test ở Task 8.
3. **Nạp mô hình P03 sai mà vẫn ra số.** Mô hình chi phí phải tái tạo đúng $443,96 (1 camera) và $651,04 (2 camera) của P03 trước khi thêm gì. Test ở Task 8.
4. **Tổ hợp trượt điều kiện biến mất khỏi bảng.** Spec bắt giữ lại để Datagent thấy cái giá. Test ở Task 9.
5. **Đo tốc độ hộp bằng cả 48 luồng** vì torch hoặc OpenCV bỏ qua giới hạn luồng. Script phải tự kiểm 4 luồng trước khi đo. Test ở Task 5.

Thêm một điều về nguồn: mọi điểm CPU dùng để quy đổi phải cùng một thang điểm. Test ở Task 2.

---

## Bối cảnh cho người thực hiện

- **Hai máy.** Repo nằm trên máy hoang (Windows, Git Bash): `cctv-goods-detection/`, nhánh `docs/vault-and-recap-skill`. Máy hoang không có ffmpeg. Máy GPU của long (Ubuntu, AMD Ryzen Threadripper 9960X, 24 nhân / 48 luồng) gọi bằng `ssh "$LONG_HOST" '<lệnh>'`; host nằm trong `~/.ssh/config` của hoang, không ghi vào repo.
- **Thứ có sẵn trên máy long** (chỉ đọc; kiểm ngày 27/10):
  - `~/Desktop/Datagent/cv_output_sample/images/`: 39 khung thật, **1920×1080** (2 MP), đã làm mờ mặt.
  - `~/Desktop/Datagent/challenge_videos/vid_milk/IMG_0798.MOV` … `IMG_0804.MOV`: 7 clip điện thoại gốc, HEVC 1920×1080, khoảng 60 fps, khoảng 13,4 Mbps, dài 3,6–8,3 giây, quay cầm tay.
  - `~/Desktop/Datagent/carton_recognition/checked_videos_types/*.json`: kết quả từng khung của 10 clip. Mỗi file có `frames` → `{"<số khung>": [unit, ...]}`; mỗi unit có `yolo_type` (vd `vinamilk_soy`).
  - `~/Desktop/Datagent/yolo/yolo26s.pt` (bản COCO gốc) và `yolo/best_types.pt` (12 loại).
  - `~/Desktop/Datagent/carton_recognition/cv_output.py`: `timed_units(image, yolo, rec, conf, imgsz) -> (units, ms)`. `main()` dựng `rec = Recognizer(device=..., types=True)` và `yolo = YOLO(<Datagent>/yolo/best_types.pt)`; chép đúng cách dựng đó.
- **Trong repo:** `media/merl-1_1.mp4`, `merl-21_1.mp4`, `merl-31_1.mp4` (camera cố định, 640×472, 30 fps, 7 giây, bộ dữ liệu công khai). `docs/architecture/cost_model.py` là mô hình P03: `estimate("30 tiệm × 1 camera", "A")` cho tổng 443,96, trong đó dòng `["2 Xử lý"]["SageMaker Async ml.g6.xlarge"]` là 179,75; hàm đọc biến toàn cục `A`. Bản P02 ở commit `518eeae` có giá KVS.
- **Trên máy hoang:** 84 ảnh iPhone 24 MP ở `D:\Milkkkk-20261013T075004Z-1-001\Milkkkk\`.
- **Lệch so với chữ của P06, ghi vào Nhật ký P06 khi chạy tới:**
  - E1 video dùng 7 clip MOV gốc và 3 clip MERL. Ba clip điện thoại còn lại không còn file gốc; thư mục `*_frames` chỉ giữ 6 khung mỗi clip.
  - Mức 8 MP lấy từ ảnh iPhone thu nhỏ, vì 39 khung chỉ có 2 MP. P06 đã dự trù trường hợp này.

### Quyết định của kế hoạch (agent tự chốt, hoang xem khi duyệt kế hoạch)

1. **Trường hợp gốc:** 1 camera mỗi tiệm, 50% tiệm không có WiFi, 4G 200.000 đ/tháng (mức cao của hai con số), cloud đếm bằng CPU. Các biến thể khác chỉ để kiểm xem quyết định có đổi không.
2. **Giá có khoảng thì lấy mức cao** (thận trọng). Khoảng đầy đủ ghi ở cột `note`.
3. **Quy đổi tốc độ CPU** bằng điểm đơn luồng: thời gian trên máy B = thời gian trên máy A × điểm máy A ÷ điểm máy B.
4. **Cloud đếm bằng SageMaker Async `ml.c5.xlarge`** (4 vCPU). Thời gian mỗi ảnh = số đo E2 trên máy long (4 luồng), quy đổi sang CPU của `ml.c5.xlarge`.
5. **G1 của B dùng bitrate của nhà sản xuất** cho camera cố định 8 MP H.265. Số đo từ clip chỉ để đối chiếu.
6. **12 tuần = 84 ngày = 2,8 tháng.**
7. **Vùng kệ của 3 clip MERL** vẽ tay trên khung đầu, lưu ở `inputs/merl_shelf_roi.csv`.
8. **Bộ đệm khi mất mạng:** với A và B, thẻ microSD 128 GB trong camera nếu camera có khe thẻ, không có khe thì bằng 0. Với C và D là ổ của hộp. Với OAK 4 S là 128 GB như P03.

## File Structure

```
experiments/p06_ingest_options/
  README.md                 cách đồng bộ, venv, chạy test, dữ liệu trên máy long
  .gitignore                results/*.log, data/, __pycache__/
  requirements.txt          pytest
  tools/sync.sh             như của P05, thư mục xa là ~/Desktop/Datagent/ingest_bench
  tools/remote_job.sh       chạy một lệnh trên máy long bằng systemd-run và chờ xong
  inputs/sources.csv        mọi giá và thông số; mỗi dòng có nguồn và ngày tra
  inputs/merl_shelf_roi.csv vùng kệ của 3 clip MERL
  ingest/__init__.py
  ingest/sources.py         đọc và kiểm sources.csv; REQUIRED_KEYS
  ingest/resolution.py      E3: px/cm, chiều cao hộp, bề ngang phủ được, G3
  ingest/encode.py          E1: MB mỗi ảnh JPEG, Mbps mỗi video (ffmpeg)
  ingest/bandwidth.py       E1: GB/ngày theo phương án và camera, G1
  ingest/edge_filter.py     E2, E4: độ nét, người chồng vùng kệ, làm mờ mặt, chọn khung, giới hạn luồng
  ingest/run_edge_timing.py E2: đo ms trên máy long (cần model)
  ingest/edge_timing.py     E2: quy đổi ms sang từng hộp và sang cloud
  ingest/frame_selection.py E4: số đếm dao động giữa các khung, tỷ lệ khung có người
  ingest/outage.py          E6: số giờ mất mạng chịu được
  ingest/costs.py           E5: tiền một lần, tiền tháng, tổng 12 tuần và 12 tháng
  ingest/report.py          quyết định done / closed-fail và results/summary.md
  tests/conftest.py         marker `remote`
  tests/test_*.py           một file test cho mỗi module trên
  results/                  CSV và summary.md (không có ảnh)
```

Lệnh test trên máy hoang: `cd experiments/p06_ingest_options && python -m pytest tests -q -m "not remote"`.
Lệnh test trên máy long: `ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/ingest_bench && .venv/bin/python -m pytest tests -q'`.

Thứ tự task theo phụ thuộc: chi phí (Task 8) cần kết quả của E1, E2 và E3. Vì vậy thứ tự khác bảng Nextstep của P06, nhưng cả sáu việc E1–E6 vẫn đủ.

---

### Task 1: Khung thư mục, đồng bộ và bảng nguồn

**Files:**
- Create: `experiments/p06_ingest_options/{README.md,.gitignore,requirements.txt}`, `tools/sync.sh`, `tools/remote_job.sh`, `ingest/__init__.py`, `ingest/sources.py`, `inputs/sources.csv` (chỉ dòng tiêu đề), `tests/conftest.py`
- Test: `tests/test_sources.py`

**Interfaces:**
- Produces: `Source(key: str, value: float, unit: str, source: str, checked_on: str, note: str)` (dataclass, frozen); `load_sources(path: Path) -> dict[str, Source]`; `value(sources: dict[str, Source], key: str) -> float`. Cột của CSV: `key,value,unit,source,checked_on,note`.
- `tools/sync.sh push|pull`: chép từ P05, chỉ đổi thư mục xa thành `~/Desktop/Datagent/ingest_bench`.
- `tools/remote_job.sh NAME 'CMD'`: qua ssh, chạy `systemd-run --user --unit=p06-NAME --collect --wait -p MemoryMax=8G -p Nice=10 -p OOMScoreAdjust=1000` trong `~/Desktop/Datagent/ingest_bench`, ghi output vào `results/NAME.log`, trả về mã thoát của lệnh.

- [ ] **Step 1: Viết test hỏng**

```python
import pytest
from ingest.sources import load_sources, value

HEADER = "key,value,unit,source,checked_on,note\n"

def write(tmp_path, body):
    p = tmp_path / "s.csv"
    p.write_text(HEADER + body, encoding="utf-8")
    return p

def test_loads_a_valid_row(tmp_path):
    s = load_sources(write(tmp_path, "fx.vnd_per_usd,26350,VND/USD,https://vietcombank.com.vn,2026-10-27,giá bán\n"))
    assert value(s, "fx.vnd_per_usd") == 26350.0
    assert s["fx.vnd_per_usd"].checked_on == "2026-10-27"

@pytest.mark.parametrize("row", [
    "a.b,1,u,,2026-10-27,\n",             # thiếu nguồn
    "a.b,1,u,https://x,27/10/2026,\n",    # ngày sai dạng
    "a.b,abc,u,https://x,2026-10-27,\n",  # giá trị không phải số
])
def test_rejects_bad_rows(tmp_path, row):
    with pytest.raises(ValueError):
        load_sources(write(tmp_path, row))

def test_rejects_duplicate_keys(tmp_path):
    row = "a.b,1,u,https://x,2026-10-27,\n"
    with pytest.raises(ValueError, match="a.b"):
        load_sources(write(tmp_path, row + row))

def test_missing_key_names_the_key(tmp_path):
    s = load_sources(write(tmp_path, "a.b,1,u,https://x,2026-10-27,\n"))
    with pytest.raises(KeyError, match="c.d"):
        value(s, "c.d")
```

- [ ] **Step 2: Chạy test, thấy hỏng** — `python -m pytest tests/test_sources.py -q` → FAIL, `ModuleNotFoundError: ingest`.
- [ ] **Step 3: Viết `ingest/sources.py`, các file khung, hai script trong `tools/`** — đọc CSV bằng `csv.DictReader`, encoding `utf-8-sig`; `checked_on` phải khớp `^\d{4}-\d{2}-\d{2}$`. `conftest.py` khai báo marker `remote`: "cần máy long (ffmpeg, model, clip)".
- [ ] **Step 4: Chạy test, thấy qua** — `python -m pytest tests -q -m "not remote"` → 6 passed.
- [ ] **Step 5: Dựng venv trên máy long, chạy test ở đó**

```bash
tools/sync.sh push
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/ingest_bench && python3 -m venv --system-site-packages .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip freeze > requirements.lock && mkdir -p data/merl results && .venv/bin/python -m pytest tests -q'
scp "$LONG_HOST:Desktop/Datagent/ingest_bench/requirements.lock" experiments/p06_ingest_options/
scp media/merl-*.mp4 "$LONG_HOST:Desktop/Datagent/ingest_bench/data/merl/"
```
Kết quả mong đợi: `6 passed`.

- [ ] **Step 6: Commit** — `git add experiments/p06_ingest_options docs/superpowers/plans/2026-10-27-p06-ingest-options.md && git commit -m "P06: ke hoach thuc hien, khung thu muc, dong bo sang may long, bang nguon co kiem tra"`

### Task 2: Giá và thông số có nguồn

**Files:**
- Modify: `ingest/sources.py` (thêm `REQUIRED_KEYS`), `inputs/sources.csv`
- Test: `tests/test_sources.py`

**Interfaces:**
- Produces: `REQUIRED_KEYS: tuple[str, ...]` gồm đúng các key trong bảng dưới. Các task sau chỉ đọc giá qua `value(sources, key)`.

| Key | Ý nghĩa | Tra ở đâu |
|---|---|---|
| `fx.vnd_per_usd` | tỷ giá bán USD | Vietcombank, ngày tra |
| `power.vnd_per_kwh` | giá điện kinh doanh, giờ bình thường, cấp điện áp dưới 6 kV | EVN |
| `plan4g_sd100.price_vnd_month`, `plan4g_sd100.gb_per_day` | 100.000; 2 | nguồn của P03 (vietteldata.vn) |
| `plan4g_report.price_vnd_month` | 200.000 | báo cáo CV Output v1.0, trang 14 (ghi `source` là tên file và trang) |
| `router4g.price_vnd` | 990.000 (mức cao của 830.000–990.000) | nguồn của P03 (meta.vn, philong.com.vn) |
| `microsd128.price_vnd` | thẻ microSD 128 GB loại dùng cho camera | cửa hàng ở Việt Nam |
| `cam_2mp.{h_pixels,hfov_deg,power_w,sd_slot}` | 1920; 112,1; …; 0 hoặc 1 | datasheet Hikvision DS-2CD1023G0E-I (link ở P03) |
| `cam_4k_28.{h_pixels,hfov_deg,price_vnd,power_w,sd_slot}` | một model CCTV 8 MP có RTSP và H.265, ống 2,8 mm | datasheet; giá ở **hai** cửa hàng Việt Nam |
| `cam_4k_40.{h_pixels,hfov_deg,price_vnd,power_w,sd_slot}` | cùng model, ống 4 mm | như trên |
| `oak4s.{h_pixels,hfov_deg,price_usd,power_w,storage_gb}` | 8000; 67; 949; …; 128 | trang Luxonis, hoặc P03 nếu trang không mở được |
| `box_{rpi5,n100,orin}.{price_vnd,power_w,storage_gb,cpu_st,hevc_hw}` | bộ chạy được ngay: board hoặc máy, nguồn, vỏ, ổ lưu; công suất tối đa; ổ (GB); điểm CPU đơn luồng; có giải mã HEVC 4K bằng phần cứng (1/0) | cửa hàng Việt Nam (không có thì giá của hãng, ghi rõ); datasheet; trang benchmark |
| `cpu_long.cpu_st`, `cpu_cloud.cpu_st` | AMD Ryzen Threadripper 9960X; CPU của `ml.c5.xlarge` | trang benchmark |
| `aws.sm_async_cpu_h` | `ml.c5.xlarge` Async Inference, Tokyo | AWS Price List API, usagetype `APN1-AsyncInf:ml.c5.xlarge`; ghi ngày công bố |
| `aws.kvs_in_gb`, `aws.kvs_store_gbmo`, `aws.kvs_getimages_img` | 0,010965; 0,025; 0,00001 | `cost_model.py` ở commit `518eeae`; kiểm lại giá cho ảnh trên 1080p |
| `vendor.h265_8mp_mbps_low`, `vendor.h265_8mp_mbps_high` | bitrate camera 8 MP H.265 | datasheet hoặc công cụ tính bitrate của Hikvision hay Dahua |

`cpu_st` của cả năm CPU dùng **cùng một** thang điểm: ưu tiên PassMark CPU single thread; thiếu CPU nào thì dùng Geekbench 6 single-core cho cả năm. Ghi tên thang vào cột `unit`.

- [ ] **Step 1: Viết test hỏng**

```python
from pathlib import Path
from ingest.sources import REQUIRED_KEYS

SOURCES = Path(__file__).parents[1] / "inputs" / "sources.csv"

def test_every_required_key_has_a_sourced_value():
    s = load_sources(SOURCES)
    assert not [k for k in REQUIRED_KEYS if k not in s]

def test_cpu_scores_share_one_scale():
    s = load_sources(SOURCES)
    assert len({s[k].unit for k in REQUIRED_KEYS if k.endswith(".cpu_st")}) == 1

def test_currencies_are_labelled():
    s = load_sources(SOURCES)
    assert all(s[k].unit == "VND" for k in REQUIRED_KEYS if k.endswith(".price_vnd"))
```

- [ ] **Step 2: Chạy test, thấy hỏng** — `python -m pytest tests/test_sources.py -q` → FAIL (`REQUIRED_KEYS` chưa có, CSV rỗng).
- [ ] **Step 3: Thêm `REQUIRED_KEYS`, tra giá và điền `inputs/sources.csv`** — mỗi dòng có link và ngày tra (ngày chạy `date`). Món đắt nhất trong mỗi nhóm (camera 4K, mỗi hộp) cần hai nguồn: ghi nguồn thứ hai vào `note`.
- [ ] **Step 4: Chạy test, thấy qua** — `python -m pytest tests -q -m "not remote"` → 9 passed.
- [ ] **Step 5: Commit** — `git commit -m "P06: gia va thong so co nguon (sources.csv)"`

### Task 3: E3 — Độ nét

**Files:**
- Create: `ingest/resolution.py`
- Test: `tests/test_resolution.py`
- Ra: `results/resolution.csv`

**Interfaces:**
- Consumes: `load_sources`, `value` (Task 1).
- Produces: `G3_MIN_PX = 60`; `G3_DISTANCE_M = 2.0`; `CAMERAS = ("cam_2mp", "cam_4k_28", "cam_4k_40", "oak4s")`; `px_per_cm(h_pixels: int, hfov_deg: float, distance_m: float) -> float`; `coverage_width_m(hfov_deg: float, distance_m: float) -> float`; `carton_px(px_cm: float, carton_cm: float) -> float`; `passes_g3(carton_px_at_2m: float) -> bool`. CSV ra: `camera,distance_m,px_per_cm,carton_px,coverage_m,g3`. Cột `g3` chỉ xét ở 2 m và lặp lại trên mọi dòng của camera đó.

- [ ] **Step 1: Viết test hỏng**

```python
import pytest
from ingest.resolution import px_per_cm, coverage_width_m, carton_px, passes_g3

@pytest.mark.parametrize("w,hfov,d,expected", [
    (8000, 67.0, 1.5, 40.3), (8000, 67.0, 2.0, 30.2), (8000, 67.0, 3.0, 20.1),   # OAK 4 S, bảng của P03
    (4056, 69.0, 2.0, 14.8),                                                     # OAK-D CM4 PoE
    (1920, 112.1, 2.0, 3.2),                                                     # 2 MP, ống 2,8 mm
])
def test_px_per_cm_matches_p03(w, hfov, d, expected):
    assert round(px_per_cm(w, hfov, d), 1) == expected

def test_coverage_width():
    assert round(coverage_width_m(67.0, 2.0), 2) == 2.65

def test_g3_gate():
    assert not passes_g3(carton_px(px_per_cm(1920, 112.1, 2.0), 11.0))    # 35,5 px
    assert passes_g3(carton_px(px_per_cm(8000, 67.0, 2.0), 11.0))          # 332 px
    assert passes_g3(60.0) and not passes_g3(59.9)
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/resolution.py`** — công thức của P03: `px/cm = h_pixels ÷ (2 × khoảng cách(cm) × tan(HFOV ÷ 2))`. CLI: `python -m ingest.resolution --sources inputs/sources.csv --carton-cm 11 --out results/resolution.csv`, chạy cho `CAMERAS` × khoảng cách 1,5 / 2 / 3 m. Nếu hoang đã đo hộp thật thì dùng số đo cho `--carton-cm`; chưa đo thì giữ 11 và ghi *(chưa kiểm chứng)* ở summary.
- [ ] **Step 4: Chạy test và CLI** — test → PASS; CLI ghi 12 dòng (4 camera × 3 khoảng cách).
- [ ] **Step 5: Commit** — `git commit -m "P06: E3 do net theo camera va G3"`

### Task 4: E1 — Dung lượng

**Files:**
- Create: `ingest/encode.py`, `ingest/bandwidth.py`
- Test: `tests/test_encode.py`, `tests/test_bandwidth.py`
- Ra: `results/bandwidth_jpeg.csv`, `results/bandwidth_video.csv`, `results/bandwidth.csv`

**Interfaces:**
- Produces (`encode.py`): `jpeg_mb(image_bgr: np.ndarray, megapixels: float, quality: int = 90) -> float` (thu nhỏ giữ tỷ lệ về đúng số MP rồi `cv2.imencode`; **không** phóng to: `ValueError` nếu MP đích lớn hơn MP gốc quá 1%); `ffmpeg_cmd(src: Path, dst: Path, codec: str, crf: int, fps: int) -> list[str]`; `measure_mbps(path: Path) -> float` (byte × 8 ÷ thời lượng; thời lượng = số khung ÷ fps theo `cv2.VideoCapture`).
- Produces (`bandwidth.py`): `G1_LIMIT_GB = 2.0`; `OPEN_HOURS = 14.0`; `MARKS_PER_DAY = 56`; `D_IMAGES_PER_DAY = 14`; `video_gb_per_day(mbps: float, hours: float = OPEN_HOURS) -> float`; `images_gb_per_day(n_images: int, mb_each: float) -> float`; `option_gb_per_day(option: str, image_mb: float, video_mbps: float) -> float`; `passes_g1(gb_day: float) -> bool`. CSV ra `bandwidth.csv`: `option,camera,gb_day_low,gb_day_high,g1,basis`.
- Cột của `bandwidth_jpeg.csv`: `label,megapixels,n_images,mb_median,mb_p90,machine`. Của `bandwidth_video.csv`: `clip,label,width,height,codec,crf,fps,mbps`.

- [ ] **Step 1: Viết test hỏng**

```python
# tests/test_bandwidth.py
import pytest
from ingest.bandwidth import video_gb_per_day, images_gb_per_day, option_gb_per_day, passes_g1

def test_units():
    assert video_gb_per_day(2.0, 14.0) == pytest.approx(12.6)        # 2 Mbps × 14 giờ
    assert images_gb_per_day(56, 1.5) == pytest.approx(0.084)

def test_options():
    kw = dict(image_mb=1.5, video_mbps=2.0)
    assert option_gb_per_day("A", **kw) == pytest.approx(0.084)
    assert option_gb_per_day("B", **kw) == pytest.approx(12.6)
    assert option_gb_per_day("C", **kw) == pytest.approx(0.084)
    assert option_gb_per_day("D", **kw) == pytest.approx(0.02121)    # 14 ảnh + 14 × 30 dòng × 0,5 KB
    with pytest.raises(ValueError):
        option_gb_per_day("E", **kw)

def test_g1():
    assert passes_g1(2.0) and not passes_g1(2.01)
```

```python
# tests/test_encode.py
from pathlib import Path
import cv2, numpy as np, pytest
from ingest.encode import jpeg_mb, ffmpeg_cmd, measure_mbps

def noise(h, w):
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)

def test_jpeg_smaller_target_is_smaller():
    img = noise(2000, 4000)                          # 8 MP
    assert jpeg_mb(img, 2.0) < jpeg_mb(img, 8.0)

def test_jpeg_refuses_upscaling():
    with pytest.raises(ValueError):
        jpeg_mb(noise(1080, 1920), 8.0)

def test_ffmpeg_cmd():
    cmd = ffmpeg_cmd(Path("in.MOV"), Path("out.mp4"), "libx265", 28, 15)
    assert cmd[:4] == ["ffmpeg", "-y", "-i", "in.MOV"] and cmd[-1] == "out.mp4"
    for flag, val in (("-c:v", "libx265"), ("-crf", "28"), ("-r", "15")):
        assert cmd[cmd.index(flag) + 1] == val
    assert "-an" in cmd

def test_measure_mbps(tmp_path):
    path = tmp_path / "v.avi"
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for _ in range(20):
        vw.write(noise(48, 64))
    vw.release()
    assert measure_mbps(path) == pytest.approx(path.stat().st_size * 8 / 2.0 / 1e6, rel=0.01)
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/encode.py` và `ingest/bandwidth.py`** — D gửi `D_IMAGES_PER_DAY` ảnh cộng `D_IMAGES_PER_DAY × 30 × 0,5 KB` CSV (30 dòng mỗi ảnh, 0,5 KB mỗi dòng, như P03). `encode.py` có hai lệnh con:
  - `jpeg --images DIR --megapixels 2 8 --label L --machine M --out results/bandwidth_jpeg.csv --append`
  - `video --clips FILE... --label L --codecs libx265 libx264 --crf 23 28 --fps 15 --out results/bandwidth_video.csv [--append]`
- [ ] **Step 4: Chạy test, thấy qua** — `python -m pytest tests -q -m "not remote"` → PASS.
- [ ] **Step 5: Đo ảnh iPhone trên máy hoang** — `python -m ingest.encode jpeg --images "D:/Milkkkk-20261013T075004Z-1-001/Milkkkk" --megapixels 8 24 --label iphone --machine hoang --out results/bandwidth_jpeg.csv`
- [ ] **Step 6: Đo 39 khung và video trên máy long**

```bash
tools/sync.sh push
tools/remote_job.sh e1-jpeg '.venv/bin/python -m ingest.encode jpeg --images ~/Desktop/Datagent/cv_output_sample/images --megapixels 2 --label frames39 --machine long --out results/bandwidth_jpeg_long.csv'
tools/remote_job.sh e1-video '.venv/bin/python -m ingest.encode video --clips data/merl/*.mp4 --label merl --codecs libx265 libx264 --crf 23 28 --fps 15 --out results/bandwidth_video.csv && .venv/bin/python -m ingest.encode video --clips ~/Desktop/Datagent/challenge_videos/vid_milk/IMG_08*.MOV ~/Desktop/Datagent/challenge_videos/vid_milk/IMG_079*.MOV --label iphone --codecs libx265 libx264 --crf 23 28 --fps 15 --out results/bandwidth_video.csv --append'
tools/sync.sh pull
```
Ghép `bandwidth_jpeg_long.csv` vào `bandwidth_jpeg.csv`. Video mã hoá xong ghi vào `data/encoded/` trên máy long, không kéo về.

- [ ] **Step 7: Tính GB/ngày và G1** — `python -m ingest.bandwidth --sources inputs/sources.csv --jpeg results/bandwidth_jpeg.csv --out results/bandwidth.csv`:
  - MB mỗi ảnh theo camera: `cam_2mp` lấy `frames39` 2 MP; `cam_4k_*` lấy `iphone` 8 MP; `oak4s` lấy 10 MB của P03 cho cả mức thấp và mức cao.
  - Mức thấp dùng trung vị, mức cao dùng p90.
  - B dùng `vendor.h265_8mp_mbps_low/high`, với `basis=vendor`.
  - G1 xét ở mức cao.
- [ ] **Step 8: Ghi Nhật ký P06** về hai chỗ lệch ở phần Bối cảnh (lấy giờ bằng `date`). Sau đó commit — `git commit -m "P06: E1 dung luong anh va video, G1"`

### Task 5: E2 — Sức hộp

**Files:**
- Create: `ingest/edge_filter.py`, `ingest/run_edge_timing.py`, `ingest/edge_timing.py`
- Test: `tests/test_edge_filter.py`
- Ra: `results/edge_timing_raw.csv`, `results/edge_timing.csv`

**Interfaces:**
- Produces (`edge_filter.py`): `FrameInfo(sharpness: float, person_on_shelf: bool)` (frozen); `sharpness(gray: np.ndarray) -> float` (phương sai của `cv2.Laplacian`); `overlaps(box_xyxy, roi_xywh, min_frac: float = 0.05) -> bool` (phần diện tích khung người nằm trong vùng kệ ≥ `min_frac`); `select_best(frames: list[FrameInfo]) -> int | None` (khung nét nhất trong các khung không có người che kệ; tất cả bị che thì `None`); `blur_faces(image_bgr: np.ndarray, detector) -> int` (YuNet, làm mờ tại chỗ, trả số mặt); `configure_threads(n: int) -> None` (đặt `torch.set_num_threads(n)` và `cv2.setNumThreads(n)`; `RuntimeError` nếu `len(os.sched_getaffinity(0)) != n`).
- Produces (`edge_timing.py`): `scale_ms(ms_ref: float, st_ref: float, st_target: float) -> float`. CSV ra `edge_timing.csv`: `target,filter_ms_frame,count_ms_image,c_s_per_mark,d_s_per_day`, với target là `box_rpi5`, `box_n100`, `box_orin` và `cloud`. `c_s_per_mark` = 60 khung × lọc. `d_s_per_day` = 56 mốc × 60 khung × lọc + 14 ảnh × đếm.

- [ ] **Step 1: Viết test hỏng**

```python
import cv2, numpy as np, pytest
from ingest.edge_filter import FrameInfo, sharpness, overlaps, select_best, configure_threads
from ingest.edge_timing import scale_ms

def test_blur_lowers_sharpness():
    g = np.random.default_rng(0).integers(0, 256, (200, 200), dtype=np.uint8)
    assert sharpness(cv2.GaussianBlur(g, (0, 0), 3)) < sharpness(g)

def test_overlaps():
    roi = (0, 0, 100, 100)
    assert overlaps((10, 10, 30, 30), roi)
    assert not overlaps((200, 200, 220, 220), roi)
    assert not overlaps((98, 98, 198, 198), roi)       # 4/10.000 diện tích trong vùng kệ, dưới 5%

def test_select_best_skips_occluded_frames():
    assert select_best([FrameInfo(10.0, False), FrameInfo(30.0, True), FrameInfo(20.0, False)]) == 2
    assert select_best([FrameInfo(5.0, True)]) is None

def test_scale_ms():
    assert scale_ms(100.0, st_ref=4000.0, st_target=2000.0) == pytest.approx(200.0)

@pytest.mark.remote
def test_configure_threads_pins_four():                 # chạy dưới `taskset -c 0-3`
    import torch
    configure_threads(4)
    assert torch.get_num_threads() == 4 and cv2.getNumThreads() == 4
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết ba module.** `edge_filter.py` chỉ import `torch` bên trong `configure_threads`, để test trên máy hoang không cần torch. `run_edge_timing.py` (chỉ chạy trên máy long):
  - Gọi `configure_threads(4)` trước khi nạp model.
  - Bước lọc trên mỗi khung: YOLO26s COCO (`classes=[0]`, `imgsz=640`, `conf=0.4`, `device="cpu"`), YuNet làm mờ mặt, rồi tính độ nét.
  - Bước đếm: `timed_units` trên CPU, dựng `rec` và `yolo` như `main()` của `cv_output.py`.
  - Lần gọi đầu là khởi động, không tính vào thời gian.
  - Ghi `image,step,ms` vào `results/edge_timing_raw.csv`.
- [ ] **Step 4: Chạy test trên máy hoang** — `python -m pytest tests -q -m "not remote"` → PASS.
- [ ] **Step 5: Tải YuNet và đo trên máy long**

```bash
tools/sync.sh push
ssh "$LONG_HOST" 'cd ~/Desktop/Datagent/ingest_bench && mkdir -p data/models && curl -sSL -o data/models/face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
tools/remote_job.sh e2-test 'taskset -c 0-3 env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m pytest tests -q -m remote'
tools/remote_job.sh e2-timing 'taskset -c 0-3 env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 .venv/bin/python -m ingest.run_edge_timing --images ~/Desktop/Datagent/cv_output_sample/images --person-model ~/Desktop/Datagent/yolo/yolo26s.pt --face-model data/models/face_detection_yunet_2023mar.onnx --datagent ~/Desktop/Datagent --out results/edge_timing_raw.csv'
tools/sync.sh pull
```
Kết quả mong đợi: test `remote` → PASS; `edge_timing_raw.csv` có 39 × 2 dòng.

- [ ] **Step 6: Quy đổi** — `python -m ingest.edge_timing --raw results/edge_timing_raw.csv --sources inputs/sources.csv --out results/edge_timing.csv`, dùng trung vị ms và `cpu_st` của `cpu_long`, từng hộp, và `cpu_cloud`.
- [ ] **Step 7: Commit** — `git commit -m "P06: E2 thoi gian loc va dem tren hop, quy doi theo diem CPU"`

### Task 6: E4 — Giá trị chọn ảnh (chỉ báo)

**Files:**
- Create: `ingest/frame_selection.py`, `inputs/merl_shelf_roi.csv` (`clip,x,y,w,h,note`)
- Test: `tests/test_frame_selection.py`
- Ra: `results/frame_selection.csv`

**Interfaces:**
- Consumes: `overlaps` (Task 5).
- Produces: `counts_per_frame(frames: dict[str, list[dict]]) -> list[Counter]` (sắp theo số khung, đếm theo `yolo_type`); `median_counts(counts: list[Counter]) -> dict[str, float]` (mọi SKU xuất hiện ở bất kỳ khung nào; khung thiếu SKU tính 0); `deviation(c: Counter, med: dict[str, float]) -> float` (tổng |đếm − trung vị|); `random_frame_deviation(counts, n: int = 1000, seed: int = 0) -> dict` (`mean`, `p50`, `p90`); `occlusion_stats(flags: list[bool], fps: float) -> dict` (`frames`, `occluded`, `occluded_share`, `longest_clean_s`). CSV ra: `source,clip,frames,metric,value`.

- [ ] **Step 1: Viết test hỏng**

```python
from collections import Counter
import pytest
from ingest.frame_selection import counts_per_frame, median_counts, deviation, occlusion_stats

def unit(t):
    return {"yolo_type": t}

def test_counts_and_deviation():
    frames = {"0": [unit("a")] * 2, "10": [unit("a")] * 5, "2": [unit("a")] * 2 + [unit("b")]}
    counts = counts_per_frame(frames)
    assert counts == [Counter(a=2), Counter(a=2, b=1), Counter(a=5)]      # khung 0, 2, 10
    med = median_counts(counts)
    assert med == {"a": 2.0, "b": 0.0}
    assert [deviation(c, med) for c in counts] == [0.0, 1.0, 3.0]

def test_occlusion_stats():
    s = occlusion_stats([False, False, True, True, False, False, False], fps=1.0)
    assert (s["frames"], s["occluded"]) == (7, 2)
    assert s["longest_clean_s"] == pytest.approx(3.0)
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/frame_selection.py` và vẽ vùng kệ** — xuất khung đầu của mỗi clip MERL ra ảnh trong thư mục tạm, xem ảnh, rồi ghi `x,y,w,h` của vùng kệ vào `inputs/merl_shelf_roi.csv`. Lệnh `--merl` chạy YOLO26s COCO (`classes=[0]`, `imgsz=640`, `conf=0.4`) trên từng khung; khung có người chồng vùng kệ là khung bị che. `ultralytics` chỉ được import bên trong hàm chạy MERL, để test trên máy hoang không cần nó.
- [ ] **Step 4: Chạy test, thấy qua** — `python -m pytest tests -q -m "not remote"` → PASS.
- [ ] **Step 5: Chạy trên máy long** — `tools/sync.sh push`, rồi `tools/remote_job.sh e4 '.venv/bin/python -m ingest.frame_selection --clip-json ~/Desktop/Datagent/carton_recognition/checked_videos_types --merl data/merl --merl-roi inputs/merl_shelf_roi.csv --person-model ~/Desktop/Datagent/yolo/yolo26s.pt --out results/frame_selection.csv'`, rồi `tools/sync.sh pull`. Kết quả: 10 clip điện thoại và 3 clip MERL đều có dòng.
- [ ] **Step 6: Commit** — `git commit -m "P06: E4 chi bao gia tri chon anh (dao dong so dem, khung co nguoi)"`

### Task 7: E6 — Rớt mạng

**Files:**
- Create: `ingest/outage.py`
- Test: `tests/test_outage.py`
- Ra: `results/outage.csv`

**Interfaces:**
- Consumes: `results/bandwidth.csv` (Task 4), `value` (Task 1).
- Produces: `SD_CARD_GB = 128`; `hours_until_full(buffer_gb: float, gb_per_day: float, open_hours: float = 14.0) -> float`; `buffer_gb(option: str, camera: str, box: str | None, sources) -> float`, theo quyết định 8 ở trên. CSV ra: `option,camera,box,buffer_gb,gb_day_high,hours_until_full`.

- [ ] **Step 1: Viết test hỏng**

```python
import pytest
from ingest.outage import hours_until_full

def test_hours_until_full():
    assert hours_until_full(128, 0.084) == pytest.approx(21333.33, rel=1e-4)
    assert hours_until_full(128, 12.6) == pytest.approx(142.22, rel=1e-4)
    assert hours_until_full(0, 0.084) == 0.0
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/outage.py`**, CLI `python -m ingest.outage --sources inputs/sources.csv --bandwidth results/bandwidth.csv --out results/outage.csv`.
- [ ] **Step 4: Chạy test và CLI** — PASS; mỗi tổ hợp phương án × camera (× hộp với C, D) có một dòng.
- [ ] **Step 5: Commit** — `git commit -m "P06: E6 so gio mat mang chiu duoc"`

### Task 8: E5 — Chi phí

**Files:**
- Create: `ingest/costs.py`
- Test: `tests/test_costs.py`
- Ra: `results/cost.csv`

**Interfaces:**
- Consumes: `value` (Task 1); `results/resolution.csv` (Task 3); `results/bandwidth.csv` (Task 4); `results/edge_timing.csv` (Task 5).
- Produces:
  - `MONTHS_12W = 84 / 30`, `N_STORES = 30`.
  - `Combo(option, camera, box, no_wifi_share, plan4g, cams_per_store, processing)` (frozen).
  - `BASE = dict(no_wifi_share=0.5, plan4g="plan4g_report", cams_per_store=1, processing="cpu")`.
  - `combos() -> list[Combo]`: tạo các tổ hợp sau.
    - Phương án A, B đi với `cam_2mp`, `cam_4k_28`, `cam_4k_40`, `box=None`.
    - Phương án C, D đi với hai camera 4K và `cam_2mp`, nhân với ba hộp; cộng thêm `oak4s` với `box=None`.
    - Mỗi tổ hợp trên nhân với các biến thể: `no_wifi_share` ∈ {0, 0,5, 1}, `plan4g` ∈ {`plan4g_sd100`, `plan4g_report`}, `cams_per_store` ∈ {1, 2}, `processing` ∈ {`cpu`, `gpu_p03`}.
  - `load_p03(repo_root: Path) -> ModuleType`: nạp `docs/architecture/cost_model.py` bằng `importlib.util.spec_from_file_location`.
  - `p03_breakdown(p03, cams_per_store: int, overrides: dict) -> dict[str, dict[str, float]]`: gán `p03.A = {**p03.ASSUMPTIONS, **overrides}` rồi gọi `estimate(<SCALES theo số camera>, "A")`, sau đó trả lại `p03.A` như cũ.
  - `cloud_monthly_usd(option: str, cams_per_store: int, processing: str, p03, sources, image_mb: float, video_gb_day: float, timing: dict) -> float`. `timing` có `filter_ms_cloud` và `count_ms_cloud`.
  - `fourg_monthly_usd(n_stores, no_wifi_share, plan_vnd, fx) -> float`, `router_one_time_usd(n_stores, no_wifi_share, router_vnd, fx) -> float`, `electricity_monthly_usd(power_w, n_devices, vnd_per_kwh, fx) -> float`.
  - `one_time_usd(combo, sources) -> float`, `monthly_usd(combo, sources, cloud_usd: float) -> float`, `totals(one_time: float, monthly: float) -> tuple[float, float]`.
  - CSV ra: các trường của `Combo` cùng `one_time_usd,monthly_usd,total_12w_usd,total_12m_usd,g1,g2,g3,base`.

- [ ] **Step 1: Viết test hỏng**

```python
from pathlib import Path
import pytest
from ingest.costs import (totals, fourg_monthly_usd, router_one_time_usd, electricity_monthly_usd,
                          load_p03, p03_breakdown, cloud_monthly_usd)
from ingest.sources import load_sources

REPO = Path(__file__).resolve().parents[3]

@pytest.fixture
def p03():
    return load_p03(REPO)

@pytest.fixture
def aws(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("key,value,unit,source,checked_on,note\n"
                 "aws.sm_async_cpu_h,0.2,USD/h,t,2026-10-27,\n"
                 "aws.kvs_in_gb,0.010965,USD/GB,t,2026-10-27,\n"
                 "aws.kvs_store_gbmo,0.025,USD/GB-month,t,2026-10-27,\n"
                 "aws.kvs_getimages_img,0.00001,USD/image,t,2026-10-27,\n", encoding="utf-8")
    return load_sources(p)

def test_totals():
    assert totals(1000.0, 100.0) == pytest.approx((1280.0, 2200.0))

def test_4g_and_router_only_for_stores_without_wifi():
    assert fourg_monthly_usd(30, 0.5, 200_000, 25_000) == pytest.approx(120.0)
    assert fourg_monthly_usd(30, 0.0, 200_000, 25_000) == 0.0
    assert router_one_time_usd(30, 0.5, 990_000, 25_000) == pytest.approx(594.0)

def test_electricity():
    assert electricity_monthly_usd(10.0, 30, 3_000, 25_000) == pytest.approx(25.92)

def test_p03_baseline_is_reproduced(p03):
    assert p03.total(p03_breakdown(p03, 1, {})) == pytest.approx(443.96, abs=0.01)
    assert p03.total(p03_breakdown(p03, 2, {})) == pytest.approx(651.04, abs=0.01)
    assert p03.A == p03.ASSUMPTIONS                       # trả lại giả định của P03 sau khi tính

def test_cloud_order_by_option(p03, aws):
    t = {"filter_ms_cloud": 200.0, "count_ms_cloud": 1000.0}
    cost = lambda o, video: cloud_monthly_usd(o, 1, "cpu", p03, aws, image_mb=1.5, video_gb_day=video, timing=t)
    assert cost("D", 0.0) < cost("C", 0.0) < cost("B", 12.6)
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/costs.py`**, theo các quy tắc sau:
  - Đè giả định của P03 cho mọi phương án: `still_mb` = MB mỗi ảnh của camera (lấy mức cao từ Task 4), `people_drop = 0`.
  - A, C: `processed_per_cam_day = 14`.
  - D: thay dòng `["2 Xử lý"]["SageMaker Async ml.g6.xlarge"]` bằng 0, và 14 ảnh gửi lên mỗi ngày.
  - Khi `processing="cpu"`, dòng đó thay bằng giờ CPU × `aws.sm_async_cpu_h`. Giờ CPU gồm:
    - (ảnh đếm × `count_ms_cloud` + khung lọc × `filter_ms_cloud`) ÷ 3,6·10⁶;
    - cộng 10 phút khởi động mỗi đêm × 30 đêm.
  - Số khung lọc trên cloud mỗi camera mỗi ngày: A là 56 ảnh; B là 56 mốc × 60 khung.
  - B cộng thêm ba khoản KVS: ghi (GB video × 30 × `aws.kvs_in_gb`), lưu 7 ngày (như P02), và lấy khung (56 × 60 × 30 × `aws.kvs_getimages_img`).
  - `processing="gpu_p03"` giữ nguyên cách tính GPU của P03.
  - Phần cứng:
    - Camera: 0 với `cam_2mp`; với camera 4K là `price_vnd ÷ fx`; với OAK 4 S là `price_usd`.
    - Hộp: C, D dùng `price_vnd ÷ fx`.
    - Thẻ 128 GB cho A, B khi camera có khe thẻ.
    - Router chỉ cho phần tiệm không có WiFi.
    - Mọi thứ nhân số camera mỗi tiệm, trừ hộp và router (một cái mỗi tiệm).
  - Điện: camera cộng hộp, chạy 24 giờ.
  - Ba cột cổng:
    - `g1` lấy từ `bandwidth.csv` cho mọi tổ hợp, kể cả khi `no_wifi_share = 0`, vì thiết kế phải chạy được ở tiệm chỉ có 4G.
    - `g2` đúng khi phương án là C hoặc D.
    - `g3` lấy từ `resolution.csv` ở 2 m.
  - CLI: `python -m ingest.costs --sources inputs/sources.csv --results results --out results/cost.csv`.
- [ ] **Step 4: Chạy test và CLI** — `python -m pytest tests -q -m "not remote"` → PASS; `cost.csv` có đủ mọi tổ hợp, cột `base` đúng với các dòng khớp `BASE`.
- [ ] **Step 5: Commit** — `git commit -m "P06: E5 chi phi mot lan, hang thang, 12 tuan va 12 thang"`

### Task 9: Tổng hợp và quyết định

**Files:**
- Create: `ingest/report.py`
- Test: `tests/test_report.py`
- Ra: `results/summary.md`

**Interfaces:**
- Consumes: mọi CSV trong `results/`.
- Produces:
  - `MAX_RATIO = 1.10`.
  - `Decision(status: str, winner: dict, best_c: dict | None, ratio: float | None)` (frozen). `status` là `"done"` hoặc `"closed-fail"`. `winner` là tổ hợp rẻ nhất qua G1–G3. `best_c` là tổ hợp C rẻ nhất qua G1–G3, hoặc `None`. `ratio` = tổng 12 tháng của `best_c` ÷ của `winner`. Khi `done`, tổ hợp đề xuất là `best_c`.
  - `decide(rows: list[dict]) -> Decision`: chỉ xét các dòng `base`.
  - `gate_label(row: dict) -> str`: trả `"qua"`, hoặc `"trượt G1, G3"` khi trượt.
  - `render_main_table(rows: list[dict]) -> str`: bảng markdown, mỗi dòng là một phương án × camera với hộp rẻ nhất, gồm cả dòng trượt.
  - CLI: `python -m ingest.report --results results --out results/summary.md`.

- [ ] **Step 1: Viết test hỏng**

```python
import pytest
from ingest.report import decide, gate_label, render_main_table

def row(option, total, g1=True, g2=True, g3=True, camera="cam_4k_28", box="box_n100"):
    return dict(option=option, camera=camera, box=box, total_12m_usd=total, g1=g1, g2=g2, g3=g3, base=True)

def test_c_cheapest_is_done():
    d = decide([row("C", 1000), row("D", 1100), row("A", 800, g2=False)])
    assert d.status == "done" and d.winner["option"] == "C" and d.ratio == pytest.approx(1.0)

def test_c_within_ten_percent_is_done():
    d = decide([row("C", 1050), row("D", 1000)])
    assert d.status == "done" and d.winner["option"] == "D" and d.ratio == pytest.approx(1.05)

def test_c_too_expensive_is_closed_fail():
    d = decide([row("C", 1200), row("D", 1000)])
    assert d.status == "closed-fail" and d.winner["option"] == "D"

def test_c_failing_a_gate_is_closed_fail():
    d = decide([row("C", 900, g3=False), row("D", 1000)])
    assert d.status == "closed-fail" and d.best_c is None

def test_gate_label_and_failing_rows_stay_in_the_table():
    assert gate_label(row("B", 1, g1=False, g2=False)) == "trượt G1, G2"
    assert gate_label(row("C", 1)) == "qua"
    assert "trượt G2" in render_main_table([row("A", 800, g2=False), row("C", 1000)])
```

- [ ] **Step 2: Chạy test, thấy hỏng** — FAIL, `ImportError`.
- [ ] **Step 3: Viết `ingest/report.py`.** `summary.md` gồm các mục sau, theo thứ tự:
  1. Quyết định và lý do, một đoạn.
  2. Bảng chính của trường hợp gốc.
  3. Độ vững: quyết định có đổi dưới biến thể nào không.
  4. Độ nét (E3) và dung lượng (E1).
  5. Sức hộp (E2), ghi rõ là ước tính quy đổi.
  6. Rớt mạng (E6).
  7. Chỉ báo chọn ảnh (E4).
  8. Giới hạn.
  9. Danh sách giả định đã dùng: trỏ tới `inputs/sources.csv` và mục "Quyết định của kế hoạch".

  Mọi số chưa đo thật ghi *(chưa kiểm chứng)*: chiều cao hộp nếu chưa đo, thời gian quy đổi sang hộp và cloud, bitrate của nhà sản xuất.
- [ ] **Step 4: Chạy test và CLI** — PASS; đọc lại `summary.md` để kiểm mọi bảng có số.
- [ ] **Step 5: Commit** — `git commit -m "P06: tong hop va quyet dinh theo luat P06"`

### Task 10: Trang research, cập nhật P06 và recap

**Files:**
- Modify: `document_vault/Recap/hoang/2026-10-27/` (recap của phiên)
- Confluence: trang research mới trong Hoàng_Research (`328026`); HOANG-P06 (`12976131`); Cách dùng — Research (`98546`); Cách dùng — RoadMap (`98529`)

- [ ] **Step 1: Đọc Cách dùng — Research (`98546`)** để lấy mẫu thẻ đầu trang và quy ước tên.
- [ ] **Step 2: Tạo trang research** trong `328026`, tạo bằng markdown. Nội dung:
  - Tên dạng `YYYY-MM-DD — <kết luận ngắn>`, ngày lấy bằng `date`.
  - Mục Kết luận: quyết định và con số.
  - Mục Bằng chứng: các bảng chép từ `summary.md`, kèm link GitHub tới file kết quả ở commit đã push.
  - Mục Giới hạn và mục Nguồn (link `inputs/sources.csv`).
  - Một bảng gọn, viết tiếng Việt, đủ để đưa Datagent xem.
- [ ] **Step 3: Thêm dòng chỉ mục** vào Cách dùng — Research. Sửa theo local-id: đọc HTML, `insertNodeAfter` dòng cuối, chạy `dryRun` trước, rồi đọc lại local-id thật trước lần sửa sau.
- [ ] **Step 4: Cập nhật HOANG-P06**:
  - `status` thành `done` hoặc `closed-fail` theo `Decision`.
  - Cập nhật `updated`.
  - Thêm dòng Nhật ký có link trang research và các commit.
  - Sửa dòng chỉ mục P06 trên Cách dùng — RoadMap.
- [ ] **Step 5: Recap** bằng skill `recap`. Gộp phần "Đã đổi gì từ phiên trước" trong `RECAP_2026-10-27_1236.md` vào recap chốt phiên. Hỏi hoang có thêm dòng P06 vào Sheet không: agent không sửa Sheet chung, vì công cụ hiện có ghi đè cả file.
- [ ] **Step 6: Commit và push** — `git add experiments/p06_ingest_options docs/superpowers/plans/2026-10-27-p06-ingest-options.md document_vault/Recap/hoang/2026-10-27 && git commit -m "Recap 27/10 - P06 <status>" && git push`. Sau đó ghi hash vào recap, commit, rồi push lần nữa.
