---
name: adk-composition-grammar
description: Builds composition grammar — page patterns, slot rules, anti-patterns — so AI gets page-level structure right, not just component-level correctness. Use when authoring page patterns for a system or judging "is this composition reasonable?".
---

# Composition Grammar

Author `systems/<sys>/compositions/*.pattern.json` (schema: `composition-pattern.schema.json`) + cross-system page archetypes in `shared/patterns/page-patterns.json`.

## Each pattern defines
`id, intent[], requiredComponents[], optionalComponents[], order[], slots{accepts,min,max,rules}, responsive{desktop/tablet/mobile}, antiPatterns[{name,why,fix}], examples{good,bad}`.

## Canonical patterns (Ant Design)
- `admin-user-permissions` — layout+menu+breadcrumb+filterBar+table+detail+confirm modal
- `table-with-filters` — filterBar above table; filters grouped before data; empty state
- `destructive-confirmation` — danger button → confirm modal; footer max 2; danger = confirm; verb labels

## Anti-patterns live in `shared/rules/anti-patterns.json`
`raw_imitation_component`, `hardcoded_color`, `alert_for_empty_state`, `primary_cta_overuse`, `destructive_without_confirmation`, `detached_instance`, `filter_after_data`…

Use these when reviewing a generated page: does it match a good pattern and avoid the anti-patterns?
