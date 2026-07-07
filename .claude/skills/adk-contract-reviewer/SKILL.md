---
name: adk-contract-reviewer
description: Reviews AI-generated component contracts for contradictions, unsupported assumptions, and gaps — semantic role vs usage, variant distinctness, prop/token/slot completeness, machine-checkability of hardRules. Reports issues; does not modify unless asked. Use after contract-authoring batches or when quality is uncertain.
---

# Contract Reviewer

Run after `adk-contract-author` batches. Don’t trust AI-authored contracts blindly — review them.

## Checklist (per contract)
- Does `semanticRole` match actual usage? Are `intents` correct?
- Are variants **semantically distinct** (not visual micro-adjustments that should merge)?
- Are props mapped to Figma/Pencil/code consistently (propMap keys = declared prop names)?
- Are token bindings complete and pointing to real tokens?
- Are forbidden overrides specified (token-bound visual paths)?
- Are slots strict enough (accepts/min/max)?
- Are `hardRules` actually machine-checkable? `kind:"fn"` must reference a registered validator.
- Are `examples.good`/`bad` present and meaningful?
- Are low-confidence claims marked `needsReview:true`?

## Classify issues
`blocking` / `risky` / `improvement` / `question`. Write `reports/contract-review/<sys>.md` + `.json`.

## Automated signals
```
python -m engine.cli validate-contracts systems/<sys>/components/*.json   # schema
python -m engine.cli validate-tokens   --system <sys>                     # token integrity
```
Plus the semantic cross-ref check (token ids exist, slot accepts are registered, intents are in taxonomy, fn rules resolve) — run via the engine in review mode.

Do not modify contracts unless explicitly asked; report and let a human (or `adk-contract-author`) apply.
