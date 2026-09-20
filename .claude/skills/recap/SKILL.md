---
name: recap
description: Dùng khi kết thúc phiên làm việc, khi cửa sổ context sắp đầy, hoặc khi người dùng nói "recap", "chốt phiên", "lưu lại trước khi hết context". Viết file recap đúng chuẩn dự án milk-camera vào document_vault/Recap/, đủ bảy mục bắt buộc, để phiên sau làm tiếp được mà không quên việc đang dở.
---

# Viết recap

Recap là cơ chế bàn giao giữa hai phiên. Phiên sau chỉ có file này để biết phiên trước đã làm gì — viết cho người đọc chưa biết gì về phiên này.

## Bước 1 — lấy giờ thật

```bash
date "+%Y-%m-%d %H:%M"
```

**Bắt buộc chạy lệnh.** Không ước lượng, không lấy giờ nhớ từ đầu phiên. Giờ trong tên file, trong `created` và trong nội dung phải khớp nhau và khớp đồng hồ thật. Ghi sai giờ làm hỏng thứ tự sự kiện của cả dự án.

## Bước 2 — xác định bạn là ai

```bash
git config user.name
```

Đối chiếu bảng:

| git user.name chứa | mã | thư mục |
|---|---|---|
| hoang | HOANG | `hoang` |
| long | LONG | `long` |
| khang | KHANG | `khang` |
| nghi | NGHI | `nghi` |
| ngoc | NGOC | `ngoc` |
| nhat | NHAT | `nhat` |

Không khớp dòng nào thì **hỏi người dùng**, đừng đoán và đừng tự tạo thư mục tên khác.

## Bước 3 — dựng đường dẫn

```
document_vault/Recap/<thư mục>/<YYYY-MM-DD>/RECAP_<YYYY-MM-DD>_<HHMM>.md
```

Chưa có folder của ngày hôm đó thì tạo. Không ghi thẳng vào gốc `Recap/`.

## Bước 4 — viết đủ bảy mục

Không mục nào được để trống. Không có gì để ghi thì viết `không có` — khác với bỏ trống, vì bỏ trống khiến phiên sau không biết là "không có" hay là "quên ghi".

```markdown
# RECAP <YYYY-MM-DD> <HH:MM>

- owner: <mã người viết thường>
- created: <YYYY-MM-DD HH:MM +07:00>
- plan/ticket đang chạy: <ID, hoặc "không có">

## Đã đổi gì từ phiên trước
<Ba dòng: việc của người khác đã đổi gì mà phiên này cần biết. Đây là kết quả của bước 3 checklist đầu phiên.>

## Đã xong
<Việc hoàn tất trong phiên. Mỗi dòng một việc, kèm link bằng chứng nếu có.>

## Đang dở
<Chính xác đến lệnh đang chạy, job đang treo, file đang sửa giữa chừng. Mục này quyết định phiên sau nối tiếp được hay phải làm lại từ đầu.>

## Bước kế tiếp
<Việc đầu tiên của phiên sau. Viết như một mệnh lệnh cụ thể, không viết "tiếp tục nghiên cứu".>

## Quyết định đã chốt
<Kèm lý do. Để phiên sau không mở lại tranh luận đã xong.>

## Câu hỏi treo
<Đang chờ ai trả lời cái gì. Ghi rõ tên người.>

## File đã sửa
<Danh sách đường dẫn.>

## commit
<Hash sau khi push. Chưa push thì ghi "chưa push" và nói rõ vì sao.>
```

## Bước 5 — nhắc phần còn lại của việc chốt phiên

Sau khi ghi file, nhắc người dùng ba việc còn lại, và làm giúp nếu họ đồng ý:

1. Cập nhật `status`, `updated` và thêm dòng Nhật ký vào plan/ticket trên Confluence.
2. `git add` → `commit` → `push`, rồi điền commit hash vào mục `## commit` của recap vừa viết.
3. Cập nhật Google Sheet nếu trạng thái việc đã đổi.

## Ba lỗi hay gặp

- **Viết "đang dở" quá chung.** "Đang train model" là vô dụng. "Job `milk-det-03` chạy từ 14:20, epoch 12/50, log ở `runs/det03.log`, chờ val mAP > 0.6" mới dùng được.
- **Bỏ mục "Câu hỏi treo".** Câu hỏi không ghi ra thì phiên sau tự trả lời bừa hoặc tự đi làm lại.
- **Ghi giờ tròn cho đẹp.** 14:00 trong khi đồng hồ là 14:23 là làm hỏng thứ tự sự kiện. Chạy `date`.

Quy tắc đầy đủ: [Claude rule](https://traditional-milk.atlassian.net/wiki/x/B4AB) mục 7.
