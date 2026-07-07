---
name: adk-pencil-library-compiler
description: Compiles component contracts + token graph into a Pencil library (.lib.pen) of reusable components — refs, descendant overrides, variables, slots, component-identity metadata. Use when publishing/refreshing a system's Pencil library.
---

# Pencil Library Compiler

Deterministic compile: contracts → `systems/<sys>/pencil/<sys>.lib.pen`.

```
python -m engine.cli compile-library --system <sys> -o systems/<sys>/pencil/<sys>.lib.pen
```

## What the compiler emits (per contract)
- a `reusable:true` component rooted at `id = <componentId>`
- `variables` from the token graph (mode-resolved)
- tokenized root/label fills bound to `$token` variables (when binding has no placeholder)
- a `label` text child (for descendant content overrides)
- `slot` frames preserving `accepts`/`min`/`max`
- root `metadata`: `{componentId, contractVersion, system, allowedDescendantOverrides, tokenBindings, slotContracts, variantAxes}`

## Hard rules
- Registered components become reusable; instances must use `type:"ref"`.
- Editable content uses `descendants`; tokenized values use `variables`.
- **Never compile raw imitation components.**
- v1 emits structurally-correct Pencil IR (proves refs/descendants/variables/slots/metadata + Pencil MCP verification). Full per-component visual fidelity is a follow-up extension via per-contract visual templates.

## Page compilation (separate)
`compile-pencil <graph.json>` emits a page `.pen` whose children are `ref` instances with descendants + token variable fills. The library + page together let Pencil MCP verify identity/tokens/layout.
