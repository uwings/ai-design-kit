# AI Design Kit (ADK) — 项目指令（给所有 agent 读）

> 本文件是本项目的"世界观 + 底线"。`AGENTS.md` 内容相同，供 Codex/其他 agent 读取。具体流程在 `.claude/skills/adk-*`，确定性逻辑在 `engine/`。

## 产品目标

本仓库构建并使用一套 **AI Design Kit**：设计规范的机器可操作表示。核心是**编译器**——把源（Figma / 代码 + Code Connect / Storybook / 品牌官网 URL / 公开规范文档）编译成标准的**组件契约 + Token 图 + 组合语法**，产出到文件系统，设计时直接读文件使用。

**AI 设计的本质受控**：AI 不直接生成 HTML/CSS，也不在画布自由画像素。AI 只能通过受控的语义操作协议，操作一个结构化的组件图（Component Graph），最终由确定性引擎（`engine/`）渲染与导出。

## 核心规则（不可妥协）

所有设计产出必须流经：

1. **Kit 检索/组装**（读文件 + 意图路由，组装最小知识包）
2. **语义设计计划**（plan.json：哪些组件、各自语义角色、每个 slot 填什么）
3. **语义组件操作**（ops.json：只允许 `component.insert / setProp / setVariant / fillSlot / reorder / bindData / token.reference / theme.switch / layout.applyPattern`）
4. **契约校验**（validator 5 类：component / slot / variant / token / layout+a11y）
5. **编译到 Pencil**（refs + descendants + variables + slots）
6. **Pencil 校验**（可选实时 Pencil MCP：batch_get / get_variables / snapshot_layout / get_screenshot）
7. **（可选）编译到代码**（从语义图，不从 .pen 反推）

## 绝对禁止

- 不要发明未注册的 UI 组件。
- 不要用 raw rectangle/text/frame 模仿 Button / Card / Modal / Table / Badge / Input 等系统组件。
- 不要硬编码颜色、字号、圆角、阴影、间距（当 token 存在时）。
- 不要绕过组件契约（detach instance、覆盖 forbidden descendant、塞错 slot）。
- 不要从视觉节点反推代码——代码必须从语义图编译，否则丢语义。
- 不要把组件规则只写在散文里——必须落进 contracts / rules / examples / validators。
- 不要把重要纠错只存在对话记忆里——必须落盘到 `memory/corrections.jsonl` + 契约/规则 patch。

## 每个生成页面必须产出

- `semantic/generated/*.graph.json`（语义设计图，唯一真相源）
- `semantic/generated/*.ops.json`（语义操作列表）
- `pencil/generated/*.pen`（编译出的 Pencil 文件）
- `reports/validation/*.json`（校验报告）
- `reports/design-rationale/*.md`（设计理由）
- （可选）`generated-code/`（React/HTML）

## 架构定位

- **ADK = 编译器**，不是存储仓库、也不是检索引擎。
- **多体系共存**：`systems/<system>/`（如 `ant-design/`、`material/`、`custom/`）。加体系/组件 = 往对应目录放文件 + 跑 `python -m engine.cli compile <sys> && python -m engine.cli index`，不写死。
- **语义图是唯一真相源**；Pencil 与 HTML/React 都是编译目标，来自同一语义图，不互相反推。
- **向量检索/向量库不在 v1**：设计时直接读文件 + 意图标签路由。向量召回是接入知识编译引擎（KC）时的扩展点（`engine.ingest.export_for_kc`），由 KC 建副本负责语义检索。

## 首选用法

- 端到端 AI 设计任务用 `adk-orchestrator` skill。
- 只做某一阶段时用对应专业 skill（见 `.claude/skills/adk-*`）。
- 确定性操作直接用 `python -m engine.cli <subcommand>`。

## 关键路径

```
systems/<sys>/components/*.contract.json   # 组件契约（框架无关 JSON，骨架）
systems/<sys>/tokens/token-graph.json      # Token 图（四层 + 别名 + 模式）
systems/<sys>/compositions/*.pattern.json  # 组合模式
shared/ontology/intent-taxonomy.json       # 跨体系意图本体（检索路由依据）
shared/rules/*.json                        # 跨体系硬/软规则
schemas/*.schema.json                      # 全套 JSON Schema（系统骨架）
engine/                                    # 确定性 Python 编译器+校验器+渲染器
.claude/skills/adk-*                       # 13 个 AI 编排 skill
```

## 成功标准

给定一段自然语言需求，系统能输出一个 **100% 使用注册组件、通过设计规则校验、附带设计理由**的页面设计；人类纠错后，同类问题不再重复出现。
