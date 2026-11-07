// milk-camera — kiến trúc AWS tổng quan, giai đoạn đầu (HOANG-P07, 07/11/2026).
// Gốc là bản P03 (commit 82760d2) cộng các chỗ hoang sửa tay trên draw.io ngày 24/10: tên tầng Record/Process/Store,
// dải bảo mật chỉ còn Identity Center, IAM, KMS, CloudTrail, và mũi tên Lambda ghi nhận ảnh → DynamoDB.
// Dựng bằng layout engine của drawio-ai-kit. Nhãn nhiều dòng dùng <br> (nhãn draw.io là HTML).
// Chạy: node build_milk_aws.mjs bake
//       DRAWIO_CLI=".../draw.io.exe" drawio-ai render milk-aws-architecture-demo.drawio -o milk-aws-architecture-demo.png --scale 1.5
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
const store = onpremFrame("store", "Tiệm tạp hoá · đợt đầu 4 tiệm, TP.HCM", [
  phantom("camrow", "", { dir: "row", gap: 96, header: 0, pad: 0, align: "top" }, [
    icon("cam", "camera", "CCTV 4K (8 MP)<br>Datagent mua, lắp<br>chưa biết model"),
    icon("boxpc", "iot_thing_industrial_pc", "Hộp lọc · mini PC N100<br>đề xuất, chờ<br>Datagent đồng ý"),
    icon("router", "router", "WiFi tiệm hoặc<br>router 4G"),
  ]),
  ossBox("edgeapp", "<b>Phần mềm trên hộp</b><br>đọc RTSP, mỗi mốc 15 phút xét 60 khung<br>bỏ khung có người che kệ · làm mờ mặt · chọn khung nét nhất<br>gửi 1 ảnh mỗi mốc · đệm SSD 256 GB · xoá khi S3 đã nhận", { w: 430, h: 88 }),
], { dir: "col", gap: 34 });

const field = endpoint("field", "<b>ĐỘI THỰC ĐỊA DATAGENT</b><br>thẻ SD · điện thoại<br>bấm \"chụp ngay\" khi đếm tay", { w: 300, h: 80 });

const G = { gap: 34 };

// ---- 1 · Record ----
const st1 = stage("st1", 0, "1 · Record", [
  icon("iot", "iot_core", "IoT Core · MQTT<br>heartbeat · \"chụp ngay\""),
  icon("s3raw", "s3", "S3 ảnh thô"),
  phantom("ingestrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("upload", "api_gateway", "API tải lên<br>presigned URL"),
    icon("sqs", "sqs", "SQS<br>S3 Event"),
    icon("lingest", "lambda", "Lambda ghi nhận ảnh<br>→ DynamoDB"),
  ]),
], { gap: 34, align: "left" });

// ---- 2 · Process ----
const st2 = stage("st2", 1, "2 · Process · mỗi đêm", [
  phantom("nightrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("sched", "eventbridge_scheduler", "EventBridge<br>Scheduler<br>mỗi đêm"),
    icon("lselect", "lambda", "Lambda<br>chọn ảnh<br>mỗi giờ"),
  ]),
  phantom("smrow", "", { dir: "row", gap: 30, header: 0, pad: 0, align: "center" }, [
    group("vpc", "group_vpc", "VPC riêng · chỉ private subnet", { dir: "row", gap: 30, align: "center" }, [
      icon("vpce", "endpoints", "S3 gateway<br>endpoint"),
      icon("sm", "sagemaker", "SageMaker Async<br>ml.c5.xlarge (CPU)<br>0 → 1 máy · không có mạng"),
    ]),
    icon("sns", "sns", "SNS<br>xong / lỗi"),
    icon("lresult", "lambda", "Lambda<br>ghi kết quả"),
  ]),
], { gap: 34, align: "left" });

// ---- 3 · Store ----
const st3 = stage("st3", 2, "3 · Store", [
  phantom("queryrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("glue", "glue_data_catalog", "Glue Catalog<br>+ Lake Formation"),
    icon("athena", "athena", "Athena<br>tính 12 KPI"),
  ]),
  phantom("tablerow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("firehose", "kinesis_data_firehose", "Data Firehose"),
    icon("s3tables", "s3_tables", "S3 Tables<br>cv_output · corrections<br>human_audit · sku_master<br>store_list"),
  ]),
  icon("ddb", "dynamodb", "DynamoDB<br>ảnh mới · tồn kho mới nhất<br>hàng đợi low confidence"),
], G);

// ---- 4 · Website ----
const st4 = stage("st4", 3, "4 · Website · blackbox, team vận hành", [
  phantom("webrow", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("apigw", "api_gateway", "API Gateway<br>+ Lambda"),
    icon("amplify", "amplify", "Amplify · Next.js<br>tồn kho · hàng đợi low confidence<br>12 KPI · tải lên · xuất CV Output"),
  ]),
  phantom("webauth", "", { dir: "row", gap: 30, header: 0, pad: 0 }, [
    icon("cognito", "cognito", "Cognito + MFA"),
    icon("waf", "waf", "WAF"),
  ]),
], G);

