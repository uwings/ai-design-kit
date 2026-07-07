# AI Design Kit 2.0 — 需求文档

> 写给 Claude Code 落地。本文档定义 What 和 Why，不定义 How。CC 根据自身经验和技术判断选择最优实现方案。

---

## 一、背景

### 这是什么

AI Design Kit（ADK）是一套**让 AI 基于组件库做可控设计**的系统。

核心理念：**AI 不直接生成 HTML/CSS，也不在画布上自由画像素。AI 只能通过受控的操作协议，操作一个结构化的组件图（Component Graph），最终由确定性引擎渲染和导出。**

### 为什么做

1. **市场刚需** — 多个客户/同事在问"怎么让 AI 根据设计规范生成页面"
2. **差异化** — 市面上的 AI 设计工具（V0、Figma AI、OpenDesign）都是"自由生成"，没有组件级硬约束。ADK 的壁垒是：AI 的每次输出都必须通过组件契约校验
3. **已有积累** — 三周前做了一版原型（已因 OneDrive 误删丢失），有完整的架构设计文档（PDF 134页），有入口脚本（PY 文件），现在要在此基础上做得更好

### 已有素材：三个文件的来源和定位

**⚠️ 这三个文件的背景：** AI Design Kit 项目三周前已经在 Codex 中落地过一版，但完整的产出文件因为 OneDrive 误删全部丢失。以下三个文件是从不同渠道抢救回来的残片。

#### 文件 1：ChatGPT 对话 PDF — **设计思想源头，必须完整读、完整理解、按它做**

- 位置：NAS `项目/ai-design-kit 恢复文件/调查Pencil OpenDesign代码.pdf`
- 来源：项目最初是与 ChatGPT 深度讨论（11分钟思考+4分钟思考）产出的完整架构方案，共 134 页
- 内容：Pencil 和 OpenDesign 代码调查、9层核心架构、13个Skills完整定义、组件契约schema、操作协议、token图、产出物目录结构、MCP配置、三层成熟度模型、上下文管理策略
- **定位：这是本项目的"圣经"。CC 必须完整读取这份 PDF，理解其中的设计思想，并以此为基础进行实现。本文档（需求文档）中的所有模块定义都是从这份 PDF 提炼的，但 PDF 里有更多细节、推理过程和设计理由。遇到不确定的地方，以 PDF 原文为准。**

#### 文件 2：入口脚本 PY — **误删抢救回来的唯一代码片段**

- 位置：NAS `项目/ai-design-kit 恢复文件/generate_ant_ai_gateway_admin.py`
- 来源：三周前 Codex 落地的项目中，唯一幸存的代码文件（从 Codex 对话记录的代码块中提取）
- 内容：ADK 的入口编排脚本，展示了目录结构（`ai-design-kit/components/`、`ai-design-kit/tokens/`、`ai-design-kit/coverage/`）、25个 Ant Design 组件列表、9个 token 引用、component.insert 操作格式
- **定位：这是从废墟里捡回来的碎片，不是完整实现。它证明了项目确实落地过、目录结构长什么样、操作格式与 PDF 定义的 Operation Protocol 一致。CC 参考它来理解目录结构和操作格式即可，不需要还原这个脚本本身。**

#### 文件 3：Codex 对话记录 JSONL — **误删抢救回来的对话历史**

- 位置：NAS `项目/ai-design-kit 恢复文件/rollout-2026-07-07T17-25-58-*.jsonl`
- 来源：Codex Desktop 的本地 session 记录（`~/.codex/sessions/` 目录），记录了三周前 Codex 基于 PDF 尝试落地的完整对话过程
- 内容：用户消息（明文）、Codex 的文字回复（明文）、Codex 的工具调用记录（shell_command 明文）。Codex 的内部推理过程（reasoning）是加密的，不可读
- **定位：这是 Codex 落地过程的"黑匣子记录"。从对话可以看到 Codex 当时做了什么——读 PDF、检查工作区（发现是空的）、尝试调用 skill-creator 和 baoyu-url-to-markdown。但实际写入磁盘的文件已经跟着 OneDrive 一起没了。CC 可以参考它了解当时的落地思路，但不要求还原 Codex 的具体做法。**

