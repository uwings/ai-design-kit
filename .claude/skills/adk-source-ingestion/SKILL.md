---
name: adk-source-ingestion
description: Ingests production design-system sources into normalized snapshots — Figma (MCP), code + Code Connect, Storybook, brand website / public spec URL. Extracts facts only, never infers semantics. Use when adding a new design system or refreshing an existing one ("把这套规范接入 ADK", "ingest this Figma / this brand site").
---

# Source Ingestion

Extract **facts** from production sources into `systems/<sys>/sources/*.snapshot.json`. **No inference here** — semantics come later in `adk-contract-author` with confidence + evidence.

## Source priority
Figma MCP > Code Connect > component source code > Storybook > design docs > production pages.

## The two real-world source shapes (per user)
1. **Figma spec file** — use Figma MCP: `get_code_connect_map`, `get_variable_defs`, `search_design_system`, `get_context_for_code_connect`, `get_screenshot`. Pull component key/node id, variants, properties, variables, nested instances, slot-like areas, code import, prop names/types.
2. **Brand website / public spec URL** — fetch to markdown (the `baoyu-url-to-markdown` skill / web reader), then extract component facts (name, import, props, usage notes) with the source URL as evidence.

## Per component, extract
canonical name candidates, figma key/node id, component set + variants, properties (text/boolean/instance swap/slot), auto-layout/constraints, bound variables, nested instances, allowed slot content, screenshots/thumbnails, code import path, prop names+types, Storybook examples, doc usage notes, real usage examples.

## Normalize
Use `engine.ingest` adapters:
- `ingest_figma(system, figma_key, raw_components, tokens)` → snapshot
- `ingest_docs(system, url, raw_components, tokens)` → snapshot (URL path)
- `ingest_codebase(system, repo_url, raw_components, tokens)` → snapshot
- `normalize.normalize_snapshot(...)` for custom sources

Snapshot schema: `{schemaVersion, system, sourceKind, sourceUrl, components[], tokenRefs[], coverage}`.

## Discipline
- Every fact must carry `evidence` (URL / file / node id). **严禁脑补** — if you can’t cite it, don’t write it.
- Don’t infer semantics (whenToUse, risk). That’s `adk-contract-author`.
- Multiple systems coexist: each under `systems/<sys>/`.
