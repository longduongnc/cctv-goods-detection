// milk-camera — Tầng bảo mật (bản demo, chưa duyệt).
// Dựng theo khuôn examples/aws/build_landingzone.mjs của drawio-ai-kit:
// Organization → tài khoản Management → các OU → tài khoản; trong Prod chia lớp danh tính · mạng · dữ liệu.
// Chạy: node build_milk_security.mjs bake
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, frame, grid, icon, box, phantom, stage, ossBox, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-security.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";
const d = new Diagram("hierarchy", { contract: CONTRACT });

// lớp bảo vệ trong tài khoản Prod: khung trắng, viền trung tính, icon xếp một hàng
const layer = (id, label, items) =>
  frame(id, label, { dir: "row", gap: 30, fill: THEME.base, stroke: THEME.bandStroke }, items);

// ---- bên ngoài AWS ----
const outside = frame("outside", "Bên ngoài AWS", { dir: "col", gap: 250, fill: THEME.onprem, stroke: THEME.onpremStroke }, [
  icon("team", "user", "Team dự án<br>6 người"),
  icon("cam", "camera", "Camera OAK tại tiệm<br>chứng chỉ X.509 riêng"),
  icon("dg", "users", "Datagent<br>xem báo cáo"),
]);

// ---- Management account ----
const mgmt = group("mgmt", "group_account", "Tài khoản Management · gốc Organization", { dir: "row", gap: 40 }, [
  icon("sso", "single_sign_on", "Identity Center<br>MFA · permission set"),
  icon("org", "organizations", "AWS Organizations"),
  icon("ct", "control_tower", "Control Tower<br>Region deny: Tokyo (+ Osaka)"),
  icon("scp", "policy", "SCP<br>cấm tắt log · cấm dùng root"),
]);

// ---- Workloads OU ----
const prod = group("a_prod", "group_account", "Tài khoản Prod · Tokyo", { dir: "col", gap: 24 }, [
  layer("l_id", "Danh tính máy: camera · pod", [
    icon("iot", "iot_core", "IoT Core<br>mTLS bằng X.509"),
    icon("credp", "policy", "IoT credential provider<br>khoá theo ThingName"),
    icon("ddef", "iot_device_defender", "Device Defender<br>audit chứng chỉ camera"),
    icon("podid", "identity_and_access_management", "Pod Identity<br>mỗi pod một role"),
  ]),
  layer("l_net", "Mạng", [
    icon("vpc", "vpc", "VPC chỉ private subnet<br>không NAT · SG chặt"),
    icon("vpce", "vpc_privatelink", "VPC endpoints<br>+ endpoint policy"),
    icon("waf", "waf", "WAF<br>trước API · website"),
    icon("shield", "shield", "Shield Standard<br>có sẵn"),
  ]),
  layer("l_data", "Dữ liệu", [
    icon("kms", "key_management_service", "KMS CMK<br>video · bảng · log"),
    icon("s3pol", "s3", "S3 chặn public<br>chỉ TLS · chỉ qua VPCE"),
    icon("lf", "lake_formation", "Lake Formation<br>Datagent: bảng tổng hợp"),
    icon("sm", "secrets_manager", "Secrets Manager<br>mật khẩu DB"),
  ]),
  layer("l_web", "Người dùng web", [
    icon("cognito", "cognito", "Cognito<br>MFA · nhóm quyền"),
  ]),
]);
const dev = group("a_dev", "group_account", "Tài khoản Dev", { dir: "row", gap: 20 }, [
  ossBox("devnote", "Cùng guardrail như Prod<br>dữ liệu giả hoặc đã làm mờ mặt", { w: 230, h: 56 }),
]);
const ouWl = stage("ou_wl", 1, "Workloads OU", [prod, dev], { gap: 24 });

// ---- Security OU ----
const logArch = grid("a_log", "group_account", "Tài khoản Log Archive", { cols: 2, gap: 30 }, [
  icon("s3log", "s3", "S3 log<br>Object Lock"),
  icon("trail", "cloudtrail", "CloudTrail<br>trail toàn org"),
  icon("cfg", "config", "Config<br>lịch sử cấu hình"),
  icon("flow", "flow_logs", "VPC Flow Logs"),
]);
const audit = grid("a_audit", "group_account", "Tài khoản Audit · công cụ bảo mật", { cols: 3, gap: 30 }, [
  icon("gd", "guardduty", "GuardDuty<br>EKS runtime · S3 · Lambda"),
  icon("insp", "inspector", "Inspector<br>quét image ECR · Lambda"),
  icon("aa", "access_analyzer", "IAM Access Analyzer<br>quyền mở ra ngoài"),
  icon("sh", "security_hub", "Security Hub<br>gom findings"),
  icon("eb", "eventbridge", "EventBridge<br>lọc mức nghiêm trọng"),
  icon("sns", "sns", "SNS<br>cảnh báo team"),
]);
const ouSec = stage("ou_sec", 0, "Security OU", [logArch, audit], { gap: 24 });

const orgFrame = group("aws", "group_aws_cloud_alt", "AWS Cloud · Organization milk-camera", { dir: "col", gap: 60, align: "center" }, [
  mgmt,
  phantom("ous", "", { dir: "row", gap: 50, align: "top", header: 0 }, [ouWl, ouSec]),
]);

const note = box("note",
  "<b>Chưa chốt / còn thiếu</b><br>" +
  "• Làm mờ mặt trước khi người gán nhãn<br>hoặc Datagent xem: chưa có trong thiết kế<br>" +
  "• Hồ sơ chuyển dữ liệu ra nước ngoài<br>(Luật 91/2025): chưa đọc văn bản gốc<br>" +
  "• Giữ video thô bao lâu: chờ Datagent<br>" +
  "• Ai sở hữu tài khoản AWS: chờ Datagent<br>" +
  "• Osaka trong Region deny chỉ khi chọn sao lưu",
  { w: 290, h: 190, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

const tree = phantom("root", "", { dir: "row", gap: 90, align: "top", header: 0, pad: 10 }, [
  outside,
  orgFrame,
  phantom("notecol", "", { dir: "col", header: 0, pad: 0 }, [note]),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Tầng bảo mật (bản demo 23/09, chưa duyệt)");

// guardrail từ Management xuống các OU
d.link("mgmt", "ou_wl", "SCP · guardrail", { dir: "TB", role: "tree" });
d.link("mgmt", "ou_sec", "", { dir: "TB", role: "tree" });
// ba cửa vào từ bên ngoài
d.link("team", "sso", "SSO + MFA", { flow: true });
d.link("cam", "iot", "mTLS · X.509", { flow: true });
d.link("dg", "cognito", "HTTPS + MFA", { flow: true });
// Prod đẩy log và findings sang Security OU
d.link("a_prod", "a_log", "CloudTrail · Flow Logs · Config");
d.link("a_prod", "a_audit", "findings");
// đường cảnh báo trong tài khoản Audit
d.link("sh", "eb", "");
d.link("eb", "sns", "");

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("Tầng bảo mật"));
console.log("WROTE", OUT, "contract:", CONTRACT);