### 与 KC 引擎的融合机会

作者有一套运行中的知识编译引擎（KC），核心链路是：
```
多源数据 → 编译成结构化知识词条 → 向量索引 → 按需装配输出
```

ADK 的链路是同构的：
```
设计规范源 → 编译成组件契约(Component Contract) → 检索索引 → 按需生成设计页面
```

融合方向（CC 自行判断是否纳入 2.0）：
- 组件契约可以做成 KC 式的"设计知识库"，支持增量编译和语义检索
- 设计生成可以像 KC 的 assemble 一样：意图理解 → 语义召回组件 → 排序 → 组装
- 反馈学习可以像 KC 的 correction 机制一样：纠错 → 更新契约 → 下次自动生效

---

## 二、核心目标

### 必须实现的能力

1. **把一套设计规范（如 Ant Design）编译成 AI 可消费的组件契约**
2. **AI 基于组件契约生成页面，但只能通过受控操作，不能直接写 HTML**
3. **生成的页面可以被校验——组件是否合法、slot 是否正确、token 是否合规**
4. **人类纠错可以被固化成系统知识，越用越准**

### 衡量标准

- 给一段自然语言需求（如"做一个企业后台的用户权限管理页面"），系统能输出符合设计规范的页面
- 生成的页面**100% 使用注册组件**，不出现手画 UI
- 生成的页面通过设计规则校验（token 合规、slot 合法、variant 正确）
- 人类纠错后，同类问题不再重复出现

---

## 三、系统架构（CC 可在此基础上优化）

PDF 中定义的核心架构分 9 层。CC 可以参考但不必照搬，以最终效果为准。

### 3.1 整体数据流

```
设计规范源（Figma / 代码 / Storybook / 文档）
  ↓ [编译]
组件契约 (Component Contract) + Token 图 + 组合语法
  ↓ [索引]
可检索的 AI Design Kit
  ↓ [生成]
语义操作列表 (Semantic Operations)
  ↓ [校验]
合法的设计图 (Component Graph)
  ↓ [渲染]
多目标输出（Pencil 设计图 / React 代码 / HTML / PDF）
```

### 3.2 核心原则

PDF 提出了最重要的设计原则，这些是**不可妥协的**：

1. **AI 不生成最终设计文件；AI 生成对组件图的操作**
2. **组件库不是 UI 资产仓库；组件库是 AI 可以调用的设计 API**
3. **AI 设计师可以提出方案，但 AI Design Kit 决定它能不能落地**
4. **Pencil 和 HTML 都应该是"编译目标"，不是"设计源"**
5. **上下文窗口的分层管理——模型不"记住整个组件库"，而是通过检索拿到当前任务所需的最小知识包**

---

## 四、模块定义

PDF 定义了 13 个 Skills。CC 可以按自身判断选择实现方式（Skill 目录 / Python 模块 / CLI 子命令 / MCP 工具，都可以），但以下功能模块必须存在：

### 模块 1：源数据接入（Source Ingestion）

**输入**：Figma 组件库 / Code Connect / 组件源码 / Storybook / 设计文档 / 已有页面

**输出**：归一化的源数据快照（JSON）

**行为要求**：
- 从生产源头抽取事实，不做语义推断
- 每个组件记录：名称、Figma key/node id、variants、properties、variables、嵌套实例、slot 区域、代码 import 路径、prop 类型和名称、Storybook 示例、文档说明
- 优先级：Figma MCP > Code Connect > 组件源码 > Storybook > 设计文档 > 生产页面
- "严禁脑补" — 只采集有证据的事实

**验收标准**：给定一个 Figma 组件库 URL 或 MCP 接入，系统能输出该库所有组件的结构化快照。

### 模块 2：组件语义（Component Semantics）

