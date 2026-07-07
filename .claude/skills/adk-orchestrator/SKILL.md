---
name: adk-orchestrator
description: Orchestrates end-to-end AI Design Kit workflows — build a kit from a design system, generate a governed page from natural language, or fold a human correction into durable rules. Use when the user asks to "build/compile/generate the ADK", "design/generate a page using the component library", or "fix/learn from this design feedback". Routes to the right specialist skill and never does specialist work directly.
---

# ADK Orchestrator

You coordinate the AI Design Kit pipeline. **Never perform specialist work directly** — delegate to the right `adk-*` skill. ADK = compiler: sources → contracts + token graph + composition grammar → filesystem; at design time AI reads files + intent-routed retrieval, and may only emit semantic operations (validated by `engine/`).

## Three workflows

### A. Build / update the Kit (from a design system)
When the user wants to ingest a design system (Figma / code+Code Connect / Storybook / brand URL / public spec) and compile it into the ADK:
1. `adk-source-ingestion` → `systems/<sys>/sources/*.snapshot.json`（facts only, no inference）
2. `adk-contract-author` → `systems/<sys>/components/*.contract.json`
3. `adk-token-graph` → `systems/<sys>/tokens/token-graph.json`
4. `adk-composition-grammar` → `systems/<sys>/compositions/*.pattern.json`
5. `adk-contract-reviewer` → `reports/contract-review/`
6. `adk-pencil-library-compiler` → `systems/<sys>/pencil/<sys>.lib.pen`
7. `index`（`python -m engine.cli index`）→ `index/*`
8. `adk-release-manager` → version bump

Then verify: `python -m engine.cli validate-contracts && validate-tokens --system <sys>`.

### B. Generate a governed page (from natural language)
1. `adk-kit-retrieval` — parse intent, assemble minimal knowledge pack (`python -m engine.cli retrieve --intent "..." --system <sys>`)
2. `adk-pencil-page-designer` — semantic plan → **semantic ops only** (`component.insert / setProp / setVariant / fillSlot / ...`)
3. `python -m engine.cli validate-ops <ops.json>` — must pass before compiling
4. `python -m engine.cli compile-pencil` + `compile-code` — same semantic graph → Pencil + React/HTML
5. `adk-pencil-validator` — `pencil-verify` via live Pencil MCP (batch_get/get_variables/snapshot_layout/get_screenshot)
6. write `reports/design-rationale/*.md`

**Forbidden**: raw visual nodes, hardcoded colors, detach instance, unregistered components, compiling code from .pen.

### C. Fold in a correction (learning loop)
1. classify the feedback (semantic/usage/token/visual/composition/code/pencil)
2. `adk-feedback-learner` → `python -m engine.cli apply-correction <correction.json>` (persists to `memory/corrections.jsonl` + patches contract/rule/example)
3. rerun affected validators; confirm the rule now catches the case
4. `adk-release-manager` → patch/minor bump

## Hard rules (never violate)
- Every generated screen produces: `semantic/*.graph.json`, `semantic/*.ops.json` (or `fixtures/`), `pencil/generated/*.pen`, `reports/validation/*.json`, rationale.
- AI only emits semantic ops; all rendering/compilation/validation is deterministic in `engine/`.
- Multiple design systems coexist under `systems/<sys>/` — never hardcode one.
- Vector retrieval is reserved for KC integration; v1 reads files + intent routing.

## Routing cheatsheet
| user says | skill |
|---|---|
| "把这套 Figma/官网规范编译成 ADK" | workflow A |
| "做一个 XX 页面" / "生成 admin 后台" | workflow B |
| "以后这类操作必须 XX" / "这个设计不对，记住" | workflow C |
| "换个主题色" / "整体调成紫色" | `token.reference` on semantic token (theme.switch), then recompile |
| single stage only | the matching `adk-*` specialist |
