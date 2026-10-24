"""The licence of each model as its Hugging Face model card states it, kept in results/licenses.json."""
import json
from pathlib import Path

from huggingface_hub import model_info

CACHE = Path(__file__).resolve().parents[1] / "results" / "licenses.json"


def license_of(hf_id: str, cache: Path = CACHE) -> str:
    """The card's licence id (e.g. apache-2.0), or "unknown" when the card names none."""
    known = json.loads(cache.read_text()) if cache.exists() else {}
    if hf_id not in known:
        card = model_info(hf_id).card_data
        known[hf_id] = (card.license if card is not None and card.license else None) or "unknown"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True))
    return known[hf_id]
