// milk-camera — Tầng 2 Xử lý: chi tiết compute (bản demo, chưa duyệt).
// Dựng theo khuôn examples/aws/build_multiaz_template.mjs của drawio-ai-kit:
// Region → VPC → AZ → private subnet → worker node → pod; mỗi ứng dụng một khung nét đứt trải 3 AZ.
// Chạy: node build_milk_compute.mjs bake
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, frame, icon, box, phantom, band, endpoint, ossBox, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-compute-detail.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";
const d = new Diagram("network", { contract: CONTRACT });

const AZS = ["1", "2", "3"];
const POD_GAP = 64;   // chừa chỗ cho nhãn dưới icon + khung nét đứt của từng ứng dụng

// ---- mỗi AZ: một private subnet, trong đó một node GPU và một node CPU ----
const gpuNode = (s) => group(`gpu_${s}`, "group_ec2_instance_contents", "Node GPU · g6.xlarge · 1× L4", { dir: "col", gap: POD_GAP, align: "center", pad: 30 }, [
  icon(`s1_${s}`, "container_1", "pod s1-locate<br>LocateAnything-3B"),
  icon(`s4_${s}`, "vllm", "pod s4-read-label<br>Qwen2.5-VL-7B · vLLM"),
]);
const cpuNode = (s) => group(`cpu_${s}`, "group_ec2_instance_contents", "Node CPU · general-purpose", { dir: "col", gap: POD_GAP, align: "center", pad: 30 }, [
  icon(`orch_${s}`, "container_1", "pod orchestrator<br>S2 bám vết · S3 · S5"),
]);
const azCol = (s) => group(`az_${s}`, "group_availability_zone", `AZ ${s}`, { dir: "col", gap: 14, align: "center" }, [
  group(`prv_${s}`, "group_subnet", "Private subnet · không NAT", { dir: "col", gap: 40, align: "center", pad: 30 }, [gpuNode(s), cpuNode(s)]),
]);

const vpc = group("vpc", "group_vpc", "VPC 10.0.0.0/16 · 3 AZ · chỉ private subnet", { dir: "col", gap: 30, align: "center" }, [
  phantom("azrow", "", { dir: "row", gap: 40, align: "top", header: 0 }, AZS.map(azCol)),
  phantom("vpcsvc", "", { dir: "row", gap: 40, align: "center", header: 0 }, [
    icon("keda", "autoscaling", "KEDA (trong cụm)<br>co giãn pod theo hàng đợi"),
    icon("vpce", "vpc_privatelink", "VPC endpoints"),
    ossBox("vpcelist", "<b>Interface:</b> ecr.api · ecr.dkr · sts · eks · eks-auth<br>ec2 · logs · sqs · kinesis-streams · kms<br><b>Gateway:</b> s3", { w: 290, h: 70 }),
  ]),
]);

// ---- dịch vụ quản lý ngoài VPC ----
const inFrame = frame("in", "Đầu vào · ngoài VPC", { dir: "row", gap: 40, fill: THEME.base, stroke: "#82B366" }, [
  phantom("inA", "", { dir: "col", gap: 60, header: 0, pad: 0 }, [
    icon("sqs1", "sqs", "SQS q-segments<br>+ DLQ"),
    icon("kvs", "kinesis_video_streams", "Kinesis Video Streams"),
  ]),
  icon("lambda", "lambda", "Lambda frame-fetcher<br>ngoài VPC"),
  phantom("inC", "", { dir: "col", gap: 60, header: 0, pad: 0 }, [
    icon("s3frames", "s3", "S3 frames<br>khung JPEG"),
    icon("sqs2", "sqs", "SQS q-infer<br>+ DLQ"),
  ]),
]);

const outFrame = frame("out", "Đầu ra · ngoài VPC", { dir: "col", gap: 40, fill: THEME.base, stroke: "#9673A6" }, [
  icon("kds", "kinesis_data_streams", "Kinesis Data Streams<br>sự kiện lấy sữa"),
  icon("s3derived", "s3", "S3 derived<br>boxes · ảnh cắt"),
  icon("cw", "cloudwatch_2", "CloudWatch<br>log · metric · cảnh báo"),
]);