**输入**：源数据快照

**输出**：组件本体论（ontology）— 每个组件的"设计意义"

**行为要求**：
- 为每个组件定义：语义角色（semantic role）、适用场景（whenToUse）、禁用场景（whenNotToUse）、variant 语义、state 语义、关联组件、替换逻辑、用户意图映射、风险等级
- 描述设计意义，不是描述视觉外观
  - ❌ "Button 是一个带文字的圆角矩形"
  - ✅ "Button 在当前决策上下文中触发明确的用户操作"
- 每条语义判断必须标注来源证据和置信度
- 低置信度的判断不能变成硬规则

**验收标准**：给定一个 Button 组件，系统输出的语义描述能让一个不懂前端的人理解"什么时候该用它、什么时候不该"。

### 模块 3：Token 图（Token Graph）

**输入**：Figma variables / CSS 变量 / code tokens / 设计文档

**输出**：Token 依赖图 + 主题模式 + Token-组件绑定

**行为要求**：
- Token 分层：primitive（原值）→ semantic（语义别名）→ component（组件级）→ state（状态级）
- 记录每个 token 的：id、类型、值或别名引用、模式（亮色/暗色）、引用关系、消费者（哪些组件用它）、来源证据
- 主题切换行为：不直接改组件颜色，改 semantic token，让别名传播
- 检测：别名循环、缺失模式、硬编码值、孤儿 token

**验收标准**：系统能回答"如果主题从亮色切到暗色，哪些组件的什么属性会变化"。

### 模块 4：组合语法（Composition Grammar）

**输入**：组件语义 + Token 图

**输出**：页面模式库 + slot 规则 + 反模式

**行为要求**：
- 定义组件之间的组合规则：哪些组件可以放在哪些 slot 里、什么顺序、什么层级
- 常见页面模式：设置页、仪表盘、数据表格+筛选、定价页、空状态、破坏性确认流程等
- 每个模式定义：必需组件、可选组件、组件顺序、slot 规则、按上下文允许的 variants、响应式行为
- 反模式：什么组合是错的、怎么修复

**验收标准**：系统能判断"一个定价页里把 CTA 按钮放在最底部是否合理"。

### 模块 5：组件契约（Contract Author）

**输入**：源数据 + 语义 + Token 图 + 组合语法

**输出**：每个组件的机器可读契约（JSON）

**行为要求**：

每个契约必须包含：
- id、version、displayName、来源引用
- 语义角色、含义
- variants（变体）及其语义差异
- props（属性）：类型、是否必需、约束（maxLength、enum 等）
- slots（插槽）：接受哪些组件、最大数量
- states（状态）
- token 绑定
- 组合规则
- Pencil 映射
- 代码映射
- 正面示例和反面示例
- 硬规则（可机器校验）和软规则（需人工/critic 判断）
- 来源证据和置信度

**关键规则**：
- 硬规则必须是可程序化校验的（schema rule / graph rule / token rule / slot rule / validator function）
- 不要用长篇文字描述能用结构化字段表达的东西
- 低置信度的判断标记为 needsReview

**验收标准**：给定一个组件（如 Ant Design Table），系统能输出一份完整契约，包含"如果 variant=striped，则 row.background 必须使用 token color.bg.subtle"这类可校验的规则。

### 模块 6：契约审查（Contract Reviewer）

**输入**：组件契约

**输出**：审查报告（blocking / risky / improvement / question）

**行为要求**：
- 检查项：
  - 语义角色是否与实际用法一致
  - variants 是否语义明确（不是视觉微调）
  - props 是否映射到 Figma、Pencil、代码三端
  - token 绑定是否完整
  - 禁止的 override 是否指定
  - slot 约束是否够严
  - 硬规则是否真的可机器校验
  - 是否有反面示例
  - 低置信度判断是否标记待审
- 不直接修改契约，只报告问题

**验收标准**：系统能发现"某个组件的 variant=large 和 variant=spacious 语义重叠，应该合并"这类问题。

