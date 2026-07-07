---
name: adk-source-ingestion
description: Ingests production design-system sources into normalized snapshots — public spec/brand URL, Figma (MCP), code + Code Connect, Storybook. Extracts facts only, never infers semantics. Use when adding/refreshing a design system ("把这套规范接入 ADK", "ingest this Figma / this brand site URL").
---

# Source Ingestion（源 → 快照）

系统是**编译器**：不存储预置契约，而是从源**采事实**。本 skill 只采事实，**严禁脑补**——语义推断在 `adk-contract-author`。

## 流程（可执行）
1. **抓取源**（agent 持有工具；engine 不联网）：
   - 公开规范/品牌 URL → `baoyu-url-to-markdown` skill 或 `web_reader` 抓成 markdown
   - Figma → Figma MCP（`get_code_connect_map` / `get_variable_defs` / `search_design_system` / `get_context_for_code_connect`）
   - 代码/Code Connect → 代码扫描 / GitHub MCP
   - Storybook → 抓 stories
2. **抽取事实**：从抓取内容里提取每个组件的 `name / codeImport / props[{name,type,values}] / variants / slot-like areas / evidence(URL)`。只采页面上有证据的；采不到的留空，不要编。
3. **归一化 → snapshot**（engine 确定性步）：
   ```bash
   python -m engine.cli ingest-snapshot --system <sys> --from url|figma|code|docs \
     --raw <raw.json> --url <url> --out systems/<sys>/sources/<source>.snapshot.json
   ```
   `raw.json` = `{components:[...], tokenRefs:[...], url, notes}`（agent 抽取的事实）。
4. 产出：`systems/<sys>/sources/*.snapshot.json`（schemaVersion/system/sourceKind/sourceUrl/components/tokenRefs/coverage）。

## 采集优先级
Figma MCP > Code Connect > 组件源码 > Storybook > 设计文档 > 生产页面。

## 纪律
- 每个事实带 `evidence`（URL/文件/node id）。无证据不写。
- **不**推断 whenToUse/risk/语义角色——那是 Contract Author 的事。
- 多源共存：每个体系独立 `sources/`。

## 实跑范例（见 `systems/shadcn/`）
shadcn/ui 三页（button/input/card）URL → markdown → 抽事实 → `ingest-snapshot --from url` → `shadcn-docs.snapshot.json`（3 组件）。可复跑。
