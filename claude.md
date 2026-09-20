# Hướng dẫn cho agent — dự án milk-camera

Nhận diện hàng hoá (sữa) từ camera cửa hàng tạp hoá, cho đối tác Datagent.
Sáu người, mỗi người một agent Claude, làm song song. Đọc hết file này trước khi làm gì.

## Nguồn sự thật

Quy tắc đầy đủ nằm trên Confluence, **không** nằm trong file này. File này chỉ là lối vào.

| Trang | content_id | Đọc khi nào |
|---|---|---|
| Claude rule (v2.1) | `98311` | Đầu mỗi phiên, bắt buộc |
| Project info | `327685` | Lần đầu vào dự án |
| Project plan | `131382` | Đầu phiên, để biết hướng |
| Cách dùng — RoadMap | `98529` | Trước khi tạo plan đầu tiên |
| Cách dùng — Ticket | `65928` | Trước khi tạo ticket đầu tiên |
| Cách dùng — Research | `98546` | Trước khi tạo research đầu tiên |

Site: `traditional-milk.atlassian.net` · cloudId: `45a7eeea-8770-4e3c-aa1f-f015eb6c5515`

Đọc bằng MCP Atlassian: `getConfluenceContent` với `content_id` ở bảng trên.
Chưa nối MCP thì chạy:

```
claude mcp add --transport http --scope user atlassian https://mcp.atlassian.com/v2/mcp
```

rồi gõ `/mcp` để đăng nhập.

## Mỗi người một folder riêng

Trên Confluence, `document_vault` có ba folder mẹ, mỗi folder chia sáu folder con theo người.
**Chỉ tạo trang trong folder mang tên mình.**

| Người | Mã | RoadMap | Ticket | Research |
|---|---|---|---|---|
| Hoàng | `HOANG` | `131380` | `131507` | `328026` |
| Long | `LONG` | `98500` | `66211` | `98505` |
| Khang | `KHANG` | `98498` | `131509` | `328028` |
| Nghi | `NGHI` | `98496` | `66209` | `98503` |
| Ngọc | `NGOC` | `328024` | `131513` | `98507` |
| Nhật | `NHAT` | `131415` | `131511` | `65910` |

Tạo trang bằng `createConfluenceContent` với `parent: {"parentContentId": "<id folder của bạn>"}`.

Tên folder có dấu cho dễ đọc; mã trong ID không dấu để tìm kiếm và trích dẫn không lỗi font.

## Cái gì nằm ở đâu

- **Google Sheet** — chia việc, meeting note, kho đường link.
- **Confluence** — plan, ticket, research, quy tắc.
- **Repo này** — code và recap.

Việc và link → Sheet · suy nghĩ và quy tắc → Confluence · code và recap → repo.

## Đầu mỗi phiên — làm đủ năm bước rồi mới được sửa gì

1. `git pull`
2. Đọc recap gần nhất của chính mình trong `document_vault/Recap/<tên bạn>/`
3. Đọc plan và ticket của **người khác** đang `in-progress` hoặc `blocked`, cập nhật trong 48h
4. Mở Sheet xem việc của mình có đổi không
5. Ghi ba dòng "đã đổi gì từ phiên trước" vào đầu recap phiên này

Bước 3 dễ bị bỏ nhất và đắt nhất khi bỏ. Có folder riêng không có nghĩa là khỏi nhìn sang
folder người khác — ngược lại, folder riêng làm việc đó dễ bỏ quên hơn. Cách nhanh nhất là
đọc bảng chỉ mục ở ba trang *Cách dùng*, thay vì mở sáu folder.

## Cuối mỗi phiên

1. Cập nhật `status`, `updated`, thêm dòng Nhật ký vào plan/ticket đang chạy
2. Viết recap (dùng skill `recap`)
3. `git add` → `commit` → `push`, ghi commit hash vào recap
4. Cập nhật Sheet nếu trạng thái việc đã đổi

## Năm điều không được vi phạm

1. **Mốc giờ lấy từ đồng hồ hệ thống**, chạy `date` tại đúng lúc ghi. Dạng `YYYY-MM-DD HH:MM +07:00`. Không ước lượng, không nhớ từ đầu phiên.
2. **`status` là một token** trong: `draft` `approved` `in-progress` `blocked` `done` `closed-fail` `superseded`. Diễn biến viết vào mục Nhật ký, không viết vào `status`.
3. **Kết luận không có bằng chứng phải tự ghi `(chưa kiểm chứng)`.** Bằng chứng là output lệnh nguyên văn hoặc link nguồn, không phải tóm tắt theo trí nhớ.
4. **Không tạo và không sửa trang trong folder của người khác.** Cần đổi thì mở ticket trong folder của chính bạn, đặt `reviewer` là người đó.
5. **Thêm dòng vào bảng chỉ mục** ở trang *Cách dùng* mỗi khi mở hoặc đóng một trang. Đó là cách người khác biết bạn đang làm gì.

## ID

Plan `<MÃ>-P<nn>` · Ticket `<MÃ>-T<nnn>`. Đếm riêng từng người.
Ví dụ: `HOANG-P01 — Quy trình lấy dữ liệu tại cửa hàng`, `LONG-T003 — ...`

## Dữ liệu

Không commit ảnh/video thô quay tại cửa hàng, không commit key hay token. Chỉ ghi đường dẫn và cách truy cập. Dữ liệu cửa hàng có thể chứa mặt người và thông tin chủ quán.
