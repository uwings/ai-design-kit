---
name: adk-contract-author
description: Authors machine-readable component contracts (one JSON per component) from source snapshots + semantics + token graph + composition grammar. Each contract is the component's AI-operable "design API". Use when ingesting new components or refining existing contracts.
---

# Contract Author

Write one `systems/<sys>/components/<id>.contract.json` per component, conforming to `schemas/component-contract.schema.json`.

## Every contract must include
`id, version, system, displayName, sourceRefs[], semanticRole, intents[], meaning{definition, useWhen, doNotUseWhen}, variants{axis:{values, default, semantics}}, props{name:{type, required?, requiredWhen?, maxLength?, enum?, accepts?}}, slots{name:{accepts, min, max, rules}}, states[], tokenBindings{visualPath: tokenExpr}, compositionRules[{id,severity,condition,assert}], pencil{componentRefPattern, allowedDescendantOverrides, forbiddenOverrides}, code{framework, import, component, propMap}, examples{good, bad}, hardRules[{id, kind, expr}], softRules[], sourceEvidence[], confidence, needsReview`.

## Rules of thumb
- **meaning** describes design meaning, not visuals (❌"圆角矩形带文字" ✅"在决策上下文触发动作").
- `intents` come from `shared/ontology/intent-taxonomy.json` — drives retrieval routing.
- `tokenBindings` values must be real token ids (no `{placeholder}`) from `token-graph.json`.
- `slots.accepts` must be registered component ids in this system.
- **hardRules** must be machine-checkable. Use `kind:"fn"` + `expr:"fn:<name>"` only for registered validators (`primary_max_one_per_action_group`, `destructive_requires_confirmation`, `icon_only_requires_aria_label`). Others use schema/graph/token/slot with a concrete expr.
- `code.propMap` maps contract prop → real framework prop (must match `mappings/kit-to-react.json`).
- Low-confidence claims → `needsReview:true`; never make a low-confidence claim a hard rule.
- Don’t write long prose where a structured field expresses it.

## Validate as you go
```
python -m engine.cli validate-contracts systems/<sys>/components/<id>.contract.json
```
Then `python -m engine.cli index` to regenerate retrieval cards + intent-index.

## Anti-example to avoid
A contract that only lists `props` with no semantics, no token bindings, no hard rules, no good/bad examples is not a contract — it’s a props table. Upgrade it.
