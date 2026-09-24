"""Ước tính chi phí AWS hằng tháng cho milk-camera — kiến trúc đếm tồn kho (HOANG-P03).

Bản cho kiến trúc cũ (video + bắt lần mua, HOANG-P02) nằm ở commit 518eeae.

Giá: AWS Price List API, On-Demand, USD, chưa thuế. Tokyo (ap-northeast-1), Osaka (ap-northeast-3).
     https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<Service>/current/<region>/index.json
     Mỗi dòng giá ghi usagetype và ngày công bố bảng giá để tra lại.
Giả định: toàn bộ nằm trong ASSUMPTIONS — đổi ở đó rồi chạy lại.
Chạy: python cost_model.py
"""

H = 730      # giờ / tháng (AWS dùng 730)
D = 30       # ngày / tháng

# ---- GIÁ (usagetype · ngày công bố bảng giá) ----
P = {
    # xử lý + train (SageMaker 2026-09-23)
    "sm_async_g6_h":      1.6341,      # APN1-AsyncInf:ml.g6.xlarge
    "sm_train_g6_h":      1.634,       # APN1-Train:ml.g6.xlarge
    # máy cho CVAT (EC2 2026-09-21)
    "m7i.xlarge_h":       0.2604,      # APN1-BoxUsage:m7i.xlarge
    # serverless
    "lambda_gbs":         0.0000166667,  # APN1-Lambda-GB-Second tier 1
    "lambda_req":         0.0000002,   # APN1-Request
    "sqs_req":            0.0000004,   # APN1-Requests-Tier1
    "iot_conn_min":       0.000000096, # APN1-ConnectionMinutes
    "iot_msg":            0.0000012,   # APN1-Messages (1 tỷ đầu)
    "firehose_iceberg_gb": 0.093,      # APN1-IcebergTablesBilledBytes tier 1
    # lưu trữ (S3 2026-09-18)
    "s3_gbmo":            0.025,       # APN1-TimedStorage-ByteHrs (50 TB đầu); Osaka APN3 cùng giá
    "s3_put":             0.0000047,   # APN1-Requests-Tier1 (Osaka APN3 cùng giá)
    "s3_get":             0.00000037,  # APN1-Requests-Tier2
    "s3tables_gbmo":      0.0288,      # APN1-Tables-TimedStorage-ByteHrs (Osaka APN3 cùng giá)
    "s3tables_repl_upd":  0.00001,     # APN1-Tables-Replication-TableUpdates
    "xregion_gb":         0.09,        # APN1-APN3-AWS-Out-Bytes (DataTransfer 2026-09-16): Tokyo → Osaka
    "ddb_wru":            0.000000715, # APN1-WriteRequestUnits
    "ddb_rru":            0.0000001425,  # APN1-ReadRequestUnits
    "athena_tb":          5.0,         # APN1-DataScannedInTB
    "ecr_gbmo":           0.10,        # APN1-TimedStorage-ByteHrs (ECR)
    "dt_out_gb":          0.114,       # APN1-DataTransfer-Out-Bytes (10 TB đầu)
    # website
    "amplify_req":        0.0000003,   # APN1-HostingComputeRequestCount
    "amplify_gbs":        0.0000555556,  # APN1-HostingComputeRequestDuration
    "apigw_http_req":     0.00000129,  # APN1-ApiGatewayHttpRequest
    "waf_acl_mo":         5.0,         # APN1-WebACL
    "waf_rule_mo":        1.0,         # APN1-Rule
    "waf_req":            0.0000006,   # APN1-Request
    "cognito_mau":        0.015,       # APN1-CognitoEssentialsMAU
    # bảo mật + giám sát
    "gd_ct_event":        0.00000472,  # APN1-PaidEventsAnalyzed
    "gd_flow_gb":         1.18,        # APN1-PaidEventsAnalyzed-Bytes (500 GB đầu)
    "sechub_check":       0.001,       # APN1-PaidComplianceCheck (100k đầu)
    "config_ci":          0.003,       # APN1-ConfigurationItemRecorded
    "config_eval":        0.001,       # APN1-ConfigRuleEvaluations (100k đầu)
    "kms_key_mo":         1.0,         # ap-northeast-1-KMS-Keys (khoá bản sao ở Osaka tính như một khoá)
    "kms_req":            0.000003,    # ap-northeast-1-KMS-Requests
    "secret_mo":          0.40,        # APN1-AWSSecretsManager-Secrets
    "cw_log_gb":          0.76,        # APN1-DataProcessing-Bytes (CloudWatch Logs)
    "cw_metric_mo":       0.30,        # APN1-CW:MetricMonitorUsage (10k đầu)
    "cw_alarm_mo":        0.10,        # APN1-CW:AlarmMonitorUsage
}

