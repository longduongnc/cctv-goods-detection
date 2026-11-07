"""Kiểm hàm chi phí giai đoạn đầu của HOANG-P07: python -m pytest docs/architecture/test_cost_phase1.py -q"""
import cost_phase1 as c


CTX = c.load_context()


def total(bill):
    return sum(sum(group.values()) for group in bill.values())


def test_full_stack_reproduces_p06_at_30_stores():
    assert round(total(c.path_bill(CTX, "C", 30)), 2) == 239.36  # results/cost.csv, cloud_usd của C trường hợp gốc


def test_video_reproduces_p06_at_30_stores():
    assert round(total(c.path_bill(CTX, "B", 30)), 2) == 1591.92


def test_full_stack_at_4_stores():
    assert round(total(c.path_bill(CTX, "C", 4)), 2) == 231.24


def test_hoang_cut_removes_only_the_three_security_lines():
    full = c.path_bill(CTX, "C", 4)
    cut = c.hoang_cut(full)
    removed = total(full) - total(cut)
    assert round(removed, 2) == 60.62  # GuardDuty 10,62 + Security Hub 15 + Config 35
    assert set(cut["8 Bảo mật"]) == {"KMS (6 khoá + 6 bản sao Osaka) + Secrets", "CloudWatch (20 GB log, 100 metric, 20 alarm)"}


def test_phase1_keeps_data_path_lines_and_is_cheaper_than_the_cut():
    full = c.path_bill(CTX, "C", 4)
    phase1 = c.phase1_bill(CTX, 4)
    for group in ("1 Thu nhận", "2 Xử lý", "3 Kết quả", "4 Lưu trữ", "5 Sao lưu Osaka"):
        assert phase1[group] == full[group]
    assert total(phase1) < total(c.hoang_cut(full))


def test_phase1_train_is_cvat_on_demand_plus_p03_training():
    assert round(sum(c.phase1_bill(CTX, 4)["6 Train"].values()), 2) == round(40 * 0.2604 + 20 * 1.634, 2)


def test_phase1_without_cloud_training_drops_only_the_training_line():
    with_train, without = c.phase1_bill(CTX, 4), c.phase1_bill(CTX, 4, cloud_training=False)
    assert round(total(with_train) - total(without), 2) == round(20 * 1.634, 2)


def test_essentials_is_the_four_data_groups_only():
    assert set(c.essentials(c.path_bill(CTX, "C", 4))) == {"1 Thu nhận", "2 Xử lý", "3 Kết quả", "4 Lưu trữ"}
    assert round(total(c.essentials(c.path_bill(CTX, "C", 4))), 2) == 6.15


def test_outside_aws_box_price_comes_from_p06_sources():
    out = c.outside_aws(CTX, stores=4, no_wifi_share=0.5)
    assert round(out["hộp"], 2) == round(4 * 5_599_000 / 26_040, 2)
    assert round(out["router 4G"], 2) == round(2 * 990_000 / 26_040, 2)


def test_counting_line_is_labelled_by_the_machine_it_is_priced_on():
    assert "SageMaker Async ml.c5.xlarge (CPU)" in c.path_bill(CTX, "C", 4)["2 Xử lý"]
    assert "SageMaker Async ml.g6.xlarge" in c.path_bill(CTX, "C", 4, processing="gpu_p03")["2 Xử lý"]


def test_phase1_on_the_video_path_keeps_the_video_lines():
    assert "KVS ghi video" in c.phase1_bill(CTX, 4, option="B")["1 Thu nhận"]


def test_store_count_is_restored_after_a_call():
    before = CTX.costs.N_STORES
    c.path_bill(CTX, "C", 4)
    assert CTX.costs.N_STORES == before
