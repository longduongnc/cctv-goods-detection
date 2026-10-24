import csv

from bench.report import pct, summarize
from bench.run_zeroshot import COLUMNS

RIGHT = "TMP-MLK-VNM-01"


def _preds(path, answers):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "confidence", "height", "pred", "top1", "answer"])
        for uid, answer in answers.items():
            w.writerow([uid, RIGHT, "khá", 50, answer, "", answer])


def _results(tmp_path):
    (tmp_path / "preds").mkdir()
    # A is right on u1-u4; yolo on u1-u2; the two answer differently on u3, u4 and u5
    _preds(tmp_path / "preds" / "enc__renders.csv",
           {"u1": RIGHT, "u2": RIGHT, "u3": RIGHT, "u4": RIGHT, "u5": "TMP-MLK-VNM-02"})
    _preds(tmp_path / "preds" / "yolo__pipeline.csv",
           {"u1": RIGHT, "u2": RIGHT, "u3": "TMP-MLK-VNM-03", "u4": "TMP-MLK-VNM-03", "u5": "TMP-MLK-VNM-04"})
    with open(tmp_path / "zeroshot.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        w.writeheader()
        w.writerow(dict(encoder="yolo", gallery="pipeline", acc=0.4, acc_k=2, acc_n=5))
        w.writerow(dict(encoder="enc", gallery="renders", acc=0.8, acc_k=4, acc_n=5, license="apache-2.0"))
    return tmp_path


def test_rates_are_written_with_a_comma_and_their_interval():
    assert pct(4, 5).startswith("80,0% (")
    assert pct(0, 0) == "—"


def test_the_table_compares_each_model_with_yolo_on_the_same_units(tmp_path):
    md = summarize(_results(tmp_path))
    row = next(line for line in md.splitlines() if line.startswith("| enc "))
    assert "80,0% (" in row
    assert "b=2, c=0" in row
    assert "hơn rõ" not in row                      # p = 0,5 with two discordant units


def test_a_clear_win_is_marked(tmp_path):
    results = _results(tmp_path)
    many = {f"u{i}": RIGHT for i in range(20)}
    _preds(results / "preds" / "enc__renders.csv", many)
    _preds(results / "preds" / "yolo__pipeline.csv", {k: "TMP-MLK-VNM-02" for k in many})
    row = next(line for line in summarize(results).splitlines() if line.startswith("| enc "))
    assert "b=20, c=0" in row
    assert "hơn rõ" in row