### 模块 7：Pencil 库编译器（Pencil Library Compiler）

**输入**：组件契约 + Token 图 + 映射规则

**输出**：Pencil 可用的组件库（.lib.pen 文件或等效产物）

**行为要求**：
- 注册组件变成可复用组件（reusable component）
- 实例必须用 ref 引用
- 可编辑内容用 descendants override
- Token 化的值用 variables
- Slot 区域保留允许的组件元数据
- 每个可复用组件根节点包含元数据：componentId、contractVersion、figmaKey、codeComponent、allowedOverrides、tokenBindings、slotContracts
- 不编译"原始模仿组件"（raw imitation）

**验收标准**：生成的 Pencil 库中，每个组件实例都能追溯到源契约。

> ⚠️ 如果 Pencil 的 MCP/API 限制使得某些功能无法实现，CC 可以选择等效的画布工具或自研预览层。以最终效果为准。

### 模块 8：页面设计器（Page Designer）

**输入**：自然语言需求 + AI Design Kit

**输出**：语义设计图 + 操作列表 + Pencil 生成文件 + 设计理由

**行为要求**（这是核心中的核心）：

强制流程：
1. **意图理解** — 解析用户要做什么类型的页面、什么风格、什么目标
2. **Kit 检索** — 加载相关的 ontology、patterns、components、token 子图（不是全部塞进去）
3. **语义设计计划** — 不是直接出图，而是先规划：页面由哪些组件组成、每个组件承担什么语义角色、每个 slot 填什么
4. **操作列表** — 只输出语义操作（component.insert / setProp / setVariant / fillSlot / bindData / token.reference）
5. **静态校验** — 组件合法、slot 合法、variant 合法、token 合法、响应式合法、无障碍合法
6. **编译到 Pencil** — 用 refs 和 descendants
7. **设计理由** — 解释为什么这么设计

**绝对禁止**：
- 创建原始视觉组件来模仿系统组件
- 直接用 Pencil batch_design 画类组件 UI
- 硬编码 token 化的值
- 分离组件实例（detach instance）
- 覆盖禁止的 descendant 路径

**验收标准**：给定"企业后台用户权限管理页面"，系统能输出一个使用注册组件、通过校验、带设计理由的完整设计。

### 模块 9：设计校验器（Design Validator）

**输入**：Pencil 输出文件 + 组件契约 + Token 图

**输出**：校验报告 JSON + 视觉审查 Markdown + 阻塞问题列表 + 修复建议

**行为要求**：

静态校验：
- 所有 UI 使用注册的 ref
- 无原始模仿组件
- 无硬编码颜色（如果 token 存在）
- descendant override 是允许的
- slot 子组件是允许的
- variant 存在
- props 满足契约
- token variable 存在
- 主题模式完整

MCP 校验（如果可用）：
- batch_get 检查节点
- get_variables 检查 token 使用
- snapshot_layout 检查布局
- get_screenshot 检查视觉效果

**验收标准**：系统能发现"某个 Button 用了 #1890ff 而不是 token variable"这类违规。

### 模块 10：代码编译器（Code Compiler）

**输入**：语义设计图 + 组件契约 + 代码映射

**输出**：可运行的前端代码

**行为要求**：
- **源数据是语义图，不是 Pencil 文件** — 避免从设计图反推代码导致丢语义
- 映射：component id → code import / variant → code prop / props → code props / slots → children composition / tokens → CSS variables / states → component props
- 生成的代码使用真实的组件 API，不是手写 CSS 模仿
- 校验：无一次性 CSS 模仿系统组件、所有注册组件使用真实 import、props 满足组件 API、token 使用批准的变量

**验收标准**：给定同一个语义设计图，系统同时输出 Pencil 设计文件和 React 代码，两者来自同一个语义源，不是互相反推。

### 模块 11：反馈学习器（Feedback Learner）

**输入**：人类纠错 / 设计 review 意见 / 校验失败报告 / 人工修改 diff

