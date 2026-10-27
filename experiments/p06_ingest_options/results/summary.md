# HOANG-P06 — bảng tổng hợp

Sinh tự động bằng `python -m ingest.report`. Tiền tính bằng USD, 30 tiệm. Trường hợp gốc: 1 camera mỗi tiệm, 50% tiệm không có WiFi, 4G 200.000 đ/tháng, cloud đếm bằng CPU. Mọi giá có nguồn ở `inputs/sources.csv`.

## 1. Quyết định

**`done`.** Tổ hợp C rẻ nhất qua cả G1–G3 là C, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $12.076 trả một lần, $396 mỗi tháng, $16.830 sau 12 tháng (mỗi tiệm $403 một lần và $13 mỗi tháng). Tổ hợp rẻ nhất qua cả ba điều kiện là D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5 với $16.786; C bằng 100,3% mức đó, trong ngưỡng 110% của P06.

Trượt điều kiện: A và B gửi mặt người lên cloud (G2); B vượt gói 4G (G1); camera 2 MP có sẵn cho hộp dưới 60 px ở 2 m (G3).

## 2. Bảng chính (trường hợp gốc)

| Phương án | Camera | Hộp | Một lần (30 tiệm) | Mỗi tháng | Sau 12 tuần | Sau 12 tháng | Điều kiện |
|---|---|---|---|---|---|---|---|
| A · camera tự gửi ảnh | 2 MP có sẵn | — | $570 | $353 | $1.560 | $4.811 | trượt G2, G3 |
| A · camera tự gửi ảnh | CCTV 4K, ống 2,8 mm | — | $4.361 | $376 | $5.412 | $8.867 | trượt G2 |
| A · camera tự gửi ảnh | CCTV 4K, ống 4 mm | — | $4.361 | $376 | $5.412 | $8.867 | trượt G2 |
| D · hộp đếm luôn | 2 MP có sẵn | Raspberry Pi 5 | $8.977 | $371 | $10.015 | $13.424 | trượt G3 |
| C · hộp lọc, cloud đếm | 2 MP có sẵn | Raspberry Pi 5 | $8.977 | $374 | $10.024 | $13.465 | trượt G3 |
| B · đẩy video lên cloud | 2 MP có sẵn | — | $570 | $1.310 | $4.238 | $16.289 | trượt G1, G2, G3 |
| D · hộp đếm luôn | CCTV 4K, ống 2,8 mm | Raspberry Pi 5 | $12.076 | $393 | $13.175 | $16.786 | qua |
| D · hộp đếm luôn | CCTV 4K, ống 4 mm | Raspberry Pi 5 | $12.076 | $393 | $13.175 | $16.786 | qua |
| C · hộp lọc, cloud đếm | CCTV 4K, ống 2,8 mm | Raspberry Pi 5 | $12.076 | $396 | $13.185 | $16.830 | qua |
| C · hộp lọc, cloud đếm | CCTV 4K, ống 4 mm | Raspberry Pi 5 | $12.076 | $396 | $13.185 | $16.830 | qua |
| B · đẩy video lên cloud | CCTV 4K, ống 2,8 mm | — | $4.361 | $1.332 | $8.090 | $20.344 | trượt G1, G2 |
| B · đẩy video lên cloud | CCTV 4K, ống 4 mm | — | $4.361 | $1.332 | $8.090 | $20.344 | trượt G1, G2 |
| D · hộp đếm luôn | OAK 4 S | — | $29.040 | $443 | $30.280 | $34.355 | qua |
| C · hộp lọc, cloud đếm | OAK 4 S | — | $29.040 | $448 | $30.296 | $34.421 | qua |

## 3. Độ vững

Quyết định giữ nguyên `done` ở 12/24 biến thể (tỷ lệ tiệm không WiFi 0/50/100%, 4G 100.000 hoặc 200.000 đ, 1 hoặc 2 camera mỗi tiệm, cloud đếm bằng CPU hoặc GPU 30 giây/ảnh như P03).

- **Cloud đếm bằng CPU (đo được, model hiện tại):** `done` ở 12/12 biến thể; C bằng 100,2–100,4% tổ hợp rẻ nhất.
- **Cloud đếm bằng GPU 30 giây/ảnh (giả định của P03):** `done` ở 0/12 biến thể; C bằng 111,6–123,2% tổ hợp rẻ nhất.

Khi cloud phải đếm bằng GPU, khoản GPU (khoảng $180/tháng ở P03) làm C đắt hơn D, vì D đếm ngay trên hộp. Con số đó giả định hộp chỉ có CPU vẫn kịp đếm 14 ảnh mỗi ngày với model nặng như vậy *(chưa kiểm chứng)*. Với model hiện tại (0,48 giây/ảnh trên CPU, báo cáo 17/10), biến thể CPU mới sát thực tế.

