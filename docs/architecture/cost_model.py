"""Ước tính chi phí AWS hằng tháng cho milk-camera (bản demo, chưa duyệt).

Giá: AWS Price List API, region ap-northeast-1 (Tokyo), On-Demand, USD, chưa thuế.
     Tải ngày 2026-09-23 từ https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<Service>/current/ap-northeast-1/index.json
     Mỗi dòng giá ghi usagetype để tra lại.
Giả định: toàn bộ nằm trong ASSUMPTIONS — đổi ở đó rồi chạy lại.
Chạy: python cost_model.py
"""

H = 730      # giờ / tháng (AWS dùng 730)
D = 30       # ngày / tháng

# ---- GIÁ TOKYO (usagetype · ngày công bố bảng giá) ----
P = {
    # compute
    "g6.xlarge_h":        1.1672,      # APN1-BoxUsage:g6.xlarge (EC2 2026-09-21) · 1× L4 24 GB
    "g6.xlarge_auto_h":   0.09104,     # APN1-EKS-Auto:g6.xlarge-management-hours (EKS 2026-09-18)
    "m7i.large_h":        0.1302,      # APN1-BoxUsage:m7i.large
    "m7i.large_auto_h":   0.01562,     # APN1-EKS-Auto:m7i.large-management-hours
    "m7i.xlarge_h":       0.2604,      # APN1-BoxUsage:m7i.xlarge
    "m7i.xlarge_auto_h":  0.03125,     # APN1-EKS-Auto:m7i.xlarge-management-hours
    "eks_cluster_h":      0.10,        # APN1-AmazonEKS-Hours:perCluster
    "sm_train_g6_h":      1.634,       # APN1-Train:ml.g6.xlarge (SageMaker 2026-09-22)
    "lambda_gbs":         0.0000166667,  # APN1-Lambda-GB-Second tier 1
    "lambda_req":         0.0000002,   # APN1-Request
    # video + hàng đợi + sự kiện
    "kvs_in_gb":          0.010965,    # APN1-BytesIn (KVS 2026-09-11)
    "kvs_store_gbmo":     0.025,       # APN1-BytesHr
    "kvs_getimages_img":  0.00001,     # APN1-LowRes-ImagesCount ($10 / triệu ảnh ≤1080p)
    "kvs_hls_gb":         0.01536,     # APN1-BytesOut (HLS)
    "sqs_req":            0.0000004,   # APN1-Requests-Tier1
    "iot_conn_min":       0.000000096, # APN1-ConnectionMinutes
    "iot_msg":            0.0000012,   # APN1-Messages (1 tỷ đầu)
    "kds_shard_h":        0.0195,      # APN1-Storage-ShardHour (provisioned)
    "kds_put_unit":       0.0000000215,  # APN1-PutRequestPayloadUnits
    "firehose_iceberg_gb": 0.093,      # APN1-IcebergTablesBilledBytes tier 1 (lấy mức cao hơn trong hai dòng)
    # lưu trữ
    "s3_gbmo":            0.025,       # APN1-TimedStorage-ByteHrs (50 TB đầu)
    "s3_put":             0.0000047,   # APN1-Requests-Tier1
    "s3_get":             0.00000037,  # APN1-Requests-Tier2
    "ddb_wru":            0.000000715, # APN1-WriteRequestUnits
    "ddb_rru":            0.0000001425,  # APN1-ReadRequestUnits
    "athena_tb":          5.0,         # APN1-DataScannedInTB
    "ecr_gbmo":           0.10,        # APN1-TimedStorage-ByteHrs (ECR)
    # mạng
    "vpce_h":             0.014,       # APN1-VpcEndpoint-Hours (mỗi endpoint mỗi AZ)
    "vpce_gb":            0.01,        # APN1-VpcEndpoint-Bytes
    "nat_h":              0.062,       # APN1-NatGateway-Hours (EC2 price list)
    "nat_gb":             0.062,       # APN1-NatGateway-Bytes
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
    "gd_eks_vcpu_mo":     2.0,         # APN1-PaidEKSvCPUMonitored (500 vCPU đầu)
    "gd_ct_event":        0.00000472,  # APN1-PaidEventsAnalyzed
    "gd_flow_gb":         1.18,        # APN1-PaidEventsAnalyzed-Bytes (500 GB đầu)
    "sechub_check":       0.001,       # APN1-PaidComplianceCheck (100k đầu)
    "config_ci":          0.003,       # APN1-ConfigurationItemRecorded
    "config_eval":        0.001,       # APN1-ConfigRuleEvaluations (100k đầu)
    "kms_key_mo":         1.0,         # ap-northeast-1-KMS-Keys
    "kms_req":            0.000003,    # ap-northeast-1-KMS-Requests
    "secret_mo":          0.40,        # APN1-AWSSecretsManager-Secrets
    "cw_log_gb":          0.76,        # APN1-DataProcessing-Bytes (CloudWatch Logs)
    "cw_metric_mo":       0.30,        # APN1-CW:MetricMonitorUsage (10k đầu)
    "cw_alarm_mo":        0.10,        # APN1-CW:AlarmMonitorUsage
}