**输出**：契约 patch / 规则 patch / 正反示例 / memory/corrections.jsonl

**行为要求**：
- 每条纠错必须变成以下至少一种持久化产物：
  - 组件契约更新
  - 组合规则
  - token 规则
  - 正面示例（good example）
  - 反面示例（bad example）
  - 修复策略
  - 校验器测试
- 纠错分类：语义纠正 / 用法纠正 / token 纠正 / 视觉纠正 / 组合纠正 / 代码映射纠正 / Pencil 映射纠正
- 重要的纠正不只存在对话记忆里，必须落盘
- 输出：patch summary、变更文件、受影响组件、需重跑的校验器

**验收标准**：用户告诉系统"在权限页里，破坏性操作必须放在确认弹窗里"，下次生成同类页面时系统自动遵守这条规则。

### 模块 12：发布管理（Release Manager）

**输入**：组件契约变更 / 新组件 / 规则更新

**输出**：版本化的 Kit 包 + changelog

**行为要求**：
- 发布包含：kit.json + contracts + token graph + composition rules + Pencil library + mappings + validators + examples + changelog
- 版本分类：patch（文档/示例/纠正）/ minor（新组件或非破坏性规则）/ major（重命名组件、删除 variant、改 slot 契约、改 token 语义）
- 发布前检查：校验所有契约、校验 token 图、编译 Pencil 库、跑 fixture 页面、对比截图（如有）

**验收标准**：系统能生成一个可分发的版本包，包含所有必要文件。

---

## 五、目录结构（建议，CC 可调整）

PDF 建议的产出物目录结构：

```
ai-design-kit/
  kit.json                          # Kit 元信息和版本
  AGENTS.md                         # 项目级长期约束（给 agent 读的"世界观"和"底线"）
  sources/                          # 源数据快照
    figma.snapshot.json
    code.snapshot.json
    storybook.snapshot.json
    docs.snapshot.json
    usage-examples.json
  ontology/                         # 组件语义
    component-roles.json
    page-patterns.json
    intent-taxonomy.json
    component-decision-tree.json
  tokens/                           # Token 系统
    tokens.json
    token-graph.json
    theme-modes.json
    token-bindings.json
  components/                       # 组件契约（每个组件一个文件）
    button.contract.json
    modal.contract.json
    data-table.contract.json
    ...
  compositions/                     # 组合模式
    dashboard-page.pattern.json
    settings-page.pattern.json
    pricing-page.pattern.json
    form-flow.pattern.json
  mappings/                         # 多端映射
    figma-to-kit.json
    kit-to-pencil.json
    kit-to-react.json
  pencil/                           # Pencil 产出
    product.lib.pen
    examples.pen
    generated/
      user-permissions-page.pen
  semantic/                         # 语义设计图（AI 生成的中间产物）
    generated/
      user-permissions-page.graph.json
      user-permissions-page.ops.json
  reports/                          # 校验和审查报告
    validation/
    visual-review/
    contract-review/
    release/
  examples/                         # 正反示例
    good/
    bad/
  memory/                           # 持续学习记忆
    corrections.jsonl
  rules/                            # 规则
    composition-rules.json
```

---

## 六、上下文窗口管理（关键设计）

PDF 提出了非常重要的上下文管理策略。**这是系统能不能在真实组件库上跑起来的关键。**

### 四层上下文形态

每个组件有四种上下文形态，按需加载：

| Level | 名称 | 大小 | 用途 |
|-------|------|------|------|
| 0 | index | ~10 token | 一句话摘要，用于搜索和初筛 |
| 1 | card | 100-300 token | 说明用途、主要 variants、主要禁忌 |
| 2 | contract | 完整 JSON | 真正使用该组件时加载 |
| 3 | deep context | 大 | 示例、反例、截图、源码、Figma 节点、历史纠错，只在复杂场景加载 |

### 一次页面生成时模型看到的应该是