| Không WiFi | 4G/tháng | Camera/tiệm | Cloud đếm | Kết quả | C so với rẻ nhất | Rẻ nhất qua G1–G3 |
|---|---|---|---|---|---|---|
| 0% | 200.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $14.834 |
| 0% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 114,6% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $14.834 |
| 0% | 200.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.240 |
| 0% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 123,2% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.240 |
| 0% | 100.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $14.834 |
| 0% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 114,6% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $14.834 |
| 0% | 100.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.240 |
| 0% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 123,2% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.240 |
| 50% | 200.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $16.786 |
| 50% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 112,9% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $16.786 |
| 50% | 200.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $20.193 |
| 50% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 121,0% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $20.193 |
| 50% | 100.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $16.095 |
| 50% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 113,5% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $16.095 |
| 50% | 100.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $19.502 |
| 50% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 121,7% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $19.502 |
| 100% | 200.000 đ | 1 | CPU | `done` | 100,2% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.739 |
| 100% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 111,6% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $18.739 |
| 100% | 200.000 đ | 2 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $22.146 |
| 100% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 119,1% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $22.146 |
| 100% | 100.000 đ | 1 | CPU | `done` | 100,2% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $17.357 |
| 100% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 112,5% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $17.357 |
| 100% | 100.000 đ | 2 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $20.763 |
| 100% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 120,4% | D, CCTV 4K, ống 2,8 mm, Raspberry Pi 5: $20.763 |

## 4. Độ nét (E3) và dung lượng (E1)

Hộp 180 ml cao 11,0 cm *(chưa kiểm chứng — chưa đo hộp thật)*. G3 xét ở 2 m.

| Camera | px/cm ở 2 m | Hộp cao (px) ở 1,5 / 2 / 3 m | Bề ngang kệ phủ được ở 2 m | G3 |
|---|---|---|---|---|
| 2 MP có sẵn | 3,2 | 47 / 36 / 24 | 5,94 m | trượt |
| CCTV 4K, ống 2,8 mm | 7,1 | 104 / 78 / 52 | 5,41 m | qua |
| CCTV 4K, ống 4 mm | 10,1 | 148 / 111 / 74 | 3,80 m | qua |
| OAK 4 S | 30,1 | 441 / 330 / 220 | 2,66 m | qua |

| Ảnh JPEG chất lượng 90 | Số ảnh | MB trung vị | MB p90 |
|---|---|---|---|
| 84 ảnh iPhone, 8 MP | 84 | 1,21 | 1,34 |
| 84 ảnh iPhone, 24 MP | 84 | 3,35 | 3,59 |
| 39 khung ở tiệm, 2 MP | 27 (bỏ 12 khung nhỏ hơn) | 0,30 | 0,35 |

| Phương án | Camera | GB/ngày/tiệm (thấp–cao) | G1 (≤ 2 GB/ngày) | Căn cứ |
|---|---|---|---|---|
| A | 2 MP có sẵn | 0,017–0,019 | qua | đo |
| A | CCTV 4K, ống 2,8 mm | 0,068–0,075 | qua | đo |
| A | CCTV 4K, ống 4 mm | 0,068–0,075 | qua | đo |
| B | 2 MP có sẵn | 31,5–50,4 | trượt | bitrate nhà sản xuất *(chưa kiểm chứng)* |
| B | CCTV 4K, ống 2,8 mm | 31,5–50,4 | trượt | bitrate nhà sản xuất *(chưa kiểm chứng)* |
| B | CCTV 4K, ống 4 mm | 31,5–50,4 | trượt | bitrate nhà sản xuất *(chưa kiểm chứng)* |
| C | 2 MP có sẵn | 0,017–0,019 | qua | đo |
| C | CCTV 4K, ống 2,8 mm | 0,068–0,075 | qua | đo |
| C | CCTV 4K, ống 4 mm | 0,068–0,075 | qua | đo |
| C | OAK 4 S | 0,560–0,560 | qua | giả định 10 MB của P03 |
| D | 2 MP có sẵn | 0,004–0,005 | qua | đo |
| D | CCTV 4K, ống 2,8 mm | 0,017–0,019 | qua | đo |
| D | CCTV 4K, ống 4 mm | 0,017–0,019 | qua | đo |
| D | OAK 4 S | 0,140–0,140 | qua | giả định 10 MB của P03 |

Video mã hoá lại ở 15 fps để đối chiếu (Mbps trung vị): iPhone 1080p, cầm tay libx264 CRF 23: 4,00; iPhone 1080p, cầm tay libx264 CRF 28: 1,89; iPhone 1080p, cầm tay libx265 CRF 23: 3,72; iPhone 1080p, cầm tay libx265 CRF 28: 1,76; MERL 640×472, camera cố định libx264 CRF 23: 0,14; MERL 640×472, camera cố định libx264 CRF 28: 0,10; MERL 640×472, camera cố định libx265 CRF 23: 0,16; MERL 640×472, camera cố định libx265 CRF 28: 0,10.

## 5. Sức hộp (E2) — ước tính quy đổi *(chưa kiểm chứng trên hộp thật)*

Đo trên 4 luồng CPU của máy long (39 khung), quy đổi theo điểm Geekbench 6 đơn luồng. Hộp tính như chỉ có CPU.

