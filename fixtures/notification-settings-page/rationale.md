# 设计理由 — 通知偏好设置页（AI 端到端 demo）

> 这是由 agent 遵循 `adk-pencil-page-designer` skill 从自然语言全新生成的页面，证明 AI 半边端到端成立（区别于 `user-permissions-page` 那份预置的确定性 fixture）。

## 流程（完全按 skill 走）
1. **Intent** — 通知偏好设置页；意图 `data_entry` + `toggle`。
2. **Retrieve**（`retrieve --intent data_entry`）— 召回 `antd.form / antd.input / antd.select / antd.switch`；查 form 契约得知 `slot.fields` 接受 switch、`slot.submit` 接受 button、必填 `onFinish`。
3. **Plan** — 一个 vertical Form；fields slot 放三个 Switch（每个带 ariaLabel）；submit slot 放一个 primary Button（全组仅 1 个 primary）。
4. **Ops** — 只输出语义操作（`component.insert` + 两次 `component.fillSlot`）。
5. **Validate** — `validate-ops` passed，0 blocking。
6. **Compile** — 同一语义图 → Pencil `.pen` + React（真实 `import { Form } from "antd"` 等）。
7. **Pen self-check** — refs_only / component_identity / no_hardcoded_color 全绿。

## 关键点
- 100% 注册组件，无 raw imitation。
- 每个 Switch 带 `ariaLabel`（无障碍）。
- primary CTA 仅 1 个（`primary_max_one_per_action_group` 通过）。
- 主题 token 经变量承载，无散落 hex。

证明：给定一段自然语言需求，系统能输出一个 100% 使用注册组件、通过设计规则校验、可同时编译为 Pencil 与 React 的页面。
