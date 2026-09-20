# document_vault

Nơi chứa recap của từng người. Mọi thứ khác đã chuyển lên Confluence từ bản rule v2.0 (20/09/2026).

## Cấu trúc

```
document_vault/
  Recap/<tên>/<YYYY-MM-DD>/RECAP_<YYYY-MM-DD>_<HHMM>.md
  RESOURCES.md
```

`<tên>` là một trong: `hoang` `long` `khang` `nghi` `ngoc` `nhat`.

Chưa có folder của ngày hôm đó thì tạo mới. **Không ghi thẳng vào gốc `Recap/`.**

## Không còn ở đây nữa

| Trước ở vault | Giờ ở |
|---|---|
| RoadMap | [Confluence — RoadMap](https://traditional-milk.atlassian.net/wiki/spaces/~7120204f8c1fdfbeb646c882494b9ab507ea3f/pages/98529/RoadMap) |
| Ticket | [Confluence — Ticket](https://traditional-milk.atlassian.net/wiki/spaces/~7120204f8c1fdfbeb646c882494b9ab507ea3f/pages/65928/Ticket) |
| Research | [Confluence — Research](https://traditional-milk.atlassian.net/wiki/spaces/~7120204f8c1fdfbeb646c882494b9ab507ea3f/pages/98546/Research) |

Lý do: ba loại đó cần người khác nhìn thấy ngay và bình luận được, không nên bắt cả team `git pull` mới biết nhau đang làm gì. Recap ở lại repo vì mỗi ngày sinh ra nhiều file và chỉ agent của chính người đó đọc.

Quy tắc đầy đủ: [Claude rule](https://traditional-milk.atlassian.net/wiki/x/B4AB).

## Viết recap

Dùng skill `recap` (`.claude/skills/recap/`). Nó tự lấy giờ hệ thống, tự dựng đường dẫn và ép đủ bảy mục bắt buộc.
