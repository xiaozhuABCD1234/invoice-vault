# AGENTS.md

## 前端（frontend/）

任何 UI、样式、组件相关改动，动手前先读 [UI_STYLE.md](./UI_STYLE.md)，并按其中 token、组件规范与禁止清单执行。

硬性要求：

- 技术栈锁定 Vue 3 + TypeScript + Tailwind CSS v4 + Reka UI / shadcn-vue + lucide 图标；不得引入第二套组件库、图标库或 CSS 框架。
- 组件必须复用：同一模式第二次出现即抽组件；禁止复制组件再改、禁止 `Xxx2` / `XxxNew` 近重复组件，差异用 variant/slot 表达；状态徽章、金额、日期、空态、分页只能用统一组件。
- 颜色、间距、圆角、字体只能来自 `UI_STYLE.md` 定义的语义 token；组件中禁止裸 hex、魔法间距、`!important`。
- 主色 `#1E3A5F`，浅色主题唯一；状态色只表达状态，且必须同时有文字或图标。
- 金额以整数分传输，展示统一 `¥1,234.56`、右对齐、tabular-nums；日期 `YYYY-MM-DD`；空值 `—`。
- 每个数据区域必须实现空 / 错 / 加载三态；异步提交必须有 loading 与禁用态。
- 交付前对照 `UI_STYLE.md` 第 15 节检查清单逐项自检。

## 后端（backend/）

- 分层：api → application → domain ← infrastructure；ORM 模型不得直接作为 API 响应，统一用 Pydantic schema。
- 金额一律整数分，禁止浮点。
