# shadcn/ui 体系 — 编译链路实跑产物

> ⚠️ 本体系的 3 个契约 + token 图 + system.json **不是手写的**，而是由 Source Ingestion → Contract Author 编译链路从公开文档 URL 自动编译产出。这是 ADK"系统是编译器"核心能力的实跑证明。

## 源
- URL: https://ui.shadcn.com/docs/components （button / input / card 三页）
- 抓取：`web_reader` 把三页转 markdown；agent 从 markdown 抽取事实（import / props / variants / slot-like areas / evidence）

## 复跑命令（端到端）
```bash
# 1) agent 抽取的 raw 事实 → 归一化 snapshot（engine 确定性）
python -m engine.cli ingest-snapshot --system shadcn --from url \
  --raw <raw-facts.json> --url https://ui.shadcn.com/docs/components \
  --out systems/shadcn/sources/shadcn-docs.snapshot.json

# 2) 取编译上下文（engine 给 AI 的约束包）
python -m engine.cli compile-context --system shadcn \
  --snapshot systems/shadcn/sources/shadcn-docs.snapshot.json

# 3) AI 据上下文从事实编译契约/token/system，引擎 schema 校验后落盘
python -m engine.cli write-system   --system shadcn --file <system.draft.json>
python -m engine.cli write-tokens   --system shadcn --file <token-graph.draft.json>
python -m engine.cli write-contract --system shadcn --file <button.draft.json>
python -m engine.cli write-contract --system shadcn --file <input.draft.json>
python -m engine.cli write-contract --system shadcn --file <card.draft.json>

# 4) 重建索引 + 自检
python -m engine.cli index
python -m engine.cli validate-contracts systems/shadcn/components/*.json
python -m engine.cli validate-tokens --system shadcn
```

## 跨体系说明
- shadcn 用 `variant` 轴（default/secondary/destructive/outline/ghost/link），与 antd 的 `intent` 轴不同。编译出的契约忠实于 shadcn 的真实 API。
- `validatorFnNames` 里的 `destructive_requires_confirmation` 检查 `intent==danger`（antd 语义）；对 shadcn 的 `variant=destructive`，契约以 softRule 表达"破坏性须确认"。跨体系 fn 泛化是后续扩展。
- 增量补齐 shadcn 其余组件 = 重复本流程（往 snapshot 加事实 → `compile-context` → `write-contract`）。

## 设计时使用
```bash
python -m engine.cli retrieve --intent data_entry --system shadcn   # 召回 shadcn.input + token 子图
```
