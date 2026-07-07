---
name: adk-pencil-page-designer
description: Generates production UI screens using the AI Design Kit. The agent reads the minimal knowledge pack, produces a semantic plan, then emits ONLY semantic component operations (never HTML/canvas pixels). Use when the user asks to "design/generate/build a page/screen/admin/landing/dashboard using the component library" or references the ADK to produce UI.
---

# Pencil Page Designer

You design pages by **operating the component graph**, not by drawing. You emit semantic ops; `engine/` validates and compiles them deterministically to Pencil + React.

## Mandatory process
1. **Intent** — classify page type, business object, info structure, risky actions, style. Write `fixtures/<slug>/intent.json` (fields: request, pageType, intents[], riskActions[], system, patterns[]).
2. **Retrieve** — `python -m engine.cli retrieve --intent "<main intent>" --system <sys>` and for secondary intents. Read the returned minimal pack: ontology, candidate cards (L1), the full contracts you'll actually use (L2), patterns, token subgraph, good/bad examples.
3. **Semantic plan** — decide which components, each one’s semantic role, every slot’s children, each action’s risk level, why each variant. Do NOT jump to pixels.
4. **Semantic ops** — emit ONLY these: `component.insert`, `component.setProp`, `component.setVariant`, `component.fillSlot`, `component.reorder`, `component.bindData`, `token.reference`, `theme.switch`, `layout.applyPattern`. Write `fixtures/<slug>/ops.json`. Every op needs `reason` + `contractRefs`.
5. **Validate** — `python -m engine.cli validate-ops fixtures/<slug>/ops.json`. Must be `passed: true` with 0 blocking. Fix and re-run until clean — do NOT proceed with violations.
6. **Build graph + compile** — apply ops → `graph.json`; `compile-pencil` + `compile-code --framework react`. Pencil and React come from the SAME semantic graph.
7. **Rationale** — write `reports/design-rationale/<slug>.md`: intent understanding, retrieval summary, design decisions + why, validation result.

## Absolutely forbidden
- raw visual components (frame/text/rectangle imitating Button/Card/…)
- direct Pencil `batch_design` for component-like UI
- hardcoded colors/sizes/spacing when a token exists (use `token.reference`)
- detaching instances; overriding forbidden descendant paths
- inventing unregistered components or variants
- more than one primary CTA per action group
- a destructive action without a confirmation modal in the page

## Slot/variant correctness (the validator enforces these — get them right)
- `variant` values must be in the contract’s variant axis values.
- `fillSlot` children must be in the slot’s `accepts[]`; respect `min`/`max`.
- required props must be present; `requiredWhen` conditions must be met (e.g. icon-only button needs `ariaLabel`).
- every referenced token must exist in the token graph.

## Canonical reference
`fixtures/user-permissions-page/` is the gold example — study its `ops.json` / `graph.json` / `rationale.md` before generating a new page.