| Nơi chạy | Lọc (ms/khung) | Đếm (ms/ảnh) | C: giây cho 60 khung mỗi mốc 15 phút | D: giây máy mỗi ngày | Giải mã HEVC phần cứng |
|---|---|---|---|---|---|
| Raspberry Pi 5 | 986 | 2.719 | 59,2 | 3.352 | có |
| mini PC N100 | 621 | 1.713 | 37,3 | 2.111 | có |
| Jetson Orin Nano Super | 934 | 2.574 | 56,0 | 3.174 | có |
| cloud (ml.c5.xlarge) | 660 | 1.819 | 39,6 | 2.243 | — |

## 6. Rớt mạng (E6)

| Phương án | Camera | Bộ đệm | Chịu được (giờ mở cửa) |
|---|---|---|---|
| A | 2 MP có sẵn | 0 GB | mất ảnh ngay |
| A | CCTV 4K, ống 2,8 mm | 128 GB | trên 1.000 giờ |
| A | CCTV 4K, ống 4 mm | 128 GB | trên 1.000 giờ |
| B | 2 MP có sẵn | 0 GB | mất ảnh ngay |
| B | CCTV 4K, ống 2,8 mm | 128 GB | 36 giờ |
| B | CCTV 4K, ống 4 mm | 128 GB | 36 giờ |
| C | 2 MP có sẵn | 128 GB | trên 1.000 giờ |
| C | CCTV 4K, ống 2,8 mm | 128 GB | trên 1.000 giờ |
| C | CCTV 4K, ống 4 mm | 128 GB | trên 1.000 giờ |
| C | OAK 4 S | 128 GB | trên 1.000 giờ |
| D | 2 MP có sẵn | 128 GB | trên 1.000 giờ |
| D | CCTV 4K, ống 2,8 mm | 128 GB | trên 1.000 giờ |
| D | CCTV 4K, ống 4 mm | 128 GB | trên 1.000 giờ |
| D | OAK 4 S | 128 GB | trên 1.000 giờ |

## 7. Chỉ báo chọn ảnh (E4) — không dùng để quyết

| Clip điện thoại | Khung | Hộp trung vị mỗi khung | Một khung ngẫu nhiên lệch (trung bình / p90) |
|---|---|---|---|
| 1791768734271_20 | 240 | 22,5 | 3,9 / 6,5 |
| 1791768734274_20 | 180 | 34,0 | 3,9 / 6,0 |
| 1791768734279_20 | 307 | 26,0 | 10,6 / 22,0 |
| IMG_0798 | 215 | 26,0 | 5,1 / 8,0 |
| IMG_0799 | 350 | 19,0 | 4,2 / 7,0 |
| IMG_0800 | 597 | 1,0 | 3,5 / 9,0 |
| IMG_0801 | 550 | 8,0 | 6,3 / 12,0 |
| IMG_0802 | 708 | 6,0 | 5,7 / 9,1 |
| IMG_0803 | 500 | 0,0 | 0,1 / 0,0 |
| IMG_0804 | 258 | 18,0 | 6,5 / 9,0 |

| Clip MERL | Khung | Khung có người chồng vùng kệ | Đoạn sạch dài nhất |
|---|---|---|---|
| merl-1_1.mp4 | 210 | 9% | 5,7 giây |
| merl-21_1.mp4 | 210 | 31% | 2,0 giây |
| merl-31_1.mp4 | 210 | 100% | 0,0 giây |

## 8. Giới hạn

- Chiều cao hộp 11,0 cm chưa đo. Camera 4K ống 2,8 mm (78 px ở 2 m) vẫn qua G3 nếu hộp cao từ 8,45 cm trở lên.
- Thời gian trên hộp và trên cloud là quy đổi theo điểm Geekbench 6 đơn luồng, chưa đo trên thiết bị thật.
- Bitrate video của B lấy từ nguồn cộng đồng và đại lý (5–8 Mbps cho 8 MP H.265); B trượt G1 ở mọi bitrate trên 0,32 Mbps, nên kết luận về B không phụ thuộc con số này.
- Clip điện thoại quay cầm tay; clip MERL trong repo là bản đã vẽ khung chú thích, độ phân giải 640×472. Chỉ báo E4 chỉ mang tính tham khảo.
- Giá OAK 4 S theo P03 ($949): trang Luxonis không hiện giá ngày 27/10. Giá mini PC N100 lấy từ Newegg cộng VAT nhập khẩu 10%, chưa gồm vận chuyển.
- Không tính công lắp đặt, bảo trì, gán nhãn (hoang chốt 27/10).

## 9. Giả định

Giá, thông số và nguồn: `inputs/sources.csv`. Các giả định của kế hoạch (trường hợp gốc, lấy mức giá cao, quy đổi CPU, `ml.c5.xlarge`, 12 tuần = 2,8 tháng, bộ đệm khi rớt mạng): mục "Quyết định của kế hoạch" trong `docs/superpowers/plans/2026-10-27-p06-ingest-options.md`. Mô hình cloud là `docs/architecture/cost_model.py` của P03, nạp nguyên vẹn.