// ---- Gán nhãn và train lại ----
const train = stage("train", 1, "Gán nhãn và train lại · bật khi đã có nhãn", [
  icon("cvat", "ec2", "EC2 · CVAT<br>(Docker Compose)<br>chỉ bật khi gán nhãn"),
  phantom("pipecol", "", { dir: "col", gap: 34, header: 0, pad: 0, align: "center" }, [
    icon("sched2", "eventbridge_scheduler", "EventBridge<br>Scheduler<br>2 tuần / lần"),
    icon("pipe", "sagemaker", "SageMaker Pipelines<br>train → chấm tập kiểm định cố định<br>chỉ nhận nếu điểm không giảm"),
  ]),
  icon("smtrain", "sagemaker_train", "Training Jobs<br>ml.g6.xlarge"),
  icon("registry", "sagemaker_model", "Model Registry<br>→ cập nhật endpoint"),
], { dir: "row", gap: 40, align: "bottom" });

const note = box("note",
  "<b>Chưa kiểm chứng / chờ Datagent</b><br>" +
  "• Model camera, có RTSP không<br>" +
  "• Ngày lắp · danh sách 4 tiệm · tiệm nào có WiFi<br>" +
  "• Datagent có đồng ý đặt hộp tại tiệm không<br>" +
  "• Thời gian trên hộp và c5.xlarge: quy đổi, chưa đo<br>" +
  "• Chỉ S3 gateway endpoint đã đủ chưa<br>" +
  "• Luật 91/2025: hồ sơ trong 60 ngày từ lần chuyển đầu",
  { w: 340, h: 148, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

const later = box("later",
  "<b>Thêm khi mở rộng quá đợt đầu</b><br>" +
  "• Organizations + Control Tower, 5 tài khoản<br>" +
  "• GuardDuty · Security Hub · Config<br>" +
  "• CVAT chạy giờ hành chính<br>" +
  "• Mì ăn liền · kính Meta Ray-Ban",
  { w: 300, h: 148, fill: THEME.base, stroke: THEME.bandStroke, fs: 11 });

// ---- dải xuyên suốt ----
const sec = band("sec", "Bảo mật · giai đoạn đầu, một tài khoản AWS", [
  icon("sso", "single_sign_on", "Identity Center<br>+ MFA"),
  icon("iam", "identity_and_access_management", "IAM<br>chỉ cho dùng Tokyo + Osaka"),
  icon("kms", "key_management_service", "KMS<br>multi-Region key"),
  icon("trail", "cloudtrail", "CloudTrail"),
]);

const ops = band("ops", "Vận hành · tiền · chống mất dữ liệu", [
  icon("budget", "budgets_2", "AWS Budgets<br>cảnh báo theo credit"),
  icon("cw", "cloudwatch_2", "CloudWatch<br>không có ảnh mới<br>lệch góc · đợt đêm lỗi"),
  icon("snsops", "sns", "SNS<br>cảnh báo"),
  icon("cfn", "cloudformation", "IaC<br>CDK / Terraform"),
  ossBox("dur", "S3 versioning + Object Lock<br>DynamoDB PITR<br>ảnh đã xử lý giữ 3 tháng", { w: 200, h: 64 }),
  icon("bk", "backup", "AWS Backup"),
]);

const tokyo = group("tokyo", "group_region", "Region Tokyo (ap-northeast-1)", { dir: "col", gap: 34 }, [
  phantom("pipeline", "", { dir: "row", gap: 46, align: "top", header: 0 }, [st1, st2, st3, st4]),
  phantom("row2", "", { dir: "row", gap: 46, align: "top", header: 0 }, [train, note, later]),
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
  endpoint("users", "<b>NGƯỜI DÙNG</b><br>Datagent · đội đếm<br>team vận hành", { w: 170, h: 80 }),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Kiến trúc AWS đếm tồn kho, giai đoạn đầu (HOANG-P07, 07/11/2026)");

// tiệm → thu nhận
d.link("cam", "boxpc", "RTSP");
d.link("boxpc", "router", "ảnh đã lọc");
const storeRight = d.R.store.x + d.R.store.w;
d.link("router", "s3raw", "ảnh · TLS", { flow: true, route: { es: "R", en: "L", kind: "Zx", lane: storeRight + 60 } });
d.link("router", "iot", "", { dash: true, route: { es: "R", en: "L", kind: "Zx", lane: storeRight + 30 } });
d.link("field", "upload", "tải lên");
d.link("upload", "s3raw", "", { route: { es: "L", en: "L" } });
d.link("s3raw", "sqs", "", { route: { es: "R", en: "T" } });
d.link("sqs", "lingest", "");
// hoang vẽ tay mũi tên này ngày 24/10; đi vòng dưới các tầng để khỏi xuyên qua chữ
const [a, b, lane] = [d.R.lingest, d.R.ddb, d.R.st1.y + d.R.st1.h + 18];
d.link("lingest", "ddb", "", { route: { es: "R", en: "L", kind: "poly", pts: [
  { x: a.x + a.w + 50, y: a.y + a.h / 2 }, { x: a.x + a.w + 50, y: lane },
  { x: b.x - 56, y: lane }, { x: b.x - 56, y: b.y + b.h * 0.75 },
] } });
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
// gán nhãn và train lại
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
