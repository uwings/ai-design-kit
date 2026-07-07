# 设计理由 — 企业后台用户权限管理页面

> 同一份语义图（`graph.json`）同时编译为 Pencil（`pencil/generated/user-permissions-page.pen`）与 React（`generated-code/.../UserPermissionsPage.tsx`）。语义图是唯一真相源，二者不互相反推。

## 意图理解
- **页面类型**：企业后台管理页（enterprise admin）
- **业务对象**：用户权限
- **信息结构**：表格 + 筛选 + 角色管理 + 破坏性行操作
- **风险动作**：删除用户、变更角色（不可逆/高影响）
- **意图标签**：`data_management`、`section`、`filtering`、`destructive_confirmation`
- **套用模式**：admin-user-permissions、table-with-filters、destructive-confirmation

## Kit 检索（最小知识包，非全库）
按意图路由召回（`index/intent-index.json`，文件直读 + 意图标签，无向量）：
- `destructive_confirmation` → 召回 `antd.modal` + `antd.button` + destructive-confirmation 模式 + `button.danger.*` / `modal.*` token 子图
- `data_management` → 召回 `antd.table` + table-with-filters 模式
- `section` → 召回 `antd.layout`
- 全局硬规则摘要（primary 每 group 最多 1、破坏性需确认、无硬编码颜色…）

模型只看到当前任务所需的最小知识包，不"记住整个组件库"。

## 设计决策与理由
1. **Layout(hasSider)** — 整页骨架；sider 放侧边导航，content 放主操作区。禁止自由绝对定位。
2. **侧栏 Menu(inline, selectedKeys=['users'])** — 导航用 Menu 而非 Button（纯导航不应用 Button）。选中态走 `menu.item.selected` token。
3. **内容区顺序：Breadcrumb → 筛选栏 → Table** — 遵循 table-with-filters 模式：筛选器在数据之前（反模式 filter_after_data 已规避）。
4. **筛选栏 = Input(search) + Select + Button(primary)** — 搜索/筛选/新增；**primary CTA 全组仅 1 个**（`primary_max_one_per_action_group` 校验通过）。
5. **Table(zebra=striped)** — 斑马纹用 `table.row.bg.subtle` token，非硬编码。columns/dataSource 数据驱动（Table 不作为布局 slot）。
6. **破坏性删除 = Button(danger) + 确认 Modal** — 遵循 destructive-confirmation 模式：`destructive_requires_confirmation` 校验通过（页面存在 confirm Modal）。Modal footer 含取消(default)+确认删除(danger)，max 2、primary 0。
7. **Modal body = Typography(body)** — 明确说明"此操作不可撤销"，动词化按钮文案（确认删除/取消），规避"是/否"含糊反模式。

## 校验结果
- 11 节点，**100% 注册组件**（无 raw imitation）
- `validation-report.json`：**passed=true**，0 blocking / 0 risky
- 所有 token 经 token 图解析（亮/暗模式），无散落 hex
- Pencil 输出：14 个 reusable 组件库 + 页面为 ref 实例 + descendants 覆盖文案 + variables 承载 token

## 验证
```bash
python -m engine.cli validate-ops fixtures/user-permissions-page/ops.json      # passed
python -m engine.cli compile-pencil fixtures/user-permissions-page/graph.json -o pencil/generated/user-permissions-page.pen
python -m engine.cli compile-code  fixtures/user-permissions-page/graph.json --framework react -o generated-code/user-permissions-page/UserPermissionsPage.tsx
```
