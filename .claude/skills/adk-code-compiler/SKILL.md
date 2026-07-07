---
name: adk-code-compiler
description: Compiles semantic design graphs into production code (React/HTML) using real component APIs and approved token variables. The source is the semantic graph, NOT the Pencil .pen — so code and design share one truth and never lose semantics. Use after a page validates, to deliver runnable code.
---

# Code Compiler

Deterministic compile from the **semantic graph** (single source of truth):

```
python -m engine.cli compile-code <graph.json> --framework react -o <dir>
python -m engine.cli compile-code <graph.json> --framework html  -o <dir>
```

## Mapping (from each contract’s `code` section + `mappings/kit-to-react.json`)
- component id → real `import { X } from "antd"`
- variant → code prop (e.g. button `intent` → `type`)
- props → code props via `propMap`; the prop mapped to `children` becomes text children
- slots/children → JSX composition
- tokens → CSS variables (`:root { --token: value }`)

## Why not from .pen
Pencil is a compile target, not the source. Compiling code from .pen reverses visual nodes into code and loses semantics (which component, which variant, which token). Both Pencil and code come from the same `semantic-graph`.

## Validate the output
- all components use real imports (no one-off CSS imitating a system component)
- props satisfy the component API (`propMap`)
- colors/sizes reference CSS variables from tokens, no raw hex