# ---- GIẢ ĐỊNH (chưa kiểm chứng — đổi ở đây) ----
ASSUMPTIONS = {
    "open_hours_per_day": 14,      # giờ tiệm mở cửa
    "capture_every_min": 15,       # camera chụp mỗi 15 phút
    "people_drop": 0.20,           # tỉ lệ ảnh bị bỏ tại camera vì có người che kệ
    "still_mb": 10,                # JPEG 48 MP của OAK 4 S — CHƯA ĐO
    "processed_per_cam_day": 14,   # kịch bản A: ảnh tốt nhất mỗi giờ
    "gpu_s_per_image": 30,         # trần KPI Datagent; chưa đo chuỗi model thật trên L4
    "cold_start_min": 10,          # thời gian tính tiền mỗi lần endpoint bật từ 0 máy — CHƯA ĐO
    "starts_per_day_A": 1,         # kịch bản A: một đợt mỗi đêm
    "raw_buffer_days": 7,          # ảnh không được chọn giữ 7 ngày rồi xoá
    "kept_retention_months": 3,    # ảnh đã xử lý giữ để đối soát (CV Output!F8) — chờ Datagent
    "skus_per_image": 30,          # số dòng CV Output mỗi ảnh
    "row_kb": 0.5,
    "train_gpu_hours": 20,         # 2 lần train lại / tháng × 10 giờ
    "cvat_hours": 176,             # m7i.xlarge chạy giờ hành chính (8 h × 22 ngày)
    "web_users": 30,
    "web_requests": 200_000,
}
A = ASSUMPTIONS

SCALES = {  # tên: (số tiệm, camera mỗi tiệm)
    "30 tiệm × 1 camera": (30, 1),
    "30 tiệm × 2 camera": (30, 2),   # Store List!E12: vài tiệm có thể cần 2 vị trí
}
SCENARIOS = {
    "A · cập nhật mỗi đêm":   "A",
    "B · cập nhật trong ngày": "B",
}


def per_camera():
    """Khối lượng một camera sinh ra trong một tháng."""
    shots = A["open_hours_per_day"] * 60 / A["capture_every_min"] * D
    uploaded = shots * (1 - A["people_drop"])
    return dict(shots=shots, uploaded=uploaded, uploaded_gb=uploaded * A["still_mb"] / 1000)


