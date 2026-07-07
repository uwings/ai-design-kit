---
name: adk-contract-author
description: Compiles component contracts FROM ingested source snapshots (not hand-written). Reads the compiler context (schema/ontology/rules/sibling ids), authors contracts from the facts, and writes them via the engine which schema-validates on write. Use after source-ingestion, or to refresh a system's contracts.
---

# Contract Author（snapshot → 契约）

契约是**编译产物**，不是手写存储。AI 从 snapshot 事实 + 编译上下文编译出契约，引擎校验落盘。

## 流程（可执行）
1. **构建编译上下文**（engine 确定性，给 AI 的约束包）：
   ```bash
   python -m engine.cli compile-context --system <sys> --snapshot systems/<sys>/sources/<src>.snapshot.json [--for-tokens]
   ```
   返回：contractSchema 必填字段、allowedIntentTags、validatorFnNames（可用的 fn 规则）、globalRules、componentDecisionTree、registeredSiblingIds、componentIdsInSnapshot、availableTokenIds、mappingConventions、每组件事实、9 条编译规则。
2. **AI 编译契约**（你，按上下文 + 事实）：为每个组件产出符合 `component-contract` schema 的 JSON。遵循上下文里的 9 条规则（intents⊆allowedIntentTags、tokenBindings⊆availableTokenIds、slots.accepts⊆sibling ids、hardRules 可机器校验且 fn 名∈validatorFnNames、code.propMap 与 mappings 一致、低置信→needsReview）。
3. **校验落盘**（engine 确定性，schema 守门）：
   ```bash
   python -m engine.cli write-contract --system <sys> --file <draft.json>
   python -m engine.cli write-tokens   --system <sys> --file <token-graph-draft.json>
   python -m engine.cli write-system   --system <sys> --file <system.json>
   ```
   引擎对契约/token 图跑 schema 校验，通过才落盘到 `systems/<sys>/components|tokens/`。
4. **重建索引**：`python -m engine.cli index`（cards + 意图路由表）。
5. 验证：`validate-contracts systems/<sys>/components/*.json && validate-tokens --system <sys>`。

## 契约必填字段
`id, version, system, displayName, sourceRefs, semanticRole, intents, meaning{definition,useWhen,doNotUseWhen}, variants, props, slots, states, tokenBindings, compositionRules, pencil, code, examples{good,bad}, hardRules, softRules, sourceEvidence, confidence, needsReview`。

## 关键纪律
- **meaning 写设计意义非视觉**（❌"圆角矩形带文字" ✅"触发用户操作"）。
- **hardRules 必须可机器校验**：图级用 `kind:"fn"` + `expr:"fn:<name>"`（name∈validatorFnNames）；其余 schema/graph/token/slot + 具体 expr。跨体系的 fn 规则按本体系语义映射（如 shadcn 破坏性是 variant=destructive 而非 intent=danger，写 soft rule 或提 validator 扩展）。
- **sourceEvidence 指向 snapshot 证据**（URL + snapshot 路径），严禁脑补。
- 低置信 `needsReview:true`，且不得成为 hardRule。

## 实跑范例
`systems/shadcn/` 的 3 契约 + token 图 + system.json 全部由本流程从 `shadcn-docs.snapshot.json` 编译产出，引擎校验落盘，`validate-contracts` 全过。复跑命令见 `systems/shadcn/README.md`。
