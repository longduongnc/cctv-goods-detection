"""The P05 tables: the six indicators of every model on the real units, each rate as "xx,x% (lo–hi)" with its 95% Wilson
interval, and McNemar against YOLO and against the grey-fixed DB on the same units.

    .venv/bin/python -m bench.report            # writes results/summary.md
"""
import csv
from pathlib import Path

from bench.metrics import rate
from bench.run_zeroshot import file_name
from bench.stats import mcnemar_exact

HERE = Path(__file__).resolve().parents[1]           # arch_bench/
BASES = (("yolo", "YOLO"), ("db_greyfix", "DB sửa grey"))
GROUPS = (("acc", "1. Đúng"), ("th", "Cặp TH"), ("suahat", "Sữa hạt"), ("neg_rej", "2. Loại hàng lạ"),
          ("h_lt40", "4. <40 px"), ("h_40_60", "40–60"), ("h_60_90", "60–90"), ("h_ge90", "≥90"))


def pct(k, n) -> str:
    """xx,x% (lo–hi) with the 95% Wilson interval; — when there is nothing to count."""
    if not n or not int(n):
        return "—"
    k, n, lo, hi = rate(int(k), int(n))
    return f"{100 * k / n:.1f}% ({100 * lo:.1f}–{100 * hi:.1f})".replace(".", ",")


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _right(path, answer="answer"):
    """{unit: answered right} for the units with a SKU label marked khá or chắc."""
    return {r["id"]: r[answer] == r["label"] for r in _read(path)
            if r["label"].startswith("TMP-MLK-") and r["confidence"] in ("khá", "chắc")}


def mcnemar_cell(model: dict, base: dict) -> str:
    """b: right only with the model, c: right only with the baseline, over the units both were scored on."""
    shared = model.keys() & base.keys()
    b = sum(model[u] and not base[u] for u in shared)
    c = sum(base[u] and not model[u] for u in shared)
    p = mcnemar_exact(b, c)
    mark = " — hơn rõ" if p < 0.05 and b > c else " — kém rõ" if p < 0.05 and c > b else ""
    return f"b={b}, c={c}, p={p:.3f}".replace(".", ",") + mark


def _new_sku(row, finetune):
    """Indicator 3: for a fine-tuned run its three held-out SKUs, otherwise the HILO photos."""
    if row["encoder"].startswith("ft:") and (row["encoder"][3:], row["gallery"]) in finetune:
        f = finetune[row["encoder"][3:], row["gallery"]]
        return (f"3 SKU bỏ ra — thật {pct(f['holdout_real_k'], f['holdout_real_n'])}; "
                f"mô phỏng {pct(f['holdout_synth_k'], f['holdout_synth_n'])}")
    if row.get("hilo_reject_before"):
        before, after = float(row["hilo_reject_before"]), float(row["hilo_acc_after"])
        return f"HILO: không nhầm thành TH {round(6 * before)}/6, nhận đúng sau khi thêm {round(6 * after)}/6"
    return "—"


def _table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows]


def summarize(results_dir: Path) -> str:
    results = Path(results_dir)
    preds = results / "preds"
    bases = {name: _right(preds / f"{name}__pipeline.csv") for name, _ in BASES if (preds / f"{name}__pipeline.csv").exists()}
    finetune = {(r["run"], r["gallery"]): r for r in _read(results / "finetune.csv")} if (results / "finetune.csv").exists() else {}
    rows = []
    for r in _read(results / "zeroshot.csv"):
        path = preds / f"{file_name(r['encoder'])}__{r['gallery']}.csv"
        mine = _right(path) if path.exists() else {}
        rows.append([r["encoder"], r["gallery"]] + [pct(r.get(f"{g}_k"), r.get(f"{g}_n")) for g, _ in GROUPS]
                    + [_new_sku(r, finetune), f"{r['ms_gpu']} / {r['ms_cpu']}".replace(".", ",") if r.get("ms_gpu") else "—",
                       r.get("license") or "—"]
                    + ["—" if name == r["encoder"] or name not in bases or not mine else mcnemar_cell(mine, bases[name])
                       for name, _ in BASES])
    header = (["Model", "Kho"] + [t for _, t in GROUPS] + ["3. SKU mới", "5. ms mỗi hộp GPU / CPU", "6. License"]
              + [f"so với {t}" for _, t in BASES])
    lines = ["# P05 — bảng tổng hợp", "",
             "Mỗi tỷ lệ: tỷ lệ (khoảng tin cậy 95% Wilson). Chỉ số 1 và 4 tính trên các hộp thật có nhãn khá/chắc; một hộp "
             "không có câu trả lời (kNN ra none, dưới ngưỡng mô phỏng) tính là sai. McNemar trên cùng các hộp: b = model đúng "
             "mà mốc sai, c = ngược lại; \"hơn rõ\" khi p < 0,05 và b > c.", ""] + _table(header, rows)
    if (results / "vlm.csv").exists():
        vrows = []
        for v in _read(results / "vlm.csv"):
            mine = _right(preds / f"vlm_{v['model']}.csv", answer="pred")
            same = {"yolo": _right(preds / "vlm_yolo.csv", answer="pred"), "db_greyfix": bases.get("db_greyfix", {})}
            vrows.append([v["model"], v["n"], v["answered"], pct(v["right"], v["n"]), pct(v["right"], v["answered"]),
                          v["ms_per_crop"].replace(".", ",") or "—"]
                         + ["—" if v["model"] == name else mcnemar_cell(mine, {u: same[name][u] for u in mine if u in same[name]})
                            for name, _ in BASES])
        lines += ["", "## VLM ý kiến thứ hai (hộp YOLO gọi vào cặp TH hoặc nhóm Sữa hạt)", ""]
        lines += _table(["Model", "Hộp", "Trả lời", "1. Đúng (không trả lời = sai)", "Đúng trong số trả lời", "ms mỗi hộp"]
                        + [f"so với {t}" for _, t in BASES], vrows)
    return "\n".join(lines) + "\n"


def main():
    out = HERE / "results" / "summary.md"
    out.write_text(summarize(HERE / "results"), encoding="utf-8")
    print("written", out.relative_to(HERE))


if __name__ == "__main__":
    main()
