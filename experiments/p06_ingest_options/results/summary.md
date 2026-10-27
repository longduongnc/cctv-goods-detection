# HOANG-P06 — bảng tổng hợp

Sinh tự động bằng `python -m ingest.report`. Tiền tính bằng USD, 30 tiệm. Trường hợp gốc: 1 camera mỗi tiệm, 50% tiệm không có WiFi, 4G 200.000 đ/tháng, cloud đếm bằng CPU. Mọi giá có nguồn ở `inputs/sources.csv`.

## 1. Quyết định

**`done`.** Tổ hợp C rẻ nhất qua cả G1–G3 là C, CCTV 4K, ống 2,8 mm, mini PC N100: $10.684 trả một lần, $439 mỗi tháng, $15.949 sau 12 tháng (mỗi tiệm $356 một lần và $15 mỗi tháng). Tổ hợp rẻ nhất qua cả ba điều kiện là D, CCTV 4K, ống 2,8 mm, mini PC N100 với $15.903; C bằng 100,3% mức đó, trong ngưỡng 110% của P06.

Trượt điều kiện: A và B gửi mặt người lên cloud (G2); B vượt gói 4G (G1); camera 2 MP có sẵn cho hộp dưới 60 px ở 2 m (G3).

## 2. Bảng chính (trường hợp gốc)

| Phương án | Camera | Hộp | Một lần (30 tiệm) | Mỗi tháng | Sau 12 tuần | Sau 12 tháng | Điều kiện |
|---|---|---|---|---|---|---|---|
| A · camera tự gửi ảnh | 2 MP có sẵn | — | $570 | $354 | $1.561 | $4.816 | trượt G2, G3 |
| B · đẩy video lên cloud | 2 MP có sẵn | — | $570 | $722 | $2.593 | $9.239 | trượt G1, G2, G3 |
| A · camera tự gửi ảnh | CCTV 4K, ống 2,8 mm | — | $4.925 | $382 | $5.996 | $9.513 | trượt G2 |
| A · camera tự gửi ảnh | CCTV 4K, ống 4 mm | — | $4.925 | $382 | $5.996 | $9.513 | trượt G2 |
| D · hộp đếm luôn | 2 MP có sẵn | mini PC N100 | $7.021 | $413 | $8.177 | $11.976 | trượt G3 |
| C · hộp lọc, cloud đếm | 2 MP có sẵn | mini PC N100 | $7.021 | $417 | $8.187 | $12.020 | trượt G3 |
| D · hộp đếm luôn | CCTV 4K, ống 2,8 mm | mini PC N100 | $10.684 | $435 | $11.902 | $15.903 | qua |
| D · hộp đếm luôn | CCTV 4K, ống 4 mm | mini PC N100 | $10.684 | $435 | $11.902 | $15.903 | qua |
| C · hộp lọc, cloud đếm | CCTV 4K, ống 2,8 mm | mini PC N100 | $10.684 | $439 | $11.913 | $15.949 | qua |
| C · hộp lọc, cloud đếm | CCTV 4K, ống 4 mm | mini PC N100 | $10.684 | $439 | $11.913 | $15.949 | qua |
| B · đẩy video lên cloud | CCTV 4K, ống 2,8 mm | — | $4.925 | $1.726 | $9.758 | $25.637 | trượt G1, G2 |
| B · đẩy video lên cloud | CCTV 4K, ống 4 mm | — | $4.925 | $1.726 | $9.758 | $25.637 | trượt G1, G2 |
| D · hộp đếm luôn | OAK 4 S | — | $29.605 | $443 | $30.845 | $34.919 | qua |
| C · hộp lọc, cloud đếm | OAK 4 S | — | $29.605 | $449 | $30.861 | $34.989 | qua |

## 3. Độ vững

