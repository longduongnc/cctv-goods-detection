"""SKU codes, names and groups, copied from SKUS in long's carton_recognition/cv_output.py, and the hand labels."""
import unicodedata

KIND_TO_SKU = {
    "vinamilk_fresh_no_sugar": "TMP-MLK-VNM-01",
    "vinamilk_fresh_less_sugar": "TMP-MLK-VNM-02",
    "vinamilk_fresh_sweetened": "TMP-MLK-VNM-03",
    "vinamilk_chocolate": "TMP-MLK-VNM-04",
    "vinamilk_banana": "TMP-MLK-VNM-05",
    "vinamilk_melon": "TMP-MLK-VNM-06",
    "vinamilk_soy": "TMP-MLK-VNM-07",
    "vinamilk_soy_almond": "TMP-MLK-VNM-08",
    "vinamilk_soy_black_sesame": "TMP-MLK-VNM-09",
    "vinamilk_9_seeds": "TMP-MLK-VNM-10",
    "th_true_milk_sweetened": "TMP-MLK-TH-01",
    "th_true_milk_less_sugar": "TMP-MLK-TH-02",
}

NAME_VI = {
    "TMP-MLK-VNM-01": "Vinamilk 100% Sữa Tươi Tiệt Trùng Không Đường 180ml",
    "TMP-MLK-VNM-02": "Vinamilk 100% Sữa Tươi Tiệt Trùng Ít Đường 180ml",
    "TMP-MLK-VNM-03": "Vinamilk 100% Sữa Tươi Tiệt Trùng Có Đường 180ml",
    "TMP-MLK-VNM-04": "Vinamilk 100% Sữa Tươi Tách Béo Tiệt Trùng Sôcôla Đậm Đặc 180ml",
    "TMP-MLK-VNM-05": "Vinamilk 100% Sữa Tươi Tiệt Trùng Giảm Béo Chuối 180ml",
    "TMP-MLK-VNM-06": "Vinamilk 100% Sữa Tươi Tách Béo Tiệt Trùng Dưa Lưới 180ml",
    "TMP-MLK-VNM-07": "Vinamilk Sữa Đậu Nành Cao Canxi Ít Đường 180ml",
    "TMP-MLK-VNM-08": "Vinamilk Sữa Hạt Đậu Nành Hạnh Nhân Ít Đường 180ml",
    "TMP-MLK-VNM-09": "Vinamilk Sữa Hạt Đậu Nành Mè Đen Ít Đường 180ml",
    "TMP-MLK-VNM-10": "Vinamilk Sữa Hạt 9 Loại Hạt Ít Đường 180ml",
    "TMP-MLK-TH-01": "TH true MILK Sữa Tươi Tiệt Trùng Có Đường 180ml",
    "TMP-MLK-TH-02": "TH true MILK Sữa Tươi Tiệt Trùng Ít Đường 180ml",
}

SKU_CODES = tuple(f"TMP-MLK-VNM-{i:02d}" for i in range(1, 11)) + ("TMP-MLK-TH-01", "TMP-MLK-TH-02")
TH_PAIR = ("TMP-MLK-TH-01", "TMP-MLK-TH-02")
SUA_HAT = ("TMP-MLK-VNM-07", "TMP-MLK-VNM-08", "TMP-MLK-VNM-09", "TMP-MLK-VNM-10")
HOLDOUT = ("TMP-MLK-TH-02", "TMP-MLK-VNM-09", "TMP-MLK-VNM-05")
HILO = "TMP-MLK-TH-HILO"          # TH true MILK HILO 180 ml: the 13th SKU, known only from iPhone photos

_SPECIAL = {"CĐ": "TMP-MLK-TH-01", "ÍĐ": "TMP-MLK-TH-02", "TH-khác": "NEG", "khác": "NEG", "?": "AMBIG", "x": "SKIP", "lệch": "SKIP"}


def normalize_label(raw: str) -> str:
    """A hand label (CĐ, ÍĐ, VNM-05, TH-khác, ?, x, lệch …) as a SKU code, or NEG, AMBIG or SKIP."""
    text = unicodedata.normalize("NFC", raw.strip())
    if text in _SPECIAL:
        return _SPECIAL[text]
    code = text if text.startswith("TMP-MLK-") else "TMP-MLK-" + text
    if code in SKU_CODES:
        return code
    raise ValueError(f"unknown label: {raw!r}")
