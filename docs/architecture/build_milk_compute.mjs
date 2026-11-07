// milk-camera — chi tiết xử lý, giai đoạn đầu (HOANG-P07, 07/11/2026): hộp tại tiệm, chuỗi model, vòng human audit.
// Bản cũ cho kiến trúc video + EKS (HOANG-P02) ở commit 82760d2.
// Chạy: node build_milk_compute.mjs bake
//       DRAWIO_CLI=".../draw.io.exe" drawio-ai render milk-aws-compute-detail.drawio -o milk-aws-compute-detail.png --scale 1.5
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, frame, icon, box, phantom, stage, endpoint, ossBox, onpremFrame, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-compute-detail.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";
const d = new Diagram("pipeline", { contract: CONTRACT });

const step = (id, text, w = 250, h = 56) => ossBox(id, text, { w, h });

// ---- hộp tại tiệm: khung chữ, nên đường dọc không đè nhãn ----
const shop = onpremFrame("shop", "Hộp lọc tại tiệm · mỗi mốc 15 phút", [
  step("cam", "<b>CCTV 4K (Datagent lắp)</b><br>luồng RTSP, H.265"),
  step("e1", "<b>1 · Lấy khung</b><br>1 khung/giây trong 60 giây quanh mốc"),
  step("e2", "<b>2 · Bỏ khung có người che kệ</b><br>YOLO26s COCO, lớp person"),
  step("e3", "<b>3 · Làm mờ mặt</b><br>YuNet"),
  step("e4", "<b>4 · Chọn khung nét nhất</b><br>phương sai Laplacian"),
  step("e5", "<b>5 · Gửi 1 ảnh, khoảng 1,3 MB</b><br>đệm SSD 256 GB, xoá khi S3 đã nhận"),
], { dir: "col", gap: 26, align: "center" });

// ---- xử lý mỗi đêm ----
const container = frame("container", "Container model · không có mạng", { dir: "row", gap: 34, fill: THEME.base, stroke: THEME.bandStroke, align: "center" }, [
  step("m1", "<b>1 · Tìm hộp</b><br>YOLO26s 1280 px, 12 lớp", 190, 70),
  step("m2", "<b>2 · Tra SKU</b><br>DINOv2-S + LanceDB<br>10 láng giềng", 190, 70),
  step("m3", "<b>3 · Đếm theo SKU</b><br>unit_score =<br>conf YOLO × support", 190, 70),
  step("m4", "<b>4 · Xuất CV Output</b><br>gắn cờ: dưới 0,7 ·<br>sku_id NULL · số lạ", 190, 70),
]);

const night = stage("night", 1, "Mỗi đêm · 14 ảnh/tiệm", [
  phantom("schedrow", "", { dir: "row", gap: 60, header: 0, pad: 0, align: "top" }, [
    icon("sched", "eventbridge_scheduler", "EventBridge<br>Scheduler"),
    icon("lsel", "lambda", "Lambda chọn<br>ảnh tốt nhất mỗi giờ"),
  ]),
  phantom("nightrow", "", { dir: "row", gap: 60, header: 0, pad: 0, align: "center" }, [
    icon("s3in", "s3", "S3 ảnh thô<br>56 ảnh/tiệm/ngày"),
    group("vpc", "group_vpc", "VPC riêng · chỉ private subnet", { dir: "row", gap: 50, align: "center" }, [
      icon("vpce", "endpoints", "S3 gateway<br>endpoint"),
      icon("sm", "sagemaker", "SageMaker Async<br>ml.c5.xlarge (CPU)<br>0 → 1 máy"),
      container,
    ]),
  ]),
], { gap: 34, align: "left" });

// ---- kết quả ----
const results = stage("results", 2, "Kết quả", [
  phantom("resrow", "", { dir: "row", gap: 60, header: 0, pad: 0, align: "top" }, [
    icon("sns", "sns", "SNS<br>xong / lỗi"),
    icon("lres", "lambda", "Lambda ghi kết quả<br>chạy lại không<br>sinh dòng trùng"),
    phantom("sinks", "", { dir: "col", gap: 50, header: 0, pad: 0, align: "center" }, [
      icon("tables", "s3_tables", "S3 Tables<br>cv_output"),
      icon("ddb", "dynamodb", "DynamoDB<br>hàng đợi low confidence"),
    ]),
  ]),
], { gap: 34, align: "center" });