const shared = band("shared", "Dùng chung · cụm EKS đọc qua VPC endpoint", [
  icon("ecr", "ecr", "ECR<br>image pod"),
  icon("s3models", "s3", "S3 models<br>weights nạp sẵn"),
  icon("kms", "key_management_service", "KMS<br>mã hoá S3 · SQS · log"),
  icon("iam", "identity_and_access_management", "IAM + Pod Identity<br>mỗi pod một quyền"),
]);

const note = box("note",
  "<b>Đề xuất · chưa duyệt</b><br>" +
  "• KVS không có VPC endpoint dùng được (phải xin AWS,<br>tối đa 10 stream) → Lambda ngoài VPC lấy khung,<br>cụm EKS không cần NAT<br>" +
  "• Chỉ xoá message SQS sau khi đã ghi sự kiện;<br>lỗi 3 lần → DLQ<br>" +
  "• Mã sự kiện = camera + thời điểm → chạy lại không trùng<br>" +
  "• g6.xlarge đủ VRAM cho cả hai model: chưa đo tải thật<br>" +
  "• S1 ~42 s/khung vẫn là nút thắt chi phí",
  { w: 330, h: 190, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

const region = group("region", "group_region", "Region Tokyo (ap-northeast-1)", { dir: "col", gap: 30, align: "center" }, [
  phantom("main", "", { dir: "row", gap: 60, align: "center", header: 0 }, [
    phantom("inwrap", "", { dir: "col", header: 0, pad: 0 }, [inFrame]),
    vpc,
    phantom("outwrap", "", { dir: "col", header: 0, pad: 0 }, [outFrame]),
  ]),
  phantom("bottom", "", { dir: "row", gap: 60, align: "top", header: 0 }, [shared, note]),
]);
const cloud = group("aws", "group_aws_cloud_alt", "AWS Cloud", { dir: "col", gap: 14 }, [region]);

const tree = phantom("root", "", { dir: "row", gap: 60, align: "center", header: 0, pad: 10 }, [
  endpoint("src", "<b>TỪ TẦNG 1</b><br>IoT Rule:<br>“có đoạn mới”", { w: 150, h: 80 }),
  cloud,
  endpoint("sink", "<b>SANG TẦNG 3–4</b><br>Firehose · Lambda<br>→ S3 Tables · DynamoDB", { w: 190, h: 80 }),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Tầng 2 Xử lý: chi tiết compute (bản demo 23/09, chưa duyệt)");

// khung nét đứt: cả cụm EKS, rồi từng ứng dụng trải qua 3 AZ (vẽ TRƯỚC khi nối để làm đích cho mũi tên)
d.clusterBox("eksstack", AZS.flatMap((s) => [`gpu_${s}`, `cpu_${s}`]),
  "Amazon EKS Auto Mode · API endpoint private · Pod Identity", { icon: "eks", stroke: "#ED7100", padTop: 34, pad: 14 });
const app = (id, base, label, stroke) =>
  d.clusterBox(id, AZS.map((s) => `${base}_${s}`), label, { icon: null, stroke, padTop: 24, pad: 40 });
app("comp_s1", "s1", "S1 · Deployment GPU", "#6666FF");
app("comp_s4", "s4", "S4 · Deployment GPU", "#16A34A");
app("comp_orch", "orch", "orchestrator · Deployment CPU", "#C2185B");

// luồng chính
d.link("src", "sqs1", "đoạn mới", { flow: true });
d.link("sqs1", "lambda", "kích hoạt", { flow: true });
d.link("kvs", "lambda", "GetImages");
d.link("lambda", "s3frames", "ghi khung");
d.link("lambda", "sqs2", "việc suy luận", { flow: true });
d.link("sqs2", "orch_1", "nhận việc", { flow: true });
d.link("s3frames", "orch_1", "đọc khung");
d.link("orch_2", "s1_2", "gọi S1");
d.link("orch_2", "s4_2", "gọi S4");
d.link("orch_3", "kds", "sự kiện", { flow: true });
d.link("orch_3", "s3derived", "boxes · ảnh cắt");
d.link("kds", "sink", "");
// phụ trợ (nét đứt)
d.link("keda", "orch_2", "scale", { dash: true });

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("Tầng 2 · compute"));
console.log("WROTE", OUT, "contract:", CONTRACT);
