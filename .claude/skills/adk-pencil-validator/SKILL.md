---
name: adk-pencil-validator
description: Validates designs against the AI Design Kit — component identity, slots, variants, tokens, layout/a11y. Runs the deterministic validator on ops/graphs and (when Pencil MCP is available) verifies the compiled .pen live. Use to check "is this design compliant?", before delivering a page, or to debug why a generation was blocked.
---

# Pencil / Design Validator

Two layers: **static** (deterministic, always) and **MCP** (live Pencil, when available).

## Static validation (always run)
```
python -m engine.cli validate-ops    <ops.json>        # apply ops → validate graph
python -m engine.cli validate-graph  <graph.json>
python -m engine.cli validate-contracts [glob]         # contracts conform to schema
python -m engine.cli validate-tokens  --system <sys>   # no alias cycles, modes complete
```
The 5 check classes (every `hardRule` is machine-checkable):
- **component** — registered id only (no raw imitation)
- **variant** — values within the contract axis
- **slot** — children ∈ accepts[], count within min/max
- **token** — no hardcoded colors; token refs resolve
- **graph/a11y** — named rules: `primary_max_one_per_action_group`, `destructive_requires_confirmation`, `icon_only_requires_aria_label`

A report is `passed:true` iff 0 blocking. Each blocking issue includes a suggested `fixOp`.

## Live Pencil MCP verification (when available)
After `compile-pencil`, push the `.pen` and check structure/visuals:
- `batch_get` — every UI node is a `ref` to a registered reusable component (no raw imitation)
- `get_variables` — colors/sizes come from token variables, not hex
- `snapshot_layout` — no overlap/overflow; responsive sane
- `get_screenshot` — visual sanity (hierarchy, density, contrast)

Write `reports/visual-review/<slug>.md` and `reports/validation/<slug>.json`. If issues found, propose minimal repair ops, re-validate, recompile.

## Violation library
`fixtures/violations/*.json` — each file demonstrates one violation class; run `validate-ops` on them to see exact messages + fixOps. Use as a reference when diagnosing.
