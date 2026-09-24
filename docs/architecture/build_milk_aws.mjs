// milk-camera — kiến trúc AWS tổng quan cho hệ thống đếm tồn kho (HOANG-P03, 24/09).
// Bản cho kiến trúc cũ (video + bắt lần mua, HOANG-P02) ở commit 518eeae.
// Dựng bằng layout engine của drawio-ai-kit. Nhãn nhiều dòng dùng <br> (nhãn draw.io là HTML).
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, icon, box, phantom, stage, band, endpoint, ossBox, onpremFrame, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-architecture-demo.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";

const d = new Diagram("pipeline", { contract: CONTRACT });

// ---- Tầng 0: tiệm ----
const store = onpremFrame("store", "Tiệm tạp hoá (×30, TP.HCM)", [
  icon("oak4", "camera", "OAK 4 S · 48 MP<br>camera chính"),
  ossBox("edgeapp", "<b>Phần mềm trên camera</b><br>chụp mỗi 15 phút<br>bỏ ảnh có người che kệ<br>làm mờ mặt trước khi gửi<br>đệm 128 GB · xoá khi S3 đã nhận", { w: 230, h: 104 }),
  icon("router", "router", "WiFi tiệm hoặc<br>router 4G"),
  ossBox("altcam", "Thay thế: OAK-D CM4 PoE,<br>camera 2 MP có sẵn ở tiệm", { w: 230, h: 48 }),
], { dir: "col", gap: 22 });

const field = endpoint("field", "<b>ĐỘI THỰC ĐỊA DATAGENT</b><br>thẻ SD · kính Meta · điện thoại<br>bấm \"chụp ngay\" khi đếm tay", { w: 230, h: 80 });

const G = { gap: 34 };

// ---- 1 · Thu nhận ----
const st1 = stage("st1", 0, "1 · Thu nhận", [
  icon("iot", "iot_core", "IoT Core<br>heartbeat · \"chụp ngay\""),
  icon("s3raw", "s3", "S3 ảnh thô"),
  phantom("ingestrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("upload", "api_gateway", "API tải lên<br>presigned URL"),
    icon("sqs", "sqs", "SQS<br>S3 Event"),
    icon("lingest", "lambda", "Lambda ghi nhận ảnh<br>→ DynamoDB"),
  ]),
], { gap: 34, align: "left" });

// ---- 2 · Xử lý mỗi đêm ----
const st2 = stage("st2", 1, "2 · Xử lý mỗi đêm", [
  phantom("nightrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("sched", "eventbridge_scheduler", "EventBridge<br>Scheduler<br>mỗi đêm"),
    icon("lselect", "lambda", "Lambda<br>chọn ảnh<br>mỗi giờ"),
  ]),
  phantom("smrow", "", { dir: "row", gap: 30, header: 0, pad: 0, align: "center" }, [
    group("vpc", "group_vpc", "VPC riêng · chỉ private subnet", { dir: "row", gap: 30, align: "center" }, [
      icon("vpce", "endpoints", "S3 gateway<br>endpoint"),
      icon("sm", "sagemaker", "SageMaker Async<br>ml.g6.xlarge (1× L4)<br>0 → 1 máy · không có mạng"),
    ]),
    icon("sns", "sns", "SNS<br>xong / lỗi"),
    icon("lresult", "lambda", "Lambda<br>ghi kết quả"),
  ]),
], { gap: 34, align: "left" });

// ---- 3 · Kết quả và lưu trữ ----
const st3 = stage("st3", 2, "3 · Kết quả · lưu trữ", [
  phantom("queryrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("glue", "glue_data_catalog", "Glue Catalog<br>+ Lake Formation"),
    icon("athena", "athena", "Athena<br>tính 12 KPI"),
  ]),
  phantom("tablerow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("firehose", "kinesis_data_firehose", "Data Firehose"),
    icon("s3tables", "s3_tables", "S3 Tables<br>cv_output · human_audit<br>sku_master · store_list"),
  ]),
  icon("ddb", "dynamodb", "DynamoDB<br>ảnh mới · tồn kho mới nhất<br>hàng đợi duyệt"),
], G);

// ---- 4 · Website ----
const st4 = stage("st4", 3, "4 · Website", [
  phantom("webrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("apigw", "api_gateway", "API Gateway<br>+ Lambda"),
    icon("amplify", "amplify", "Amplify · Next.js<br>tồn kho · duyệt · 12 KPI<br>tải lên · xuất CV Output"),
  ]),
  phantom("webauth", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("cognito", "cognito", "Cognito + MFA"),
    icon("waf", "waf", "WAF"),
  ]),
], G);

// ---- Train lại mỗi 2 tuần ----
const train = stage("train", 1, "Train lại mỗi 2 tuần", [
  icon("cvat", "ec2", "EC2 · CVAT<br>(Docker Compose)<br>gán nhãn chỗ lệch"),
  phantom("pipecol", "", { dir: "col", gap: 34, header: 0, pad: 0, align: "center" }, [
    icon("sched2", "eventbridge_scheduler", "EventBridge<br>Scheduler<br>2 tuần / lần"),
    icon("pipe", "sagemaker", "SageMaker Pipelines<br>train → chấm tập kiểm định cố định<br>chỉ nhận nếu điểm không giảm"),
  ]),
  icon("smtrain", "sagemaker_train", "Training Jobs<br>ml.g6.xlarge"),
  icon("registry", "sagemaker_model", "Model Registry<br>→ cập nhật endpoint"),
], { dir: "row", gap: 40, align: "bottom" });

