# Design Systems（多体系共存）

ADK 是**编译器**，不是存储仓库。`systems/<sys>/` 下的契约都是**编译产物**——由
Source Ingestion → Contract Author 链路从源（URL/Figma/代码/Storybook）编译产出，
经引擎 schema 校验落盘。系统不存任何预置/手写契约。

## 加一个体系（按需编译）
```bash
python -m engine.cli ingest-snapshot --system <新体系> --from url|figma|code --raw <raw.json> --url <url>
python -m engine.cli compile-context  --system <新体系> --snapshot systems/<新体系>/sources/*.snapshot.json
# AI 据上下文编译 → write-contract / write-tokens / write-system（引擎校验落盘）
python -m engine.cli index
```
不指定源时系统里什么都没有；指定一个源就编译出一个体系。

## 现有体系
- **ant-design/** — 14 契约。首版从 AntD 公开文档编译产出；作为**参照/fixture**保留（校验编译链路、跑规范 demo）。
- **shadcn/** — 3 契约。**实跑证明**：从 https://ui.shadcn.com URL 经完整编译链路产出（非手写）。见 `shadcn/README.md`。

## 每个体系的产物
```
systems/<sys>/
  system.json                 体系元信息 + 源出处 + kcHookup
  sources/*.snapshot.json     Source Ingestion 产物（事实，严禁脑补）
  components/*.contract.json  Contract Author 编译产物（schema 校验过）
  tokens/token-graph.json     token 图编译产物
  compositions/  mappings/  ontology/  pencil/  examples/
```

## 单一真相源
- 契约的 `intents` 字段直接喂检索意图路由（`index/intent-index.json` 由 indexer 从契约编译）。
- 契约的 `sourceEvidence` 指回 snapshot 证据 URL——可审计、可复跑。