# ---- GIẢ ĐỊNH (chưa kiểm chứng — đổi ở đây) ----
ASSUMPTIONS = {
    "open_hours_per_day": 16,      # giờ tiệm mở cửa
    "bitrate_mbps": 2.0,           # mỗi camera
    "send_fraction": 0.40,         # phần giờ mở cửa camera gửi lên (lọc người, cho phép gửi thừa)
    "kvs_retention_days": 7,
    "events_per_cam_day": 100,     # số lần có người lấy/chạm kệ mỗi camera mỗi ngày
    "sample_fps": 1.0,             # khung/giây lấy ra để xử lý
    "frame_kb": 200,               # JPEG 1080p
    "frames_per_s3_object": 25,    # gộp khung theo lô để giảm phí PUT
    "frames_retention_days": 7,
    "stills_per_event": 2,
    "still_mb": 5,                 # trung bình giữa ảnh 48 MP (OAK 4) và 12 MP (CM4)
    "clip_seconds_per_event": 10,
    "long_retention_months": 3,    # giữ ảnh chụp + clip sự kiện trên S3 Standard
    "s1_s_per_frame": 42.0,        # đo trên máy GPU của team (HOANG-P01), chưa đo trên L4
    "s4_s_per_crop": 3.2,          # đo trên máy GPU của team (HOANG-P01)
    "crops_per_event": 2,
    "s1_keyframes_per_event": 5,   # kịch bản P2
    "fast_detector_s_per_frame": 0.05,  # kịch bản P3 — detector tự train, CHƯA ĐO
    "gpu_utilization": 0.70,       # tỉ lệ thời gian máy GPU thật sự bận
    "vpc_endpoints": 10,           # interface endpoint trong bản vẽ compute
    "azs": 3,
    "train_gpu_hours": 100,        # SageMaker ml.g6.xlarge / tháng
    "cvat_hours": 176,             # m7i.xlarge chạy giờ hành chính (8 h × 22 ngày)
    "web_users": 30,
    "web_requests": 200_000,
}
A = ASSUMPTIONS

SCALES = {  # tên: (số tiệm, camera mỗi tiệm, số máy CPU cho orchestrator)
    "S · 5 tiệm × 2 cam":  (5, 2, 2),
    "M · 10 tiệm × 2 cam": (10, 2, 2),
    "L · 20 tiệm × 4 cam": (20, 4, 4),
}
PROCESSING = {
    "P1 · S1 mọi khung (như hiện nay)": "p1",
    "P2 · S1 chỉ khung then chốt":      "p2",
    "P3 · detector nhanh thay S1":      "p3",
}


def per_camera():
    """Khối lượng sinh ra bởi một camera trong một tháng."""
    sent_s = 3600 * A["open_hours_per_day"] * D * A["send_fraction"]
    video_gb = A["bitrate_mbps"] * 1e6 / 8 * sent_s / 1e9
    frames = sent_s * A["sample_fps"]
    events = A["events_per_cam_day"] * D
    return dict(sent_s=sent_s, video_gb=video_gb, frames=frames, events=events)