const note = box("note",
  "<b>Chưa kiểm chứng / chờ Datagent</b><br>" +
  "• 30 giây/ảnh trên L4: chưa đo<br>" +
  "• Chỉ S3 gateway endpoint đã đủ chưa<br>" +
  "• Tần suất chụp, giờ đóng cửa, giữ ảnh bao lâu<br>" +
  "• Bao nhiêu tiệm không có WiFi<br>" +
  "• Tư vấn pháp lý Luật 91/2025",
  { w: 300, h: 128, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

// ---- dải xuyên suốt ----
const sec = band("sec", "Bảo mật · áp dụng toàn hệ thống", [
  icon("org", "organizations", "Organizations"),
  icon("ct", "control_tower", "Control Tower<br>chỉ Tokyo + Osaka"),
  icon("sso", "single_sign_on", "Identity Center<br>+ MFA"),
  icon("iam", "identity_and_access_management", "IAM"),
  icon("kms", "key_management_service", "KMS<br>multi-Region key"),
  icon("trail", "cloudtrail", "CloudTrail"),
  icon("gd", "guardduty", "GuardDuty"),
  icon("sh", "security_hub", "Security Hub"),
  icon("cfg", "config", "Config"),
]);

const ops = band("ops", "Vận hành · chống mất dữ liệu", [
  icon("cw", "cloudwatch_2", "CloudWatch<br>không có ảnh mới<br>lệch góc · đợt đêm lỗi"),
  icon("snsops", "sns", "SNS<br>cảnh báo"),
  icon("cfn", "cloudformation", "IaC<br>CDK / Terraform"),
  ossBox("dur", "S3 versioning + Object Lock<br>DynamoDB PITR<br>ảnh đã xử lý giữ 3 tháng", { w: 200, h: 64 }),
  icon("bk", "backup", "AWS Backup"),
]);

const tokyo = group("tokyo", "group_region", "Region Tokyo (ap-northeast-1)", { dir: "col", gap: 34 }, [
  phantom("pipeline", "", { dir: "row", gap: 46, align: "top", header: 0 }, [st1, st2, st3, st4]),
  phantom("row2", "", { dir: "row", gap: 46, align: "top", header: 0 }, [train, note]),
  sec,
  ops,
]);

const osaka = group("osaka", "group_region", "Region Osaka (ap-northeast-3) · sao lưu", { dir: "row", gap: 50 }, [
  icon("s3osaka", "s3", "S3 bản sao (S3 Replication)<br>ảnh · dữ liệu train · model"),
  icon("tablesosaka", "s3_tables", "S3 Tables bản sao<br>(S3 Tables replication)"),
  icon("vaultosaka", "backup_vault", "Backup vault<br>bản sao DynamoDB"),
]);

const cloud = group("aws", "group_aws_cloud_alt", "AWS Cloud", { dir: "col", gap: 30 }, [tokyo, osaka]);

const tree = phantom("root", "", { dir: "row", gap: 90, align: "top", header: 0, pad: 10 }, [
  phantom("leftcol", "", { dir: "col", gap: 40, header: 0, pad: 0 }, [store, field]),
  cloud,
  endpoint("users", "<b>NGƯỜI DÙNG</b><br>Datagent · team<br>người duyệt", { w: 170, h: 80 }),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Kiến trúc AWS đếm tồn kho (HOANG-P03, 24/09/2026)");

// tiệm → thu nhận
d.link("edgeapp", "router", "");
d.link("router", "s3raw", "ảnh · TLS", { flow: true });
d.link("router", "iot", "MQTT", { dash: true });
d.link("field", "upload", "tải lên");
d.link("upload", "s3raw", "", { route: { es: "L", en: "L" } });
d.link("s3raw", "sqs", "", { route: { es: "R", en: "T" } });
d.link("sqs", "lingest", "");
// xử lý mỗi đêm
d.link("sched", "lselect", "");
d.link("lselect", "sm", "", { flow: true, route: { es: "R", en: "T" } });
d.link("s3raw", "vpce", "đọc ảnh", { dash: true });
d.link("vpce", "sm", "");
d.link("sm", "sns", "");
d.link("sns", "lresult", "");
// kết quả → lưu trữ → website
d.link("lresult", "firehose", "CV Output", { flow: true });
d.link("lresult", "ddb", "");
d.link("firehose", "s3tables", "", { flow: true });
d.link("s3tables", "athena", "", { route: { es: "R", en: "R" } });
d.link("athena", "apigw", "");
d.link("ddb", "apigw", "");
d.link("apigw", "amplify", "");
d.link("amplify", "users", "HTTPS");
// train lại
d.link("cvat", "pipe", "nhãn");
d.link("sched2", "pipe", "", { route: { es: "L", en: "L" } });
d.link("pipe", "smtrain", "");
d.link("smtrain", "registry", "");
// sao lưu Osaka
d.link("bk", "vaultosaka", "chép chéo region", { dash: true });

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("milk-camera AWS"));
console.log("WROTE", OUT, "contract:", CONTRACT);