Quyết định giữ nguyên `done` ở 12/24 biến thể (tỷ lệ tiệm không WiFi 0/50/100%, 4G 100.000 hoặc 200.000 đ, 1 hoặc 2 camera mỗi tiệm, cloud đếm bằng CPU hoặc GPU 30 giây/ảnh như P03).

- **Cloud đếm bằng CPU (đo được, model hiện tại):** `done` ở 12/12 biến thể; C bằng 100,3–100,4% tổ hợp rẻ nhất.
- **Cloud đếm bằng GPU 30 giây/ảnh (giả định của P03):** `done` ở 0/12 biến thể; C bằng 112,1–123,6% tổ hợp rẻ nhất.

Khi cloud phải đếm bằng GPU, khoản GPU (khoảng $180/tháng ở P03) làm C đắt hơn D, vì D đếm ngay trên hộp. Con số đó giả định hộp chỉ có CPU vẫn kịp đếm 14 ảnh mỗi ngày với model nặng như vậy *(chưa kiểm chứng)*. Với model hiện tại (0,48 giây/ảnh trên CPU, báo cáo 17/10), biến thể CPU mới sát thực tế.

| Không WiFi | 4G/tháng | Camera/tiệm | Cloud đếm | Kết quả | C so với rẻ nhất | Rẻ nhất qua G1–G3 |
|---|---|---|---|---|---|---|
| 0% | 200.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $13.950 |
| 0% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 115,5% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $13.950 |
| 0% | 200.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.921 |
| 0% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 123,6% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.921 |
| 0% | 100.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $13.950 |
| 0% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 115,5% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $13.950 |
| 0% | 100.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.921 |
| 0% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 123,6% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.921 |
| 50% | 200.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $15.903 |
| 50% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 113,6% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $15.903 |
| 50% | 200.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $19.874 |
| 50% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 121,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $19.874 |
| 50% | 100.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $15.212 |
| 50% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 114,2% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $15.212 |
| 50% | 100.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $19.183 |
| 50% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 122,1% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $19.183 |
| 100% | 200.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.856 |
| 100% | 200.000 đ | 1 | GPU (P03) | `closed-fail` | 112,1% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $17.856 |
| 100% | 200.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $21.827 |
| 100% | 200.000 đ | 2 | GPU (P03) | `closed-fail` | 119,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $21.827 |
| 100% | 100.000 đ | 1 | CPU | `done` | 100,3% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $16.473 |
| 100% | 100.000 đ | 1 | GPU (P03) | `closed-fail` | 113,1% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $16.473 |
| 100% | 100.000 đ | 2 | CPU | `done` | 100,4% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $20.444 |
| 100% | 100.000 đ | 2 | GPU (P03) | `closed-fail` | 120,7% | D, CCTV 4K, ống 2,8 mm, mini PC N100: $20.444 |

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
| B | 2 MP có sẵn | 12,6–12,6 | trượt | bitrate tham khảo từ diễn đàn và trang hướng dẫn *(chưa kiểm chứng)* |
| B | CCTV 4K, ống 2,8 mm | 31,5–50,4 | trượt | bitrate tham khảo từ diễn đàn và trang hướng dẫn *(chưa kiểm chứng)* |
| B | CCTV 4K, ống 4 mm | 31,5–50,4 | trượt | bitrate tham khảo từ diễn đàn và trang hướng dẫn *(chưa kiểm chứng)* |
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

Đo trên 4 luồng CPU của máy long: 39 khung ở tiệm, mỗi khung đưa về đúng số điểm ảnh của camera 2 MP và của camera 4K (12 khung dọc 480×854 được phóng lên), quy đổi theo điểm Geekbench 6 đơn luồng. Hộp tính như chỉ có CPU. Bước lọc tìm mặt trên cả khung nên chậm dần theo số điểm ảnh.

