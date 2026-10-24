# Tài nguyên dùng chung

Máy train, GPU, tài khoản có hạn mức. Ai định chạy job dài hơn 30 phút thì **ghi vào bảng dưới trước khi chạy**, và xoá dòng khi xong.

Không ghi thì người khác sẽ xếp job chồng lên và cả hai cùng chậm. Ở dự án trước việc này từng làm trễ gần hai tiếng.

## Đang giữ

| Người | Tài nguyên | Từ | Dự kiến tới | Job | Ghi chú |
|---|---|---|---|---|---|
| hoang | Máy GPU của long — GPU, tối đa 22 GB RAM | 2026-10-24 10:49 +07:00 | xong 2026-10-24 12:12 +07:00 | Train lại embedder 12 loại sau khi sửa lỗi `grey` trong augmentation, build lại DB, chạy lại CV Output mẫu và 10 clip để so A/B | **Đã xong, để lại dòng này một phiên cho team thấy.** Mọi thứ nằm trong `carton_recognition_greyfix/` (467 MB); model đang dùng không bị đụng |
| hoang | Máy GPU của long — GPU (tối đa ~10 GB VRAM), tối đa 20 GB RAM | 2026-10-24 15:50 +07:00 | xong 2026-10-24 17:11 +07:00 | HOANG-P05 bước 1: chấm 8 encoder × 3 kho ảnh mẫu trên hộp thật (unit `p05-zeroshot`, thư mục `arch_bench/`) | **Đã xong, để lại dòng này một phiên cho team thấy.** 16:46 dừng để sửa cách đo thời gian của SigLIP/CLIP, 16:59 chạy lại phần còn lại |
| hoang | Máy GPU của long — GPU (SigLIP 2 so400m chiếm ~30 GB VRAM, chỉ còn chưa tới 1 GB trống), mỗi lần tối đa 22 GB RAM, ~40 GB đĩa tạm trong `arch_bench/data/mmap/` | 2026-10-24 17:23 +07:00 | ước tính 2026-10-25 05:00 +07:00 (đã đo: DINOv2-S ~30 phút/lần, SigLIP 2 base 45–55 phút/lần, so400m 23,5 phút/epoch nên ~4 giờ/lần; chấm và đo lại thời gian thêm ~1 giờ 15) | HOANG-P05 bước 2: 6 lần fine-tune nối tiếp (DINOv2-S, SigLIP 2 base, SigLIP 2 so400m; mỗi model một lần đủ 12 SKU và một lần bỏ 3 SKU), unit `p05-ft-chain` gọi từng unit `p05-ft-<run>`; 4/6 lần đã xong và đã chấm. Khi chuỗi xong, unit `p05-ft-final` tự chấm 2 checkpoint so400m (`p05-ft-eval`, kho kiểu build_db 43 GB trong `arch_bench/data/cache/`), đo lại thời gian mọi encoder (`p05-retime`) và dựng bảng (`p05-report`). 17:31–17:57 dừng chuỗi để chạy VLM (bước 3) | Nice 10, OOMScoreAdjust 1000. long cần GPU gấp thì dừng được: `systemctl --user stop p05-ft-final p05-ft-chain p05-ft-<run>`; chạy lại chain thì nó bỏ qua lần đã xong |

## Cách ghi

- Giờ dạng `YYYY-MM-DD HH:MM +07:00`, lấy từ đồng hồ hệ thống.
- "Dự kiến tới" cứ ước lượng, sai thì sửa — có con số vẫn hơn để trống.
- Job chạy quá giờ dự kiến mà chưa xong thì sửa lại dòng, đừng để người khác tưởng máy đã trống.
- Xong thì **xoá dòng**, và nếu đáng nhớ thì ghi vào Nhật ký của ticket liên quan.

## Tài nguyên đã biết

| Tài nguyên | Ai quản | Ghi chú |
|---|---|---|
| *(chưa liệt kê — điền khi team chốt máy train)* | | |