def estimate(scale, scenario):
    shops, cams = SCALES[scale]
    n = shops * cams
    v = per_camera()
    L = {}

    def add(group, item, usd):
        L.setdefault(group, {})[item] = L.get(group, {}).get(item, 0) + usd

    processed = n * (A["processed_per_cam_day"] * D if scenario == "A" else v["uploaded"])
    work_h = processed * A["gpu_s_per_image"] / 3600
    if scenario == "A":
        gpu_h = work_h + A["starts_per_day_A"] * D * A["cold_start_min"] / 60
    else:  # giữ một máy bật suốt giờ mở cửa; thêm máy khi việc vượt quá
        gpu_h = max(work_h, A["open_hours_per_day"] * D)

    # 1 · thu nhận
    add("1 Thu nhận", "S3 PUT ảnh", n * v["uploaded"] * P["s3_put"])
    add("1 Thu nhận", "IoT Core (heartbeat mỗi phút)", n * D * 1440 * (P["iot_conn_min"] + P["iot_msg"]))
    add("1 Thu nhận", "SQS + Lambda ghi nhận ảnh", n * v["uploaded"] * (3 * P["sqs_req"] + P["lambda_req"] + 0.2 * P["lambda_gbs"]))
    # 2 · xử lý
    add("2 Xử lý", "SageMaker Async ml.g6.xlarge", gpu_h * P["sm_async_g6_h"])
    add("2 Xử lý", "Lambda chọn ảnh + ghi kết quả", processed * 2 * (P["lambda_req"] + 0.5 * P["lambda_gbs"]))
    add("2 Xử lý", "S3 GET ảnh + PUT kết quả", processed * (P["s3_get"] + P["s3_put"]))
    # 3 · kết quả
    rows_gb = processed * A["skus_per_image"] * A["row_kb"] / 1e6
    add("3 Kết quả", "Firehose → S3 Tables", rows_gb * P["firehose_iceberg_gb"])
    add("3 Kết quả", "DynamoDB", processed * A["skus_per_image"] * (P["ddb_wru"] + 3 * P["ddb_rru"])
        + n * v["uploaded"] * P["ddb_wru"])
    # 4 · lưu trữ (Tokyo)
    kept_gb = processed * A["still_mb"] / 1000
    buffer_gb = n * v["uploaded_gb"] * A["raw_buffer_days"] / D
    add("4 Lưu trữ", f"S3 ảnh đã xử lý ({A['kept_retention_months']} tháng)", kept_gb * A["kept_retention_months"] * P["s3_gbmo"])
    add("4 Lưu trữ", f"S3 ảnh đệm ({A['raw_buffer_days']} ngày)", buffer_gb * P["s3_gbmo"])
    add("4 Lưu trữ", "S3 Tables", rows_gb * A["kept_retention_months"] * P["s3tables_gbmo"])
    add("4 Lưu trữ", "Athena (0,05 TB quét)", 0.05 * P["athena_tb"])
    add("4 Lưu trữ", "ECR + S3 models", 30 * P["ecr_gbmo"] + 30 * P["s3_gbmo"])
    # 5 · sao lưu Osaka
    add("5 Sao lưu Osaka", "Chép ảnh đã xử lý Tokyo → Osaka", kept_gb * (P["xregion_gb"] + 0) + processed * P["s3_put"])
    add("5 Sao lưu Osaka", "S3 Osaka lưu bản sao", kept_gb * A["kept_retention_months"] * P["s3_gbmo"])
    add("5 Sao lưu Osaka", "S3 Tables replication", 3000 * P["s3tables_repl_upd"] + rows_gb * A["kept_retention_months"] * P["s3tables_gbmo"])
    # 6 · train
    add("6 Train", f"SageMaker ml.g6.xlarge {A['train_gpu_hours']} h", A["train_gpu_hours"] * P["sm_train_g6_h"])
    add("6 Train", f"CVAT trên EC2 m7i.xlarge {A['cvat_hours']} h", A["cvat_hours"] * P["m7i.xlarge_h"])
    # 7 · website
    add("7 Website", "Amplify + API Gateway", A["web_requests"] * (P["amplify_req"] + 0.5 * P["amplify_gbs"] + P["apigw_http_req"]))
    add("7 Website", "WAF (1 ACL, 5 rule)", P["waf_acl_mo"] + 5 * P["waf_rule_mo"] + A["web_requests"] * P["waf_req"])
    add("7 Website", "Cognito", A["web_users"] * P["cognito_mau"])
    add("7 Website", "Dữ liệu ra internet (50 GB)", 50 * P["dt_out_gb"])
    # 8 · bảo mật + giám sát
    add("8 Bảo mật", "GuardDuty (log)", 1e6 * P["gd_ct_event"] + 5 * P["gd_flow_gb"])
    add("8 Bảo mật", "Security Hub (5 tài khoản)", 5 * 3000 * P["sechub_check"])
    add("8 Bảo mật", "Config", 5000 * P["config_ci"] + 20000 * P["config_eval"])
    add("8 Bảo mật", "KMS (6 khoá + 6 bản sao Osaka) + Secrets", 12 * P["kms_key_mo"] + 1e6 * P["kms_req"] + 3 * P["secret_mo"])
    add("8 Bảo mật", "CloudWatch (20 GB log, 100 metric, 20 alarm)", 20 * P["cw_log_gb"] + 100 * P["cw_metric_mo"] + 20 * P["cw_alarm_mo"])
    return n, processed, gpu_h, L


def total(L):
    return sum(sum(g.values()) for g in L.values())


if __name__ == "__main__":
    v = per_camera()
    print(f"Mỗi camera / tháng: chụp {v['shots']:,.0f} ảnh, gửi lên {v['uploaded']:,.0f} ảnh = {v['uploaded_gb']:,.1f} GB\n")

    print("TỔNG / THÁNG (USD)")
    for s in SCALES:
        for label, sc in SCENARIOS.items():
            n, processed, gpu_h, L = estimate(s, sc)
            print(f"  {s:20} {label:26} {total(L):>9,.0f}   ({processed:>7,.0f} ảnh xử lý · {gpu_h:>6,.0f} giờ GPU)")

    s, sc = "30 tiệm × 1 camera", "A"
    n, processed, gpu_h, L = estimate(s, sc)
    print(f"\nCHI TIẾT {s} · kịch bản {sc} · {n} camera · {processed:,.0f} ảnh · {gpu_h:,.0f} giờ GPU")
    for g, items in L.items():
        print(f"  {g:16} {sum(items.values()):>10,.2f}")
        for k, usd in items.items():
            print(f"      {k:50} {usd:>10,.2f}")
    print(f"  {'TỔNG':16} {total(L):>10,.2f}")
