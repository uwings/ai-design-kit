---
name: adk-feedback-learner
description: Converts human design feedback, validation failures, or review comments into durable AI Design Kit knowledge — contract/rule/example patches persisted to disk (never just conversation memory). Use when the user says "记住：以后…", "这个设计不对，应该…", or gives any correction the system should learn from.
---

# Feedback Learner

**Never store important corrections only in conversation memory.** Every correction becomes one or more durable artifacts.

## Classify the correction
`semantic | usage | token | visual | composition | code | pencil`.

## Build a correction object (schema: `schemas/correction.schema.json`)
```json
{
  "id": "corr-<slug>-001",
  "type": "usage",
  "summary": "一句话摘要",
  "target": { "kind": "contract|rule|example|antiExample|validator", "system": "ant-design",
              "componentId": "antd.input", "path": "..." },
  "patch": { "propConstraint": {"prop":"placeholder","maxLength":50},
             "hardRule": {"id":"...","kind":"schema","expr":"...","message":"..."} },
  "source": "human review", "sourceEvidence": ["..."], "confidence": 0.9
}
```
`patch` supports: `hardRule`, `softRule`, `compositionRule`, `slotRule`, `exampleGood`, `exampleBad`, `propConstraint` (maxLength/enum/min/max on a prop — enforced by the validator).

## Apply
```
python -m engine.cli apply-correction <correction.json>
```
This: patches the target contract/rule/example, validates the patched contract still conforms, and appends the record to `memory/corrections.jsonl` with `appliedAt`.

## Prove the loop
After applying, re-validate a case that should now be caught (e.g. a fixture exercising the new rule) — it must go from pass → blocking. If it doesn’t, the patch didn’t become enforceable (e.g. a documentary hardRule with no validator fn); elevate it to a `propConstraint` or a registered `fn` rule.

## Output summary
`{correctionId, type, filesChanged, affectedComponents, validatorsToRerun}` → hand to `adk-release-manager` for a patch bump.
