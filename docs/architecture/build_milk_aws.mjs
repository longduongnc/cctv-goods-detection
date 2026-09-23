// milk-camera — kiến trúc AWS, bản demo (chưa duyệt). Dựng bằng layout engine của drawio-ai-kit.
// Nhãn nhiều dòng dùng <br> (thuộc tính XML không giữ ký tự xuống dòng; nhãn draw.io là HTML).
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, icon, box, phantom, stage, band, endpoint, ossBox, onpremFrame, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-architecture-demo.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";

const d = new Diagram("pipeline", { contract: CONTRACT });

// ---- Tầng 0: cửa hàng ----
const store = onpremFrame("store", "Cửa hàng tạp hoá (×5–20 tiệm)", [
  phantom("cams", "", { dir: "row", gap: 24, header: 0, pad: 0 }, [
    icon("oak4", "camera", "OAK 4 S<br>kệ xa · 48 MP"),
    icon("cm4", "camera", "OAK-D CM4 PoE<br>kệ trong ~2,9 m"),
  ]),
  ossBox("edgeapp", "<b>App trên camera</b> (DepthAI v3)<br>model nhỏ lọc đoạn có người<br>đệm đĩa · xoá khi có PERSISTED<br>chứng chỉ X.509 riêng", { w: 230, h: 96 }),
  icon("router", "router", "Switch PoE · Router<br>UPS"),
], { dir: "col", gap: 22 });

// ---- các cột xử lý trong region Tokyo ----
// hàng r0..r4 được xếp để các đường chính chạy thẳng: iot→sqs, lambda→ddb, firehose→s3tables, ddb→apigw
const G = { gap: 34 };
const st1 = stage("st1", 0, "1 · Thu nhận", [
  icon("iot", "iot_core", "IoT Core<br>MQTT · Rule · cấp khoá"),
  icon("kvs", "kinesis_video_streams", "Kinesis Video Streams<br>1 stream / camera"),
  icon("s3stills", "s3", "S3 raw-stills<br>ảnh 48 MP"),
], G);

const st2 = stage("st2", 1, "2 · Xử lý", [
  icon("sqs", "sqs", "SQS + DLQ<br>hàng đợi đoạn mới"),
  group("vpc", "group_vpc", "VPC riêng · private subnet · 3 AZ", { dir: "col", gap: 18 }, [
    icon("eks", "eks", "EKS Auto Mode<br>worker S1 → S5"),
    phantom("nodes", "", { dir: "row", gap: 20, header: 0, pad: 0 }, [
      icon("gpu", "ec2", "Máy GPU G6 / G6e<br>S1 định vị · S4 đọc nhãn"),
      icon("cpu", "ec2", "Máy CPU<br>S2 · S3 · S5"),
    ]),
    icon("vpce", "vpc_privatelink", "VPC endpoints<br>máy GPU không ra internet"),
  ]),
  phantom("st2b", "", { dir: "row", gap: 20, header: 0, pad: 0 }, [
    icon("s3derived", "s3", "S3 derived<br>worker ghi boxes · ảnh cắt"),
    icon("ecr", "ecr", "ECR<br>image worker"),
  ]),
], G);

// SKIP = khoảng cách để hai icon cách nhau đúng hai hàng (icon cao 82 + gap 34 → bước 116)
const SKIP = 2 * (82 + G.gap) - 82;
const st3 = stage("st3", 2, "3 · Đường ống sự kiện", [
  phantom("st3r", "", { dir: "row", gap: 40, header: 0, pad: 0, align: "center" }, [
    icon("kds", "kinesis_data_streams", "Kinesis Data Streams<br>sự kiện lấy sữa"),
    phantom("st3c", "", { dir: "col", gap: SKIP, header: 0, pad: 0 }, [
      icon("lambda", "lambda", "Lambda<br>ghi DB · hàng đợi duyệt"),
      icon("firehose", "kinesis_data_firehose", "Data Firehose<br>ghi vào Iceberg"),
    ]),
  ]),
], G);

const st4 = stage("st4", 3, "4 · Lưu trữ", [
  phantom("st4r", "", { dir: "row", gap: 30, header: 0, pad: 0, align: "center" }, [
    phantom("st4c", "", { dir: "col", gap: SKIP, header: 0, pad: 0 }, [
      icon("ddb", "dynamodb", "DynamoDB<br>vận hành · hàng đợi duyệt"),
      icon("s3tables", "s3_tables", "S3 Tables (Iceberg)<br>bảng sự kiện"),
    ]),
    icon("athena", "athena", "Athena<br>SQL báo cáo"),
  ]),
  phantom("catalog", "", { dir: "row", gap: 20, header: 0, pad: 0 }, [
    icon("glue", "glue_data_catalog", "Glue Catalog"),
    icon("lf", "lake_formation", "Lake Formation<br>quyền tới cột"),
  ]),
  icon("s3lake", "s3", "S3 lưu lâu<br>clips · training · models"),
], G);

const st5 = stage("st5", 4, "5 · Website", [
  phantom("st5r", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("apigw", "api_gateway", "API Gateway<br>+ Lambda"),
    icon("amplify", "amplify", "Amplify · Next.js<br>dashboard · duyệt S6 · HLS"),
  ]),
  icon("cognito", "cognito", "Cognito<br>admin · duyệt · Datagent"),
  icon("waf", "waf", "WAF"),
], G);