| Khung | Nơi chạy | Lọc (ms/khung) | Đếm (ms/ảnh) | C: giây cho 60 khung mỗi mốc 15 phút | D: giây máy mỗi ngày | Giải mã HEVC phần cứng |
|---|---|---|---|---|---|---|
| 2,1 MP | Raspberry Pi 5 | 1.042 | 3.169 | 62,5 | 3.544 | có |
| 2,1 MP | mini PC N100 | 656 | 1.996 | 39,4 | 2.232 | có *(chưa kiểm chứng)* |
| 2,1 MP | Jetson Orin Nano Super | 986 | 3.000 | 59,2 | 3.355 | có *(chưa kiểm chứng)* |
| 2,1 MP | cloud (ml.c5.xlarge) | 697 | 2.120 | 41,8 | 2.371 | — |
| 8,3 MP | Raspberry Pi 5 | 3.712 | 3.170 | 222,7 | 12.518 | có |
| 8,3 MP | mini PC N100 | 2.338 | 1.996 | 140,3 | 7.884 | có *(chưa kiểm chứng)* |
| 8,3 MP | Jetson Orin Nano Super | 3.515 | 3.001 | 210,9 | 11.851 | có *(chưa kiểm chứng)* |
| 8,3 MP | cloud (ml.c5.xlarge) | 2.484 | 2.120 | 149,0 | 8.375 | — |

## 6. Rớt mạng (E6)

| Phương án | Camera | Bộ đệm | Chịu được (giờ mở cửa) |
|---|---|---|---|
| A | 2 MP có sẵn | 0 GB | mất ảnh ngay |
| A | CCTV 4K, ống 2,8 mm | 128 GB | trên 1.000 giờ *(chưa kiểm chứng: camera tự ghi vào thẻ khi rớt mạng và gửi bù khi có mạng lại)* |
| A | CCTV 4K, ống 4 mm | 128 GB | trên 1.000 giờ *(chưa kiểm chứng: camera tự ghi vào thẻ khi rớt mạng và gửi bù khi có mạng lại)* |
| B | 2 MP có sẵn | 0 GB | mất ảnh ngay |
| B | CCTV 4K, ống 2,8 mm | 128 GB | 36 giờ *(chưa kiểm chứng: camera tự ghi vào thẻ khi rớt mạng và gửi bù khi có mạng lại)* |
| B | CCTV 4K, ống 4 mm | 128 GB | 36 giờ *(chưa kiểm chứng: camera tự ghi vào thẻ khi rớt mạng và gửi bù khi có mạng lại)* |
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
- Bitrate video của B lấy từ diễn đàn người dùng và trang hướng dẫn, không phải từ hãng; B trượt G1 ở mọi bitrate trên 0,32 Mbps, nên kết luận về B không phụ thuộc con số này.
- Clip điện thoại quay cầm tay; clip MERL trong repo là bản đã vẽ khung chú thích, độ phân giải 640×472. Chỉ báo E4 chỉ mang tính tham khảo.
- Giá OAK 4 S theo P03 ($949): trang Luxonis không hiện giá ngày 27/10. Mini PC N100 (ZOTAC CI337 nano, 8 GB/256 GB) là hàng đặt trước ở Hacom và sắp về ở Tin Học Ngôi Sao; board Pi 5 8 GB hết hàng ở Cytron, còn ở hshop.vn. Mỗi hộp lấy giá cao hơn trong hai nguồn.
- Điện của camera mới và hộp tính ở công suất tối đa, chạy 24 giờ mỗi ngày, nên là cận trên.
- Không tính công lắp đặt, bảo trì, gán nhãn (hoang chốt 27/10).

## 9. Giả định

Giá, thông số và nguồn: `inputs/sources.csv`. Các giả định của kế hoạch (trường hợp gốc, lấy mức giá cao, quy đổi CPU, `ml.c5.xlarge`, 12 tuần = 2,8 tháng, bộ đệm khi rớt mạng): mục "Quyết định của kế hoạch" trong `docs/superpowers/plans/2026-10-27-p06-ingest-options.md`. Mô hình cloud là `docs/architecture/cost_model.py` của P03, nạp nguyên vẹn.
