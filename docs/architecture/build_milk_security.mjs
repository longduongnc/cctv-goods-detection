// milk-camera — bảo mật giai đoạn đầu (HOANG-P07, 07/11/2026): một tài khoản AWS, chưa có Organizations.
// Bản cũ nhiều tài khoản cho kiến trúc video (HOANG-P02) ở commit 82760d2; phần "thêm khi mở rộng" giữ lại từ bản đó.
// Chạy: node build_milk_security.mjs bake
//       DRAWIO_CLI=".../draw.io.exe" drawio-ai render milk-aws-security.drawio -o milk-aws-security.png --scale 1.5
import { writeFileSync } from "node:fs";
import { Diagram } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/builder.mjs";
import {
  group, frame, icon, box, phantom, renderTree,
} from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/layout-engine.mjs";
import { THEME } from "file:///C:/Users/huyho/AppData/Roaming/npm/node_modules/drawio-ai-kit/src/theme.mjs";

const OUT = "C:/Users/huyho/OneDrive/Desktop/milk-camera/cctv-goods-detection/docs/architecture/milk-aws-security.drawio";
const CONTRACT = process.argv[2] ?? "scaffold";
const d = new Diagram("hierarchy", { contract: CONTRACT });

const layer = (id, label, items) =>
  frame(id, label, { dir: "row", gap: 44, fill: THEME.base, stroke: THEME.bandStroke }, items);

// ---- bên ngoài AWS ----
const outside = frame("outside", "Bên ngoài AWS", { dir: "col", gap: 110, fill: THEME.onprem, stroke: THEME.onpremStroke }, [
  icon("team", "user", "Team vận hành"),
  icon("dg", "users", "Datagent · đội đếm<br>chỉ dùng website"),
  icon("boxpc", "iot_thing_industrial_pc", "Hộp lọc tại tiệm<br>mỗi hộp một chứng chỉ X.509<br>ảnh đã làm mờ mặt"),
]);

// ---- tài khoản Prod ----
const account = group("acct", "group_account", "Một tài khoản AWS · chỉ cho dùng Tokyo và Osaka bằng IAM", { dir: "col", gap: 26 }, [
  layer("l_people", "Team", [
    icon("sso", "single_sign_on", "Identity Center<br>MFA · permission set"),
    icon("iam", "identity_and_access_management", "IAM<br>cấm dùng root"),
  ]),
  layer("l_web", "Người dùng website", [
    icon("cognito", "cognito", "Cognito<br>MFA · nhóm quyền"),
    icon("waf", "waf", "WAF<br>trước website"),
  ]),
  layer("l_device", "Hộp tại tiệm", [
    icon("iot", "iot_core", "IoT Core<br>mTLS bằng X.509"),
    icon("credp", "policy", "IoT credential provider<br>khoá tạm, ghi đúng thư mục của hộp"),
  ]),
  layer("l_net", "Mạng và máy", [
    icon("vpc", "vpc", "VPC chỉ private subnet<br>không NAT"),
    icon("vpce", "endpoints", "S3 gateway endpoint"),
    icon("iso", "sagemaker", "SageMaker<br>network isolation"),
    icon("role", "role", "Execution role<br>mỗi job một quyền"),
  ]),
  layer("l_data", "Dữ liệu", [
    icon("kms", "key_management_service", "KMS<br>3 khoá + 3 bản sao Osaka"),
    icon("s3pol", "s3", "S3 chặn public · chỉ TLS<br>versioning · Object Lock"),
    icon("sec", "secrets_manager", "Secrets Manager"),
  ]),
  layer("l_watch", "Theo dõi và tiền", [
    icon("trail", "cloudtrail", "CloudTrail"),
    icon("cw", "cloudwatch_2", "CloudWatch<br>không có ảnh mới · đợt đêm lỗi"),
    icon("budget", "budgets_2", "AWS Budgets<br>50 · 80 · 100% credit"),
    icon("sns", "sns", "SNS<br>cảnh báo team"),
  ]),
]);

const cloud = group("aws", "group_aws_cloud_alt", "AWS Cloud", { dir: "col", gap: 20 }, [account]);

const later = box("later",
  "<b>Thêm khi mở rộng quá đợt đầu</b><br>" +
  "• Organizations + Control Tower:<br>Management, Log Archive, Audit, Prod, Dev<br>" +
  "• SCP cấm tắt log, Region deny<br>" +
  "• GuardDuty · Security Hub · Config<br>" +
  "• Inspector · IAM Access Analyzer",
  { w: 320, h: 150, fill: THEME.base, stroke: THEME.bandStroke, fs: 11 });

const note = box("note",
  "<b>Chưa chốt / còn thiếu</b><br>" +
  "• Chuyển ảnh sang Nhật: hồ sơ đánh giá gửi trong 60 ngày<br>từ lần chuyển đầu (Luật 91/2025, Điều 20)<br>" +
  "• Ai xin đồng ý của chủ tiệm khi Datagent tự lắp<br>" +
  "• Team là bên kiểm soát hay bên xử lý dữ liệu<br>" +
  "• Không có hộp thì che mặt ngay khi ảnh tới cloud,<br>và phải báo Datagent là mặt người đã rời tiệm<br>" +
  "• Ai giữ tài khoản AWS, credit cấp dưới dạng nào",
  { w: 320, h: 180, fill: THEME.note, stroke: THEME.noteStroke, fs: 11 });

const tree = phantom("root", "", { dir: "row", gap: 90, align: "top", header: 0, pad: 10 }, [
  outside,
  cloud,
  phantom("notecol", "", { dir: "col", gap: 30, header: 0, pad: 0 }, [note, later]),
]);

renderTree(d, tree, [40, 80]);
d.title("milk-camera — Bảo mật giai đoạn đầu (HOANG-P07, 07/11/2026)");

d.link("team", "sso", "SSO + MFA", { flow: true });
d.link("boxpc", "iot", "mTLS · X.509", { flow: true });
d.link("dg", "cognito", "HTTPS + MFA", { flow: true });
d.link("iot", "credp", "");
d.link("trail", "cw", "");
d.link("cw", "sns", "", { route: { es: "T", en: "T" } });
d.link("budget", "sns", "");

const res = d.validate();
console.log("VALIDATE:", JSON.stringify({ ok: res.ok, errors: res.errors, warnings: res.warnings, advice: res.audit.advice }, null, 1));
writeFileSync(OUT, d.mxfile("Bảo mật giai đoạn đầu"));
console.log("WROTE", OUT, "contract:", CONTRACT);