// ---- vòng human audit ----
const layer1 = stage("layer1", 3, "Tầng 1 · gán nhãn: dòng bị gắn cờ của 1 ảnh/tiệm/ngày, khoảng 130–160 dòng mỗi chu kỳ 14 ngày (đề xuất)", [
  icon("web", "amplify", "Website<br>hàng đợi low confidence"),
  endpoint("counters", "<b>ĐỘI ĐẾM DATAGENT</b><br>sửa SKU và số đếm", { w: 170, h: 70 }),
  icon("corr", "s3_tables", "S3 Tables<br>corrections"),
  icon("cvat", "ec2", "EC2 · CVAT<br>vẽ khung, chỉ bật khi cần"),
  icon("train", "sagemaker_train", "SageMaker Training<br>ml.g6.xlarge"),
  icon("gate", "sagemaker", "Chấm tập kiểm định cố định<br>chỉ nhận nếu điểm không giảm"),
  icon("reg", "sagemaker_model", "Model Registry<br>→ cập nhật endpoint"),
], { dir: "row", gap: 70, align: "center" });

const layer2 = stage("layer2", 0, "Tầng 2 · đo KPI: đếm đủ kệ sữa mỗi tiệm, mỗi chu kỳ (đề xuất, chờ Datagent xác nhận)", [
  endpoint("field", "<b>ĐỘI THỰC ĐỊA DATAGENT</b><br>đếm tay, số chuẩn", { w: 190, h: 70 }),
  icon("audit", "s3_tables", "S3 Tables<br>human_audit"),
  icon("athena", "athena", "Athena<br>tính 12 KPI"),
  box("why", "Chỉ xem dòng low confidence thì không đo được KPI:<br>trên ảnh mô phỏng, ngưỡng 0,70 bắt 96% phát hiện sai<br>nhưng chỉ 35% dòng đếm sai; SKU bị bỏ sót không có dòng để gắn cờ", { w: 400, h: 70, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 }),
], { dir: "row", gap: 70, align: "center" });

const region = group("region", "group_region", "Region Tokyo (ap-northeast-1)", { dir: "col", gap: 40, align: "center" }, [
  phantom("mainrow", "", { dir: "row", gap: 60, align: "center", header: 0 }, [night, results]),
  layer1,
  layer2,
]);
const cloud = group("aws", "group_aws_cloud_alt", "AWS Cloud", { dir: "col", gap: 14 }, [region]);

const tree = phantom("root", "", { dir: "row", gap: 70, align: "top", header: 0, pad: 10 }, [shop, cloud]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Chi tiết xử lý: hộp tại tiệm, chuỗi model, vòng human audit (HOANG-P07, 07/11/2026)");

// hộp tại tiệm
d.link("cam", "e1", "");
d.link("e1", "e2", "");
d.link("e2", "e3", "");
d.link("e3", "e4", "");
d.link("e4", "e5", "");
d.link("e5", "s3in", "TLS", { flow: true });
// mỗi đêm
d.link("sched", "lsel", "");
d.link("lsel", "sm", "", { dash: true, route: { es: "R", en: "T", kind: "Lhv" } });
d.link("s3in", "vpce", "đọc ảnh", { dash: true });
d.link("vpce", "sm", "");
d.link("sm", "m1", "");
d.link("m1", "m2", "");
d.link("m2", "m3", "");
d.link("m3", "m4", "");
d.link("m4", "sns", "ghi S3");
d.link("sns", "lres", "");
d.link("lres", "tables", "");
d.link("lres", "ddb", "");
// tầng 1
d.link("web", "counters", "");
d.link("counters", "corr", "bản sửa");
d.link("corr", "cvat", "");
d.link("cvat", "train", "nhãn");
d.link("train", "gate", "");
d.link("gate", "reg", "");
// tầng 2
d.link("field", "audit", "");
d.link("audit", "athena", "");

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("Chi tiết xử lý"));
console.log("WROTE", OUT, "contract:", CONTRACT);
