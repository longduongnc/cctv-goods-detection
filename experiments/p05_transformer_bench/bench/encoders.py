"""Image encoders behind one interface: uint8 RGB crops (n, S, S, 3) in, unit-length float32 vectors (n, d) out.
Batches of 64, fp16 autocast on CUDA. Models download into the Hugging Face cache on the GPU machine."""
import importlib.util
import sys
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import torch

DATAGENT = Path(__file__).resolve().parents[2]
FT_DIR = Path(__file__).resolve().parents[1] / "data" / "ft"
BATCH = 64
TIMM = {
    "dinov2_s": "vit_small_patch14_reg4_dinov2.lvd142m",
    "dinov2_b": "vit_base_patch14_reg4_dinov2.lvd142m",
    "dinov2_l": "vit_large_patch14_reg4_dinov2.lvd142m",
}
HF = {
    "siglip2_b": "google/siglip2-base-patch16-224",
    "siglip2_so400m": "google/siglip2-so400m-patch14-384",
    "clip_l": "openai/clip-vit-large-patch14",
}
CARTON = {
    "long_ft": DATAGENT / "carton_recognition" / "embedder_types.pt",
    "greyfix_ft": DATAGENT / "carton_recognition_greyfix" / "embedder_types.pt",
}
NAMES = tuple(TIMM) + tuple(HF) + tuple(CARTON)
HF_ID = {**{n: f"timm/{m}" for n, m in TIMM.items()}, **HF,
         **{n: f"timm/{TIMM['dinov2_s']}" for n in CARTON}}              # whose licence an encoder carries


class Encoder(Protocol):
    name: str

    def embed(self, crops: np.ndarray) -> np.ndarray: ...


def _long_embedder():
    """long's carton_recognition/embedder.py (CartonNet), imported without writing caches into his folder."""
    if "long_embedder" not in sys.modules:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("long_embedder", DATAGENT / "carton_recognition" / "embedder.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["long_embedder"] = module
    return sys.modules["long_embedder"]


class _Encoder:
    """Batching, autocast and normalising; subclasses turn a batch of crops into features."""

    def __init__(self, name, device):
        self.name, self.device = name, device

    @torch.no_grad()
    def embed(self, crops):
        out = []
        for i in range(0, len(crops), BATCH):
            with torch.autocast("cuda", dtype=torch.float16, enabled=self.device.startswith("cuda")):
                f = self._features(np.asarray(crops[i:i + BATCH]))
            out.append(torch.nn.functional.normalize(f.float(), dim=-1).cpu().numpy())
        return np.concatenate(out)


class _Square(_Encoder):
    """Models that take a size x size RGB square with ImageNet statistics: resize with cv2, as crop_box does."""
    size = 224
    mean = np.array([0.485, 0.456, 0.406], np.float32)
    std = np.array([0.229, 0.224, 0.225], np.float32)

    def _input(self, crops):
        if crops.shape[1] != self.size:
            how = cv2.INTER_AREA if crops.shape[1] > self.size else cv2.INTER_CUBIC
            crops = np.stack([cv2.resize(c, (self.size, self.size), interpolation=how) for c in crops])
        x = (crops.astype(np.float32) / 255 - self.mean) / self.std
        return torch.from_numpy(np.ascontiguousarray(x.transpose(0, 3, 1, 2))).to(self.device)


class TimmDino(_Square):
    """DINOv2 with the pooling of CartonNet (summary token next to the mean of the patch tokens), no projection."""

    def __init__(self, name, model_id, device):
        super().__init__(name, device)
        import timm
        self.model = timm.create_model(model_id, pretrained=True, num_classes=0, img_size=self.size).to(device).eval()

    def _features(self, crops):
        t = self.model.forward_features(self._input(crops))
        n = self.model.num_prefix_tokens
        return torch.cat([t[:, 0], t[:, n:].mean(1)], dim=-1)


class Carton(_Square):
    """A CartonNet checkpoint of train_embedder.py. Takes RGB crops: no channel flip here (long's Embedder flips
    because it is fed BGR)."""

    def __init__(self, name, checkpoint, device):
        super().__init__(name, device)
        self.model = _long_embedder().CartonNet(pretrained=False)
        self.model.load_state_dict(torch.load(checkpoint, map_location="cpu")["weights"])
        self.model.to(device).eval()

    def _features(self, crops):
        return self.model(self._input(crops))


class HFImage(_Square):
    """A Hugging Face image-text model at the input size and statistics of its own processor, resized with cv2 like
    the timm models (the processor itself took 30-60 ms a crop on the CPU, which the timing would have charged to
    the model); get_image_features pools."""

    def __init__(self, name, hf_id, device):
        super().__init__(name, device)
        from transformers import AutoImageProcessor, AutoModel
        p = AutoImageProcessor.from_pretrained(hf_id)
        self.size = (getattr(p, "crop_size", None) or p.size).height          # CLIP crops to 224, SigLIP resizes
        self.mean, self.std = np.array(p.image_mean, np.float32), np.array(p.image_std, np.float32)
        self.model = AutoModel.from_pretrained(hf_id).to(device).eval()

    def _features(self, crops):
        f = self.model.get_image_features(pixel_values=self._input(crops))
        return f if isinstance(f, torch.Tensor) else f.pooler_output


def checkpoint_path(name: str) -> Path:
    """The checkpoint of an encoder named "ft:<run>" (data/ft/<run>/embedder.pt) or "ft:<path to a .pt file>"."""
    spec = name[3:]
    return Path(spec) if spec.endswith(".pt") else FT_DIR / spec / "embedder.pt"


class FineTuned(_Square):
    """A checkpoint of bench/finetune.py, fed at its training size with its backbone's statistics."""

    def __init__(self, name, path, device):
        super().__init__(name, device)
        from bench.finetune import FtNet
        state = torch.load(path, map_location="cpu")
        self.model = FtNet(state["backbone"], pretrained=False)
        self.model.load_state_dict(state["weights"])
        self.model.to(device).eval()
        self.size = state["size"]
        self.mean, self.std = np.array(state["mean"], np.float32), np.array(state["std"], np.float32)

    def _features(self, crops):
        return self.model(self._input(crops))


def licence_id(name: str) -> str:
    """The model card an encoder's licence is read from; a fine-tuned checkpoint carries its backbone's."""
    if name.startswith("ft:"):
        state = torch.load(checkpoint_path(name), map_location="cpu")
        return state["backbone"] if state["backbone_kind"] == "hf" else f"timm/{state['backbone']}"
    return HF_ID[name]


def make_encoder(name: str, device: str) -> Encoder:
    if name.startswith("ft:"):
        return FineTuned(name, checkpoint_path(name), device)
    if name in TIMM:
        return TimmDino(name, TIMM[name], device)
    if name in HF:
        return HFImage(name, HF[name], device)
    if name in CARTON:
        return Carton(name, CARTON[name], device)
    raise ValueError(f"unknown encoder {name!r}; known: {', '.join(NAMES)}")
