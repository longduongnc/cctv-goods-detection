"""Step 3 of P05: a vision-language model as a second opinion on the hard groups. It only chooses inside the group
YOLO already named (the TH pair or the Sữa hạt four), never from the hand label."""
import re
import time
import unicodedata

import cv2
import numpy as np
import torch
from PIL import Image

from bench.skus import NAME_VI, SUA_HAT, TH_PAIR

QUESTION = ("Đây là ảnh cắt một hộp sữa trên kệ cửa hàng. Đây là sản phẩm nào trong danh sách sau? "
            "Trả lời đúng một dòng trong danh sách, hoặc KHÔNG CHẮC nếu không đọc được.")
OCR_KEYWORDS = (("HANH NHAN", "TMP-MLK-VNM-08"), ("ME DEN", "TMP-MLK-VNM-09"), ("9 LOAI HAT", "TMP-MLK-VNM-10"),
                ("DAU NANH", "TMP-MLK-VNM-07"), ("IT DUONG", "TMP-MLK-TH-02"), ("CO DUONG", "TMP-MLK-TH-01"))


def candidates_for(unit) -> tuple[str, ...] | None:
    """The group YOLO named for this unit (TH pair or Sữa hạt), or None for the other SKUs. unit.label is not read."""
    if unit.yolo_sku in TH_PAIR:
        return TH_PAIR
    if unit.yolo_sku in SUA_HAT:
        return SUA_HAT
    return None


def plain(text: str) -> str:
    """Upper case, no accents (đ -> D), only letters and digits separated by single spaces."""
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").upper()
    return " ".join(re.findall(r"[A-Z0-9]+", text))


def parse_answer(text: str, candidates: tuple[str, ...]) -> str | None:
    """The candidate whose full name (NAME_VI) the answer contains; None for KHÔNG CHẮC or any other answer."""
    answer = plain(text)
    if "KHONG CHAC" in answer:
        return None
    hits = [c for c in candidates if plain(NAME_VI[c]) in answer]
    return hits[0] if len(hits) == 1 else None


def sku_from_ocr(text: str, candidates: tuple[str, ...]) -> str | None:
    """The SKU of the first keyword found in the OCR text (in the order of OCR_KEYWORDS), if it is a candidate."""
    words = plain(text)
    for keyword, sku in OCR_KEYWORDS:
        if keyword in words:
            return sku if sku in candidates else None
    return None


def prompt(candidates: tuple[str, ...]) -> str:
    return "\n".join([QUESTION] + [NAME_VI[c] for c in candidates])


def upscale(crop_rgb: np.ndarray, short: int = 448) -> Image.Image:
    """The crop enlarged (never shrunk) so that its short side is at least `short` pixels."""
    h, w = crop_rgb.shape[:2]
    s = max(1.0, short / min(h, w))
    return Image.fromarray(cv2.resize(crop_rgb, (round(w * s), round(h * s)), interpolation=cv2.INTER_CUBIC))


def tight_crop(frame_bgr: np.ndarray, box: tuple[int, int, int, int], margin: float = 0.06) -> np.ndarray:
    """The box (x, y, w, h) with the margin of crop_unit but no grey square around it, as RGB."""
    x, y, w, h = box
    m = margin * max(w, h)
    xa, ya = int(max(np.floor(x - m), 0)), int(max(np.floor(y - m), 0))
    xb, yb = int(min(np.ceil(x + w + m), frame_bgr.shape[1])), int(min(np.ceil(y + h + m), frame_bgr.shape[0]))
    return np.ascontiguousarray(frame_bgr[ya:yb, xa:xb, ::-1])


class QwenVL:
    def __init__(self, model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct", device: str = "cuda"):
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id, dtype=torch.bfloat16).to(device).eval()

    @torch.no_grad()
    def choose(self, crop_rgb: np.ndarray, candidates: tuple[str, ...]) -> tuple[str | None, str, float]:
        """(SKU or None, the model's own answer, ms for this crop)."""
        t = time.perf_counter()
        image = upscale(crop_rgb)
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt(candidates)}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt").to(self.model.device)
        out = self.model.generate(**inputs, max_new_tokens=48, do_sample=False)
        answer = self.processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
        return parse_answer(answer, candidates), answer, (time.perf_counter() - t) * 1000


class Florence:
    def __init__(self, model_id: str = "microsoft/Florence-2-large", device: str = "cuda"):
        from transformers import AutoProcessor, Florence2ForConditionalGeneration
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = Florence2ForConditionalGeneration.from_pretrained(model_id, dtype=torch.float16).to(device).eval()

    @torch.no_grad()
    def ocr(self, crop_rgb: np.ndarray) -> tuple[str, float]:
        """(text read with the <OCR> task, ms for this crop)."""
        t = time.perf_counter()
        inputs = self.processor(text="<OCR>", images=upscale(crop_rgb), return_tensors="pt").to(self.model.device, torch.float16)
        out = self.model.generate(**inputs, max_new_tokens=64, do_sample=False, num_beams=3)
        text = self.processor.batch_decode(out, skip_special_tokens=True)[0]
        return text.strip(), (time.perf_counter() - t) * 1000
