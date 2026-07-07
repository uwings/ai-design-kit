---
name: adk-kit-retrieval
description: Assembles the minimal knowledge pack for a design task by reading files + intent routing (no vectors in v1). Returns global rules, relevant ontology, candidate component cards, the full contracts you’ll actually use, related patterns, the needed token subgraph, and good/bad examples. Use BEFORE planning any page, or when the user asks "what component should I use for X".
---

# Kit Retrieval (minimal knowledge pack)

The model never holds the whole component library in context. You load only what the current task needs.

## How to use
```
python -m engine.cli retrieve --intent "<intent>" --system ant-design [--query "..."] 
```
Optionally pass `include_contracts` (in code) to force-load specific components.

## Intents (from shared/ontology/intent-taxonomy.json)
`primary_action`, `secondary_action`, `destructive_action`, `destructive_confirmation`, `navigation`, `data_management`, `data_entry`, `filtering`, `search`, `bulk_action`, `empty_state`, `status_display`, `toggle`, `feedback`, `content`, `section`.

## What the pack contains (4-level context)
- **L0/L1** candidate component cards (summary, key variants, useWhen/doNotUseWhen)
- **L2** full contracts of the components you’ll actually use (loaded on demand, not the whole library)
- relevant composition patterns + page scenarios
- **token subgraph** — only tokens consumed by those components (resolved for light/dark)
- global hard rules summary + top anti-patterns
- good/bad examples from those contracts

## When unsure which component
Read `shared/ontology/component-decision-tree.json` — it walks "user triggering an action? / showing records? / entering data? / conveying state?" to the right component + intent.

## Backend note
v1 backend = `fileread` (deterministic, explainable, auditable). Vector/semantic recall is a reserved backend implemented when the Knowledge Compiler (KC) is hooked up (`engine.ingest.export_for_kc`). Never treat similarity as a constraint — only contracts/rules validate.
