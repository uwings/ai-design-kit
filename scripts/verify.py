"""ADK 端到端验证 —— 跑全部 8 项检查，打印汇总。

用法: python scripts/verify.py
退出码 0 = 全绿；非 0 = 有失败项。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def cli(*args) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "engine.cli", *args],
                       capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout + p.stderr)


# 1. Schema 自洽
rc, _ = cli("validate-contracts")
check("1. schema: 14 contracts valid", rc == 0)
rc, out = cli("validate-tokens", "--system", "ant-design")
check("1. schema: token graph clean", rc == 0 and "OK" in out)

# 2. 确定性管线
rc, _ = cli("compile-pencil", "fixtures/user-permissions-page/graph.json",
            "-o", "pencil/generated/user-permissions-page.pen")
check("2. pipeline: compile-pencil", rc == 0)
rc, _ = cli("compile-code", "fixtures/user-permissions-page/graph.json",
            "--framework", "react", "-o", "generated-code/user-permissions-page/UserPermissionsPage.tsx")
check("2. pipeline: compile-react", rc == 0)
pen = json.loads((ROOT / "pencil/generated/user-permissions-page.pen").read_text(encoding="utf-8"))

def _has_ref(n):
    if not isinstance(n, dict):
        return False
    if n.get("type") == "ref":
        return True
    for ch in n.get("children", []) or []:
        if _has_ref(ch):
            return True
    for kids in (n.get("slots") or {}).values():
        for k in kids:
            if _has_ref(k):
                return True
    return False

has_ref = any(_has_ref(page) for page in pen.get("children", []))
check("2. pipeline: .pen has refs+variables", has_ref and len(pen.get("variables", {})) > 0)

# 3. Validator 拦截（每个违规文件应 blocking）
viol_dir = ROOT / "fixtures/violations"
blocked_all = True
for vf in sorted(viol_dir.glob("*.json")):
    rc, out = cli("validate-ops", str(vf))
    try:
        d = json.loads(out)
        blocked = d["counts"]["blocking"] > 0
    except Exception:
        blocked = False
    if not blocked:
        blocked_all = False
        check(f"3. validator blocks: {vf.name}", False)
check("3. validator: all violation fixtures blocked", blocked_all,
      f"{len(list(viol_dir.glob('*.json')))} files")

# 合法 fixture 必须通过
rc, out = cli("validate-ops", "fixtures/user-permissions-page/ops.json")
d = json.loads(out)
check("3b. validator: valid fixture passes (no false positive)", d["passed"])

# 4. 意图路由召回
rc, out = cli("retrieve", "--intent", "destructive_confirmation", "--system", "ant-design")
d = json.loads(out)
check("4. retrieval: destructive_confirmation routes to modal+button",
      "antd.modal" in d["contracts"] and "antd.button" in d["contracts"])

# 5. 主题传播
from engine.kit import Kit
tg = Kit.load().load_tokens("ant-design")
affected = tg.affected_by("color.brand.primary")
check("5. theme propagation: brand.primary → button/badge/menu",
      {"button.primary.background", "badge.background", "menu.item.selected"} <= affected,
      str(sorted(affected)))

# 6. .pen 结构自检（实时 MCP 需运行中的 Pencil，此处跑确定性自检）
rc, out = cli("pencil-verify", "pencil/generated/user-permissions-page.pen")
d = json.loads(out)
check("6. pencil .pen structural self-check", d["passed"],
      f"refs={d['checks']['ref_count']} vars={d['checks']['variable_count']}")

# 7. 学习闭环（已落盘的 input placeholder<=50 规则应拦截长 placeholder）
rc, out = cli("validate-ops", "fixtures/violations/feedback-placeholder-too-long.json")
d = json.loads(out)
corr_exists = (ROOT / "memory/corrections.jsonl").exists()
check("7. feedback loop: persisted correction now blocks the case",
      d["passed"] is False and corr_exists)

# 8. AI 全链路（notification-settings-page 生成产物存在且通过）
for p in ["fixtures/notification-settings-page/graph.json",
          "pencil/generated/notification-settings-page.pen",
          "generated-code/notification-settings-page/NotificationSettingsPage.tsx"]:
    check(f"8. AI e2e: {p} exists", (ROOT / p).exists())
rc, out = cli("validate-ops", "fixtures/notification-settings-page/ops.json")
d = json.loads(out)
check("8. AI e2e: notification page validates clean", d["passed"])

# 9. 编译链路：shadcn 体系从 URL 源经 ingest→compile 产出（非手写）
shad_sys = ROOT / "systems/shadcn/system.json"
shad_snap = ROOT / "systems/shadcn/sources/shadcn-docs.snapshot.json"
shad_contracts = list((ROOT / "systems/shadcn/components").glob("*.contract.json"))
check("9a. compile pipeline: shadcn system + snapshot exist",
      shad_sys.exists() and shad_snap.exists())
snap = json.loads(shad_snap.read_text(encoding="utf-8"))
sysm = json.loads(shad_sys.read_text(encoding="utf-8"))
provenance_ok = (snap.get("sourceUrl", "").startswith("https://ui.shadcn.com")
                 and sysm.get("source", {}).get("kind") == "url")
check("9b. compile pipeline: snapshot source = shadcn URL (real ingestion)", provenance_ok,
      snap.get("sourceUrl", ""))
check("9c. compile pipeline: 3 contracts compiled (button/input/card)", len(shad_contracts) == 3,
      f"{len(shad_contracts)} contracts")
# 契约的 sourceEvidence 指向源 URL（可审计，非脑补）
ev_ok = all(any("ui.shadcn.com" in e for e in json.loads(c.read_text(encoding="utf-8")).get("sourceEvidence", []))
            for c in shad_contracts)
check("9d. compile pipeline: contracts cite source URL in evidence", ev_ok)
# compile-context 可跑
rc, out = cli("compile-context", "--system", "shadcn", "--snapshot", str(shad_snap))
ctx_ok = rc == 0 and json.loads(out)["systemDefaults"]["newSystem"] is False and \
         len(json.loads(out)["componentIdsInSnapshot"]) == 3
check("9e. compile pipeline: compile-context runs (newSystem + 3 ids)", ctx_ok)
# shadcn 契约全过 schema
rc, _ = cli("validate-contracts", "systems/shadcn/components/*.json")
check("9f. compile pipeline: shadcn contracts schema-valid", rc == 0)
# shadcn 页面可编译（多体系可用）
rc, _ = cli("compile-code", "fixtures/shadcn-login-page/graph.json", "--framework", "react",
            "-o", "generated-code/shadcn-login-page/ShadcnLoginPage.tsx")
tsx = (ROOT / "generated-code/shadcn-login-page/ShadcnLoginPage.tsx").read_text(encoding="utf-8")
check("9g. compile pipeline: shadcn page → real React import",
      rc == 0 and "@/components/ui/card" in tsx)

print("\n" + "=" * 50)
passed = sum(1 for _, ok, _ in results if ok)
print(f"{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