```
全局设计原则摘要
  ↓
相关 ontology 摘要
  ↓
候选组件 card（Level 1）
  ↓
实际使用组件的 full contract（Level 2）
  ↓
相关 composition pattern
  ↓
必要 token 子图
  ↓
少量 good / bad examples
```

**模型不是"记住整个组件库"，而是通过检索拿到当前任务所需的最小知识包。**

---

## 七、三层成熟度

PDF 定义了三层成熟度。**2.0 版本应瞄准 Level 2，预留 Level 3 接口。**

| Level | 名称 | 能力 | 状态 |
|-------|------|------|------|
| 1 | 组件可用 | AI 知道有哪些组件、props、variants、tokens | 基础 |
| 2 | 组件可控 | AI 只能通过合法 operation 使用组件，违规被 validator 拦截 | **2.0 目标** |
| 3 | 组件有设计判断 | AI 知道场景、意图、信息层级、组合模式、反例、审美偏好 | 3.0 预留 |

---

## 八、MCP 配置（建议）

PDF 建议的 MCP 配置，CC 可以根据实际环境调整：

- **Figma MCP** — 读取 Figma 组件库（通过 Figma API / Figma MCP Server）
- **Pencil MCP** — 操作 Pencil 设计文件（get_screenshot / snapshot_layout / batch_get / get_variables / set_variables）
- **Playwright MCP** — 浏览器自动化（截图 QA / 视觉对比）
- **GitHub MCP** — 代码库访问

---

## 九、第一版交付优先级

PDF 建议第一版先实现 7 个核心模块。CC 可以按自身判断调整顺序，但以下为建议优先级：

### P0 — 必须先有（没有这些其他模块都跑不起来）

1. **组件契约（Contract Author）** — 定义组件的结构化描述
2. **设计校验器（Design Validator）** — 能判断输出是否合规
3. **页面设计器（Page Designer）** — AI 基于契约生成页面

### P1 — 紧随其后

4. **源数据接入（Source Ingestion）** — 从 Figma/代码自动生成契约
5. **Pencil 库编译器** — 把契约编译成可用的设计库
6. **代码编译器** — 从语义图生成真实代码
7. **反馈学习器** — 固化人类纠错

### P2 — 后续迭代

8. 组件语义、Token 图、组合语法（可以作为 Contract Author 的子能力实现）
9. 契约审查器
10. 发布管理器

---

## 十、参考技术栈（建议，CC 可自选）

PDF 建议：
- TypeScript + Zod / JSON Schema（类型安全）
- React（组件实现）
- Vite 或 Next.js（Web 应用）
- Hono / Fastify（本地服务）
- Playwright / Puppeteer（截图 QA）
- axe-core（无障碍校验）
- pnpm workspace（monorepo）
- plain files（主存储，不用 DB）
- SQLite（可选，仅做索引和缓存）

CC 可以选择更合适的技术栈。唯一硬约束：**组件契约必须是框架无关的 JSON/Schema**，否则会被 React 绑死，后面要导出 HTML、PPTX、SVG 会很痛苦。

---

## 十一、测试策略

### 组件契约测试

给定一个已知组件（如 Ant Design Button），验证：
- 契约包含所有必需字段
- 硬规则真的可程序化校验
- 正反示例存在且合理

### 端到端生成测试

给定"企业后台用户权限管理页面"，验证：
- 生成的页面 100% 使用注册组件
- 通过所有校验（token、slot、variant、layout、a11y）
- Pencil 输出和代码输出来自同一个语义源
- 设计理由存在且合理

### 反馈学习测试

给定一条纠错"破坏性操作必须放在确认弹窗里"，验证：
- 规则被写入持久化文件
- 下次同类页面生成自动遵守
- 校验器新增了对应检查

---

## 十二、CC 的自由度

以下决策**由 CC 自主判断**，本文档不强制：