def gpu_seconds(mode, v):
    s4 = v["events"] * A["crops_per_event"] * A["s4_s_per_crop"]
    if mode == "p1":
        return v["frames"] * A["s1_s_per_frame"] + s4
    if mode == "p2":
        return v["events"] * A["s1_keyframes_per_event"] * A["s1_s_per_frame"] + s4
    return v["frames"] * A["fast_detector_s_per_frame"] + s4


def estimate(scale, mode, network="A"):
    shops, cams_per_shop, cpu_nodes = SCALES[scale]
    n = shops * cams_per_shop
    v = per_camera()
    L = {}  # nhóm -> {dòng: USD}

    def add(group, item, usd):
        L.setdefault(group, {})[item] = L.get(group, {}).get(item, 0) + usd

    # 1 · thu nhận
    add("1 Thu nhận", "KVS ghi video", n * v["video_gb"] * P["kvs_in_gb"])
    add("1 Thu nhận", f"KVS lưu {A['kvs_retention_days']} ngày", n * v["video_gb"] * A["kvs_retention_days"] / D * P["kvs_store_gbmo"])
    add("1 Thu nhận", "IoT Core", n * (D * 1440 * P["iot_conn_min"] + (D * 1440 + v["events"]) * P["iot_msg"]))
    # 2 · xử lý
    add("2 Xử lý", "KVS GetImages", n * v["frames"] * P["kvs_getimages_img"])
    add("2 Xử lý", "Lambda frame-fetcher", n * (v["frames"] * 0.04 * P["lambda_gbs"] + v["events"] * P["lambda_req"]))
    batches = v["frames"] / A["frames_per_s3_object"]
    add("2 Xử lý", "S3 frames (PUT + lưu 7 ngày)", n * (batches * (P["s3_put"] + P["s3_get"])
        + v["frames"] * A["frame_kb"] / 1e6 * A["frames_retention_days"] / D * P["s3_gbmo"]))
    add("2 Xử lý", "SQS", n * (v["events"] + batches) * 3 * P["sqs_req"])
    gpu_h = n * gpu_seconds(mode, v) / 3600 / A["gpu_utilization"]
    add("2 Xử lý", "Máy GPU g6.xlarge + phí Auto Mode", gpu_h * (P["g6.xlarge_h"] + P["g6.xlarge_auto_h"]))
    add("2 Xử lý", f"Máy CPU m7i.large ×{cpu_nodes} (24/7)", cpu_nodes * H * (P["m7i.large_h"] + P["m7i.large_auto_h"]))
    add("2 Xử lý", "Cụm EKS", H * P["eks_cluster_h"])
    if network == "A":
        add("2 Xử lý", f"VPC endpoints ×{A['vpc_endpoints']} × {A['azs']} AZ", A["vpc_endpoints"] * A["azs"] * H * P["vpce_h"] + 50 * P["vpce_gb"])
    else:
        image_pull_gb = 500
        add("2 Xử lý", f"NAT Gateway ×{A['azs']}", A["azs"] * H * P["nat_h"] + image_pull_gb * P["nat_gb"])
    # 3 · sự kiện
    ev_kb = 1.0
    add("3 Sự kiện", "Kinesis Data Streams (1 shard)", H * P["kds_shard_h"] + n * v["events"] * P["kds_put_unit"])
    add("3 Sự kiện", "Firehose → Iceberg", n * v["events"] * ev_kb / 1e6 * P["firehose_iceberg_gb"])
    add("3 Sự kiện", "Lambda ghi DynamoDB", n * v["events"] * (P["lambda_req"] + 0.1 * P["lambda_gbs"]))
    # 4 · lưu trữ
    stills_gb = v["events"] * A["stills_per_event"] * A["still_mb"] / 1000
    clips_gb = v["events"] * A["clip_seconds_per_event"] * A["bitrate_mbps"] / 8 / 1000
    add("4 Lưu trữ", f"S3 ảnh chụp + clip ({A['long_retention_months']} tháng)",
        n * ((stills_gb + clips_gb) * A["long_retention_months"] * P["s3_gbmo"] + v["events"] * (A["stills_per_event"] + 1) * P["s3_put"]))
    add("4 Lưu trữ", "DynamoDB", n * v["events"] * (P["ddb_wru"] + 5 * P["ddb_rru"]))
    add("4 Lưu trữ", "Athena (0,05 TB quét)", 0.05 * P["athena_tb"])
    add("4 Lưu trữ", "ECR + S3 models", 30 * P["ecr_gbmo"] + 30 * P["s3_gbmo"])
    # 5 · website
    add("5 Website", "Amplify + API Gateway", A["web_requests"] * (P["amplify_req"] + 0.5 * P["amplify_gbs"] + P["apigw_http_req"]))
    add("5 Website", "WAF (1 ACL, 5 rule)", P["waf_acl_mo"] + 5 * P["waf_rule_mo"] + A["web_requests"] * P["waf_req"])
    add("5 Website", "Cognito", A["web_users"] * P["cognito_mau"])
    add("5 Website", "Xem video HLS + dữ liệu ra internet", 20 * P["kvs_hls_gb"] + 50 * P["dt_out_gb"])
    # 6 · train
    add("6 Train", f"SageMaker ml.g6.xlarge {A['train_gpu_hours']} h", A["train_gpu_hours"] * P["sm_train_g6_h"])
    add("6 Train", f"CVAT m7i.xlarge {A['cvat_hours']} h", A["cvat_hours"] * (P["m7i.xlarge_h"] + P["m7i.xlarge_auto_h"]))
    # 7 · bảo mật + giám sát
    vcpu = cpu_nodes * 2 + gpu_h / H * 4
    add("7 Bảo mật", "GuardDuty (EKS runtime + log)", vcpu * P["gd_eks_vcpu_mo"] + 1e6 * P["gd_ct_event"] + 5 * P["gd_flow_gb"])
    add("7 Bảo mật", "Security Hub (5 tài khoản)", 5 * 3000 * P["sechub_check"])
    add("7 Bảo mật", "Config", 5000 * P["config_ci"] + 20000 * P["config_eval"])
    add("7 Bảo mật", "KMS + Secrets Manager", 6 * P["kms_key_mo"] + 1e6 * P["kms_req"] + 3 * P["secret_mo"])
    add("7 Bảo mật", "CloudWatch (20 GB log, 100 metric, 20 alarm)", 20 * P["cw_log_gb"] + 100 * P["cw_metric_mo"] + 20 * P["cw_alarm_mo"])
    return n, gpu_h, L


