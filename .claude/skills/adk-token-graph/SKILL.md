---
name: adk-token-graph
description: Builds the token dependency graph (primitive → semantic → component → state) + theme modes + alias bindings. Lets a single semantic-token change propagate to every consuming component. Use when ingesting tokens, checking theme propagation, or answering "if I change the brand color, what changes?".
---

# Token Graph

Author/maintain `systems/<sys>/tokens/token-graph.json` (schema: `schemas/token-graph.schema.json`).

## Four levels
`primitive` (raw value) → `semantic` (alias, e.g. `color.brand.primary`) → `component` (e.g. `button.primary.background`) → `state`.

## Token fields
`{type: color|number|string|boolean, level, value | alias | modes{light,dark}}`.
- `alias` = target token id (no braces).
- `modes` = per-mode value or alias reference string `"{id}"`.
- Convention: change a **semantic** token → aliases propagate to component tokens. Never hardcode component colors.

## Theme behavior
Theme switch changes semantic tokens only; component tokens follow via aliases. `engine` resolves aliases recursively and detects cycles.

## Validate
```
python -m engine.cli validate-tokens --system <sys>
```
Checks: alias cycles, mode completeness (every themed token has all modes). `engine.TokenGraph.affected_by(<semantic_id>)` lists downstream tokens — use it to answer "what changes if I recolor the brand".

## Bindings
Record consumers in `token-graph.json#bindings` (token → `[componentId:visualPath]`) and mirrored in `tokens/token-bindings.json` for human/KC reading.