1. **实现方式** — Skill 目录 / Python 模块 / CLI 子命令 / MCP 工具 / 独立 App，CC 选最合适的
2. **组件库选择** — 第一版用 Ant Design 做验证（PY 文件里已有 25 个组件的列表），但架构要支持多套设计系统
3. **画布工具选择** — PDF 以 Pencil 为例，如果 Pencil 限制太大，CC 可以选择替代方案（自研预览层 / 其他设计工具 MCP）
4. **技术栈选择** — TypeScript / Python / 混合，CC 选最优解
5. **上下文管理实现** — 向量检索 / 分层缓存 / KV 存储，CC 自选
6. **与 KC 引擎的融合程度** — 深度融合 / 轻量借鉴 / 完全独立，CC 评估后决定
7. **渐进式交付策略** — 先跑通哪条链路、先支持哪个场景，CC 按实际可行性排

---

## 十三、参考资料

| 文件 | 位置 | 说明 |
|------|------|------|
| ChatGPT 对话 PDF | `项目/ai-design-kit 恢复文件/调查Pencil OpenDesign代码.pdf` | 134页完整架构讨论，**最核心的参考** |
| 入口脚本 PY | `项目/ai-design-kit 恢复文件/generate_ant_ai_gateway_admin.py` | 暴露了目录结构、Ant Design 组件列表、token 引用方式 |
| Codex 对话 JSONL | `项目/ai-design-kit 恢复文件/rollout-*.jsonl` | Codex 落地过程的对话记录（文件产出已丢失） |

PDF 中的关键内容索引：
- 第 1-5 页：Pencil 和 OpenDesign 的代码调查结论
- 第 5-9 页：核心架构（组件注册中心 / Token 系统 / Design IR / 操作协议 / 布局引擎）
- 第 9-14 页：渲染器、预览器、AI 编排器、Artifact 存储
- 第 15-20 页：MVP 建议、技术栈建议、最重要的设计原则
- 第 21-108 页：AI Design Kit 的深度设计（三层成熟度、上下文管理、生产流程、模块定义）
- 第 109-134 页：13 个 Skills 的完整定义（SKILL.md 全文）、AGENTS.md 全文、MCP 配置、目录结构

---

## 附录：PY 文件中暴露的关键信息

### 目录结构（从代码推断）

```
ai-design-kit/
  coverage/
    ant-design-public-docs.coverage.json    # 组件覆盖率
  tokens/
    token-graph.json                        # Token 依赖图
  components/
    antd.*.contract.json                    # 每个组件一个契约文件
```

### 使用的 Ant Design 组件（25 个）

```
antd.layout, antd.menu, antd.breadcrumb, antd.tabs,
antd.flex, antd.space, antd.typography, antd.card,
antd.statistic, antd.table, antd.tag, antd.badge,
antd.progress, antd.alert, antd.form, antd.input,
antd.select, antd.date-picker, antd.switch, antd.button,
antd.descriptions, antd.timeline, antd.drawer,
antd.modal, antd.divider
```

### 使用的 Token 引用（9 个）

```
font.size.base, font.lineHeight.base, space.grid.unit,
color.text.default, color.text.secondary, color.text.disabled,
color.border.default, color.bg.layout, theme.algorithm.default
```

### 操作类型（从 component_op 函数推断）

```python
{
    "op": "component.insert",
    "componentId": "antd.button",
    "node": { "id": ..., "type": "component", ... },
    "reason": "...",
    "contractRefs": ["antd.button"],
    "parentId": ...,
    "variant": ...
}
```

这与 PDF 中定义的 Operation Protocol 一致。

---

## 总结

**这份需求文档的目标**：让 CC 理解 AI Design Kit 的核心设计思想（AI 只操作组件图，不直接画页面）、完整的功能模块（13 个模块的输入输出和行为要求）、以及与 KC 引擎融合的可能性。

**CC 的任务**：基于这份文档 + PDF 参考资料，设计并实现一个可运行的 AI Design Kit 2.0。不限于还原三周前的方案——可以做得更好、更完整、更实用。

**衡量成功的唯一标准**：给定一段自然语言需求，系统能输出一个 100% 使用注册组件、通过设计规则校验、附带设计理由的页面设计。
