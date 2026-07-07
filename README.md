# AI Design Kit 2.0 (ADK)

> 把设计规范编译成 AI 可消费、可校验、可执行的组件契约。AI 只操作组件图，不直接画像素/写 HTML。

## 这是什么

ADK 是一套**让 AI 基于组件库做可控设计**的系统。核心是**编译器**：把设计规范源（Figma / 代码 + Code Connect / Storybook / 品牌官网 / 公开规范）编译成标准的 **组件契约 + Token 图 + 组合语法**，产出到文件系统；设计时 AI 按需读取最小知识包，**只能通过受控语义操作**生成页面，违规被确定性 validator 拦截。

```
设计规范源 (Figma / 代码 / Storybook / 官网 URL / 公开文档)
  ↓ [编译]  engine/ingest → contract-author → token-graph
组件契约 + Token 图 + 组合语法（框架无关 JSON）
  ↓ [生成]  AI 只输出语义操作（component.insert / setProp / fillSlot / ...）
语义设计图 (Component Graph) —— 唯一真相源
  ↓ [校验]  engine/validator（component/slot/variant/token/layout+a11y）
  ↓ [编译]  engine/compilers/pencil + react + html
Pencil 设计图 / React 代码 / HTML（都是编译目标，来自同一语义图）
```

## 核心原则

1. AI 不生成最终设计文件；AI 生成对组件图的操作。
2. 组件库不是 UI 资产仓库，是 AI 可调用的设计 API。
3. AI 可以提方案，但 AI Design Kit 决定它能不能落地。
4. Pencil 和 HTML 都是"编译目标"，不是"设计源"。
5. 模型负责语义推理；Kit 负责长期知识；Validator 负责硬约束；Compiler 负责确定性输出；Memory 负责持续学习。

## 目录

```
kit.json                     Kit 元信息 + 版本 + 已注册体系
schemas/                     全套 JSON Schema（系统骨架）
systems/<system>/            多体系共存（ant-design/、material/、custom/…）
  components/*.contract.json  组件契约
  tokens/                     Token 图（四层 + 别名 + 模式）
  compositions/               组合模式
  ontology/ mappings/ examples/ pencil/
shared/                      跨体系意图本体 + 规则 + 页面模式
engine/                      确定性 Python 编译器/校验器/渲染器 + CLI
index/                       编译器派生产物（cards + 意图路由表，文件直读）
semantic/generated/          AI 生成中间产物（plan/ops/graph）
pencil/generated/            编译出的 .pen
generated-code/              编译出的 React/HTML
reports/                     校验/审查/发布报告
memory/                      持久化学习（corrections.jsonl）
fixtures/                    规范 demo + 违规样本
.claude/skills/adk-*         13 个 AI 编排 skill
docs/origin/                 原始资料（需求文档 / PDF 圣经 / PY 残片 / Codex 对话）
```

## 快速开始

```bash
# 校验所有 Ant Design 契约 + token 图
python -m engine.cli validate-contracts systems/ant-design/components/*.json
python -m engine.cli validate-tokens --system ant-design

# 编译索引（生成 cards + 意图路由表）
python -m engine.cli index

# 设计时检索：按意图组装最小知识包（文件直读 + 意图路由，无向量）
python -m engine.cli retrieve --intent "破坏性操作确认" --system ant-design

# 确定性管线：语义图 → Pencil + React
python -m engine.cli compile-pencil fixtures/user-permissions-page/graph.json -o pencil/generated/user-permissions-page.pen
python -m engine.cli compile-code   fixtures/user-permissions-page/graph.json --framework react -o generated-code/user-permissions-page

# 校验语义操作（含违规拦截）
python -m engine.cli validate-ops fixtures/user-permissions-page/ops.json
```

端到端 AI 设计走 skill：`adk-orchestrator` → `adk-pencil-page-designer`（见 `.claude/skills/`）。

## 多体系接入

加一套设计规范 = 往 `systems/<新体系>/` 放文件 + 跑 `compile` + `index`，架构不写死：

```bash
python -m engine.cli ingest <新体系> --source figma --figma-key <key>   # 或 --source url --url <品牌官网>
python -m engine.cli compile <新体系>
python -m engine.cli index
```

## 成熟度

- **Level 1 组件可用**：AI 知道有哪些组件/props/variants/tokens。
- **Level 2 组件可控**（v1 目标）：AI 只能通过合法 operation 使用组件，违规被 validator 拦截。
- **Level 3 组件有设计判断**（预留）：AI 知道场景/意图/信息层级/组合模式/反例/审美偏好。

## 向量检索 / KC 接入（预留）

v1 设计时直接读文件 + 意图标签路由，不建向量库。语义向量检索与召回是**接入知识编译引擎（KC）**时的扩展点：KC 消费本 Kit 编译产物（`engine.ingest.export_for_kc`）建向量副本，届时 `engine.retriever` 切换 `kc` 后端即可。

## 起源

本项目三周前在 Codex Desktop 落地过一版，因 OneDrive 同步误删全部丢失，仅抢救回需求文档、PDF 架构圣经、PY 入口残片、Codex 对话记录。本仓库据此在 Claude Code 重构。原始资料见 `docs/origin/`。