def total(L):
    return sum(sum(g.values()) for g in L.values())


if __name__ == "__main__":
    v = per_camera()
    print(f"Mỗi camera / tháng: gửi {v['sent_s']/3600:.0f} giờ video = {v['video_gb']:.0f} GB · "
          f"{v['frames']:,.0f} khung · {v['events']:,} sự kiện\n")

    print("TỔNG / THÁNG (USD, phương án mạng A: VPC endpoints)")
    head = f"{'':24}" + "".join(f"{k:>36}" for k in PROCESSING)
    print(head)
    for s in SCALES:
        row = f"{s:24}"
        for label, mode in PROCESSING.items():
            n, gpu_h, L = estimate(s, mode)
            row += f"{total(L):>24,.0f}  ({gpu_h:>7,.0f} GPU-h)"
        print(row)

    for s, mode in [("M · 10 tiệm × 2 cam", "p2"), ("M · 10 tiệm × 2 cam", "p3")]:
        n, gpu_h, L = estimate(s, mode)
        print(f"\nCHI TIẾT {s} · {mode.upper()} · {n} camera · {gpu_h:,.0f} giờ GPU")
        for g, items in L.items():
            print(f"  {g:14} {sum(items.values()):>10,.2f}")
            for k, usd in items.items():
                print(f"      {k:52} {usd:>10,.2f}")
        print(f"  {'TỔNG':14} {total(L):>10,.2f}")

    print("\nMẠNG: A (VPC endpoints, không NAT) so với B (NAT Gateway) — quy mô M, P3")
    for net in ("A", "B"):
        _, _, L = estimate("M · 10 tiệm × 2 cam", "p3", network=net)
        line = [k for k in L["2 Xử lý"] if k.startswith(("VPC", "NAT"))][0]
        print(f"  {net}: {line:34} {L['2 Xử lý'][line]:>8,.2f}   tổng {total(L):>9,.2f}")