// ---- Train ----
const train = stage("train", 1, "Train", [
  ossBox("cvat", "<b>CVAT / Label Studio</b><br>tự host trên EKS · chưa chốt<br>thay Ground Truth (đã đóng)", { w: 220, h: 76 }),
  icon("registry", "sagemaker_model", "Model Registry<br>→ image trong ECR"),
  icon("sm", "sagemaker_train", "SageMaker Training Jobs<br>Spot → HyperPod sau"),
], { dir: "row", gap: 36 });

const note = box("note",
  "<b>Chưa chốt / rủi ro</b><br>" +
  "• Công cụ gán nhãn: CVAT hay Label Studio<br>" +
  "• Sao lưu sang Osaka: có hay không<br>" +
  "• S1 ~42 s/khung: cần detector nhanh,<br>nếu không ~35 GPU cho 20 camera<br>" +
  "• Làm mờ mặt: chờ tư vấn Luật 91/2025",
  { w: 290, h: 128, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

// ---- dải xuyên suốt ----
const sec = band("sec", "Bảo mật · áp dụng toàn hệ thống", [
  icon("org", "organizations", "Organizations"),
  icon("ct", "control_tower", "Control Tower<br>SCP khoá region"),
  icon("sso", "single_sign_on", "Identity Center<br>+ MFA"),
  icon("iam", "identity_and_access_management", "IAM"),
  icon("kms", "key_management_service", "KMS"),
  icon("trail", "cloudtrail", "CloudTrail"),
  icon("gd", "guardduty", "GuardDuty"),
  icon("sh", "security_hub", "Security Hub"),
  icon("cfg", "config", "Config"),
]);

const ops = band("ops", "Bền · vận hành", [
  icon("cw", "cloudwatch_2", "CloudWatch<br>camera ngừng đẩy · DLQ"),
  icon("sns", "sns", "SNS<br>cảnh báo"),
  icon("bk", "backup", "AWS Backup<br>Vault Lock"),
  icon("cfn", "cloudformation", "IaC<br>CDK / Terraform"),
  ossBox("dur", "S3 versioning + Object Lock<br>DynamoDB PITR<br>đệm đĩa + ack PERSISTED", { w: 210, h: 70 }),
]);

const tokyo = group("tokyo", "group_region", "Region Tokyo (ap-northeast-1)", { dir: "col", gap: 34 }, [
  phantom("pipe", "", { dir: "row", gap: 46, align: "top", header: 0 }, [st1, st2, st3, st4, st5]),
  phantom("row2", "", { dir: "row", gap: 46, align: "top", header: 0 }, [note, train]),
  sec,
  ops,
]);

const osaka = group("osaka", "group_region", "Region Osaka (ap-northeast-3) · tuỳ chọn, chỉ sao lưu", { dir: "row", gap: 40 }, [
  icon("bkosaka", "backup", "Backup vault<br>bản sao"),
  icon("s3osaka", "s3", "S3<br>bản sao"),
]);

const cloud = group("aws", "group_aws_cloud_alt", "AWS Cloud", { dir: "col", gap: 30 }, [tokyo, osaka]);

// phantom bọc ngoài để khung cửa hàng giữ chiều cao tự nhiên (không kéo theo AWS Cloud)
const tree = phantom("root", "", { dir: "row", gap: 90, align: "top", header: 0, pad: 10 }, [
  phantom("storecol", "", { dir: "col", header: 0, pad: 0 }, [store]),
  cloud,
  endpoint("users", "<b>NGƯỜI DÙNG</b><br>team · người duyệt<br>Datagent", { w: 170, h: 80 }),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Kiến trúc AWS (bản demo 23/09, chưa duyệt)");

// cửa hàng → thu nhận
d.link("edgeapp", "router", "");
d.link("router", "iot", "MQTT: đoạn mới", { role: "fanout" });
d.link("router", "kvs", "video · TLS", { role: "fanout" });
d.link("router", "s3stills", "ảnh · TLS", { role: "fanout" });
// thu nhận → xử lý
d.link("iot", "sqs", "IoT Rule", { flow: true });
d.link("sqs", "eks", "việc", { flow: true });
d.link("kvs", "eks", "GetImages");
d.link("s3stills", "eks", "");
// xử lý → sự kiện → lưu trữ
d.link("eks", "kds", "sự kiện", { flow: true });
d.link("kds", "lambda", "");
d.link("kds", "firehose", "");
d.link("lambda", "ddb", "", { flow: true });
d.link("firehose", "s3tables", "", { flow: true });
d.link("s3tables", "athena", "");
// lưu trữ → website → người dùng
d.link("ddb", "apigw", "");
d.link("athena", "apigw", "");
d.link("apigw", "amplify", "");
d.link("amplify", "users", "HTTPS");
// train + sao lưu
d.link("s3lake", "sm", "dữ liệu train");
d.link("bk", "osaka", "sao chép chéo region", { dash: true });

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("milk-camera AWS"));
console.log("WROTE", OUT, "contract:", CONTRACT);
