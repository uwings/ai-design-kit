---
name: adk-release-manager
description: Versions and releases AI Design Kit artifacts — bump version, run pre-release checks (contracts + token graph + library compile), export the KC ingestion manifest, write changelog. Use when publishing a new kit version after contracts/rules/components change.
---

# Release Manager

```
python -m engine.cli release --bump patch|minor|major [--system ant-design] [--notes "..."]
```

## Version classification
- **patch** — docs / examples / corrections (non-breaking rule tightening counts here if it only catches previously-undesired output)
- **minor** — new component or non-breaking rule/pattern
- **major** — renamed component, removed variant, changed slot contract, changed token semantics

## Pre-release checks (run automatically)
- all contracts schema-valid
- token graph: no alias cycles, modes complete
- Pencil library compiles
- KC export manifest written to `index/_kc/<sys>.manifest.json`

## Release package includes
`kit.json`, contracts, token graph, composition rules, Pencil library, mappings, schemas, index artifacts, examples, changelog.

## Changelog
Written to `reports/release/v<version>.json`. Also bumps `kit.json#version`.

## KC hookup (reserved)
`export-kc` only writes the consumption manifest (contracts + cards + intent-index paths). KC builds the vector copy on its side when hooked up; `retriever.py` then switches to the `kc` backend.
