"""源数据接入包。

各适配器把不同源的原始数据归一化为 sources/*.snapshot.json。
v1 的实际抓取（Figma MCP / 品牌 URL）由 adk-source-ingestion skill 驱动 agent 完成，
本包提供归一化与 KC 导出接口。
"""
