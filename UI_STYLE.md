# UI 与前端设计约束（v1）

> 状态：生效。适用于 `frontend/` 下所有页面、组件与样式。
> 与本文冲突的实现一律按缺陷处理；确需例外时在文末「例外记录」登记，不允许静默偏离。

## 1. 产品定位与设计原则

这是内部财务/票据工作台，不是营销官网。使用者是管理员和提交票据的同事，日常高频操作，屏幕以 1280–1920 桌面为主。

四条原则，按优先级排序：

1. **信息优先**：表格、金额、状态一眼可读；装饰不得抢注意力。
2. **克制**：一个主色 + 一组语义状态色；无渐变、无玻璃拟态、无大插画、无发光效果。
3. **一致**：同一种控件在全站只有一种样子；字号、间距、圆角、颜色全部来自 token。
4. **可信**：金额、日期、文件名、权限相关操作必须准确；破坏性操作必须二次确认。

设计关键词：**克制的数据工作台**（restrained data workspace）。参考气质是财务后台、审计工具，而不是 SaaS 落地页。

## 2. 技术栈（锁定）

| 范畴 | 选型 | 约束 |
|---|---|---|
| 框架 | Vue 3.5 + TypeScript（strict）+ Vite | 只用 `<script setup lang="ts">` 与 Composition API |
| 样式 | Tailwind CSS v4（CSS-first，`@theme` 定义 token） | 不生成 `tailwind.config.js`；不用 CSS-in-JS |
| 组件 | Reka UI + shadcn-vue（复制进仓库，代码归项目所有） | 只此一套；组件放 `src/components/ui` |
| 图标 | `lucide-vue-next` | 统一 16 / 18 / 20px，stroke 1.75；禁止 emoji 当图标 |
| 路由 | Vue Router 4 | 路由级权限用 `meta.requiresAuth` / `meta.roles` |
| 全局状态 | Pinia | 只放登录态、当前用户、UI 偏好；服务端数据用组合式函数 |
| 图表 | ECharts 5 + vue-echarts | 按需引入，禁止 3D 图表 |
| 日期 | dayjs | 不引第二个日期库 |
| 提示 | vue-sonner | 统一 toast，不自制通知条 |
| 测试 | Vitest + Playwright | 金额/格式化必须有单测，核心流程有 e2e |

**禁止引入**：Element Plus、Ant Design Vue、Naive UI、Vuetify、Arco Design、Vant、Bootstrap；任何第二套组件库或图标库；jQuery；外部字体/CDN 资源；Options API；`any`（除非有注释说明的第三方边界）。

## 3. 色彩

首版**只交付浅色主题**。暗色主题本期不做，但 token 需按语义命名，便于后续成对扩展。所有颜色必须通过 token 使用，组件与页面中不得出现裸 hex / rgb。

| 语义 | Token | 值 | 用途 |
|---|---|---|---|
| 画布 | `--color-canvas` | `#F6F7F9` | 页面底色 |
| 表面 | `--color-surface` | `#FFFFFF` | 卡片、表格、弹层 |
| 次级表面 | `--color-surface-muted` | `#F1F3F5` | 表头、禁用底、hover 底 |
| 边框 | `--color-border` | `#E3E6EA` | 分割线、输入框 |
| 强边框 | `--color-border-strong` | `#CBD2D9` | 强调分隔、可交互边框 |
| 正文 | `--color-text` | `#0F172A` | 主文本 |
| 次要文本 | `--color-text-secondary` | `#475569` | 说明、表头 |
| 弱文本 | `--color-text-muted` | `#64748B` | 占位、辅助信息 |
| 主色 | `--color-primary` | `#1E3A5F` | 主按钮、当前导航、链接、焦点 |
| 主色 hover | `--color-primary-hover` | `#162C47` | 主按钮 hover/active |
| 主色浅底 | `--color-primary-soft` | `#E9EFF6` | 选中行、当前导航底 |
| 焦点环 | `--color-ring` | `rgba(30, 58, 95, 0.35)` | focus-visible 外环 |
| 成功 | `--color-success` | `#047857` | 已付款、已通过 |
| 成功浅底 | `--color-success-soft` | `#E7F5EF` | 成功 badge 底 |
| 警告 | `--color-warning` | `#B45309` | 待审核、部分付款、差异 |
| 警告浅底 | `--color-warning-soft` | `#FDF3E3` | 警告 badge 底 |
| 危险 | `--color-danger` | `#B91C1C` | 删除、驳回、重复、失败 |
| 危险浅底 | `--color-danger-soft` | `#FDECEC` | 危险 badge 底 |
| 信息 | `--color-info` | `#1D4ED8` | 识别中、进行中、提示链接 |
| 信息浅底 | `--color-info-soft` | `#E8EFFD` | 信息 badge 底 |

使用规则：

- 主色只用于**主操作、当前导航、焦点、可点击链接**；不要拿来给大面积背景或标题上色。
- 状态色只表达状态，不用于装饰；且必须同时有文字或图标，不能只靠颜色区分。
- 正文与背景对比度 ≥ 4.5:1；大字与图形 ≥ 3:1。
- 金额不用绿色/红色区分正负（本系统无收入概念）；风险用图标 + 文案。

### 状态语义映射（固定）

| 业务状态 | 展示 | 颜色 |
|---|---|---|
| 待审核 / review_pending | 待审核 | warning |
| 识别中 / running | 识别中 | info |
| 排队 / queued | 排队中 | muted |
| 已生效 / active | 已生效 | success |
| 已驳回 / rejected | 已驳回 | danger |
| 失败 / failed | 失败 | danger |
| 已作废 / void | 已作废 | muted |
| 重复 / duplicate | 重复 | danger |
| 未付款 / unpaid | 未付款 | warning |
| 部分付款 / partial | 部分付款 | info |
| 已付款 / paid | 已付款 | success |
| 未分配 / unallocated | 未分配 | warning |
| 已全额分配 / fully_allocated | 已核销 | success |

## 4. 字体与排版

字体只用系统字体栈，不加载 Web Font（单机/内网部署，避免外部依赖）：

```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
  "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
--font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

金额、数量、日期等数字列统一 `font-variant-numeric: tabular-nums`，等宽数字防跳动。

| 场景 | 字号/行高 | 字重 |
|---|---|---|
| 辅助说明、时间戳 | 12 / 16 | 400 |
| 表格正文、表头、meta | 13 / 20 | 400（表头 500） |
| 正文默认、表单标签、按钮 | 14 / 22 | 400 / 500 |
| 移动端正文、表单输入 | 16 / 24 | 400 |
| 区块标题 | 20 / 28 | 600 |
| 页面标题 | 24 / 32 | 600 |
| KPI 数字 | 30 / 38 | 600 |

规则：

- 正文不小于 12px；移动端输入框 16px 起，避免 iOS 自动缩放。
- 中文正文不加 `letter-spacing`；标题可 `-0.01em`。
- 长文本优先换行；必须截断时用省略号 + tooltip 提供全文。
- 发票号码、文件 hash 用等宽字体，不换行，提供复制按钮。

## 5. 间距、圆角、阴影、边框

- 间距基数 4px，只用：`4, 8, 12, 16, 24, 32, 40, 48`（密集表格内部可用 2px 半个单位，但不得出现 5/7/13 这类随手值）。
- 圆角：标签 4px、控件 6px、卡片 8px、弹窗 12px、胶囊 999px。
- 默认不用卡片阴影，用 1px 边框区分层级；仅浮层使用阴影：
  - 下拉/气泡：`0 4px 12px rgba(15, 23, 42, 0.08)`
  - 弹窗：`0 16px 48px rgba(15, 23, 42, 0.16)`
- 全部边框 1px；不做 2px 粗边框（焦点环除外）。
- 图标统一 lucide，尺寸 16（行内）/ 18（按钮）/ 20（导航），stroke 1.75。

## 6. 布局与页面骨架

### AppShell

```
┌────────────┬──────────────────────────────────────────┐
│ Sidebar    │ Topbar 56px（面包屑 / 用户 / 登出）        │
│ 232px      ├──────────────────────────────────────────┤
│ (收起 64)  │ Content：padding 24–32px                  │
│            │  PageHeader → FilterBar → Card/Table ...  │
└────────────┴──────────────────────────────────────────┘
```

固定尺寸：

- 侧栏展开 232px、收起 64px；顶栏 56px；内容内边距 24px（≥1440px 时 32px）。
- 内容最大宽度：表格页不限宽（铺满）；表单页 720px；阅读型内容 760px。
- 断点：`sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`。
- ≥1024px 用固定侧栏；<1024px 侧栏改为抽屉，顶栏出现菜单按钮。
- 页面不允许出现横向滚动；宽表格在卡片内部横向滚动，首列（发票号/名称）可 sticky。

### 页面模板

1. **列表页**（发票、付款、用户、审计）：页面标题 + 右侧主操作 → 筛选栏（高 36px 控件，间距 12px，可折叠高级筛选）→ 表格卡片（含批量操作条）→ 分页。筛选条件同步到 URL query。
2. **详情/审核页**：顶部返回 + 标题 + 状态 + 操作；主体左右两栏（左 1.2fr 文件预览，右 1fr 字段表单），预览区 sticky；字段分组用区块标题，不用满地卡片。审核页必须常驻展示「字段置信度 / 校验错误 / 与上次结果 diff」。
3. **仪表盘**：一行 2–4 个 KPI 卡（边框卡，无阴影）→ 两列图表 → 缺口/异常表格。KPI 数字用 tabular-nums，涨跌用箭头 + 文案，不用红绿单独表达。
4. **登录页**：居中 400px 卡片，品牌名 + 表单；不做左右分屏营销图，不放插画。
5. **空/错/加载**：每个数据区域都必须实现三态；空状态含一句说明 + 一个主操作；错误含原因 + 重试。

## 7. 组件规范

| 组件 | 规范 |
|---|---|
| Button | 高度 sm 32 / md 36 / lg 40；变体 primary（实心主色）、secondary（描边）、ghost（无底）、danger（危险）；每屏主按钮最多 1 个；加载中禁用并显示 spinner |
| Input / Select | 高 36（移动端 44），边框 1px，focus 时边框主色 + 2px 焦点环；标签常驻上方，禁止只用 placeholder 当标签；错误信息在字段下方，红色 + 图标 |
| Table | 表头高 40、行高 44（紧凑 40）；表头 sticky；不斑马纹；hover 行 `surface-muted`，选中行 `primary-soft`；数字右对齐；操作列固定右侧；排序用 `aria-sort` |
| Badge | 圆角 4，浅底 + 深色文字 + 状态点；文案固定，不用纯色块 |
| Dialog | Reka UI Dialog；宽度 480 / 640 / 800 三档；标题 16/600；底部按钮右对齐，取消在左；危险操作按钮用 danger，并写清后果 |
| Toast | vue-sonner，右上角，4s 自动关闭，`aria-live="polite"`；成功/失败都要有 |
| 上传 | 虚线拖拽区 + 点击选择；展示文件名、大小、进度、失败原因；同文件重复上传提示已存在，不静默覆盖 |
| 分页 | 默认 20，可选 50 / 100；显示总数；键盘可达 |
| Tabs | 只用于同一实体的并列视图（如发票详情/明细/付款），不作为主导航 |
| Tooltip | 仅补充信息，不承载唯一关键信息；键盘可触发 |

金额与状态在表格中必须右对齐/居中固定，不允许因内容长度改变列宽节奏。

### 7.1 组件复用规则（强制）

组件分三层，依赖方向只能向下：

```
views/        页面编排：只做数据获取、布局组合、路由参数
  ↓
components/<domain>/   领域组件：发票表格、状态徽章、金额、文件预览
  ↓
components/ui/        基础组件：Button、Input、Dialog、Table 原语
```

1. **第二次出现就抽组件**：同一种视觉或交互模式在第二个地方出现时，必须抽成组件，不允许复制粘贴。不是等到第三次。
2. **页面里禁止重复手写这些片段**：状态徽章、金额、日期、空状态、错误状态、加载骨架、表格工具栏、分页、确认弹窗、文件上传区。全部使用统一组件。
3. **不做近重复组件**：禁止 `InvoiceTable2`、`PaymentTableNew`、`StatusBadgeSmall` 这类分叉；差异用 `variant` / `size` / `tone` 等联合类型 props 或 slot 表达。
4. **变体优先于新组件**：同一组件第 2 种外观先加 variant；只有结构、交互、可访问性语义不同才新建组件。
5. **禁止复制后改**：复制已有组件再改是本项目明确禁止的做法；需要不同行为时改原组件 API 并回归所有调用点。
6. **ui/ 组件保持纯展示**：不发请求、不读路由、不依赖业务枚举、不写业务文案；只接收 props、抛事件，保证可单测、可复用。
7. **领域组件承载业务语义**：状态到文案/颜色的映射、金额格式化、发票号复制等只在领域组件或 `lib/` 中实现一次。
8. **页面只做编排**：views 负责取数与组合，不重新实现表格排序、分页、空态等逻辑；单页超过约 200 行时应拆分。
9. **props 向下、事件向上**：禁止子组件修改 props；双向绑定统一用 `defineModel`。
10. **slot 优于布尔爆炸**：布尔 props 超过 5 个或出现 `showXxx` 组合时，改用 slot 或拆组件。
11. **新增组件必须有真实调用点**：不写"以后可能用得上"的投机组件；新组件需有类型化 props、emits，并至少被一个页面使用。
12. **复用不等于过度抽象**：在只有一处使用、且变化方向尚不明确时，不要提前造通用组件；第二次真实出现时再抽象，并同时迁移第一处。

统一的复用入口（必须存在且唯一）：

- `StatusBadge`：业务状态 → 文案 + 颜色 + 状态点。
- `MoneyText`：分 → `¥1,234.56`，支持右对齐、负数、合计加粗。
- `DateText`：日期/时间统一格式与空值 `—`。
- `DataTable`：表头、排序、空/错/加载、分页、行选择。
- `EmptyState` / `ErrorState` / `TableSkeleton`：三态统一。
- `ConfirmDialog`：危险操作确认与后果文案。
- `FilePreview`：PDF/图片在线预览与版本切换。

## 8. 金额、日期与编号格式

- 后端传输一律整数分（`*_cents`）；前端只在展示层格式化，禁止浮点累加。
- 金额展示 `¥1,234.56`，负数 `-¥1,234.56`；合计行加粗；表格右对齐；不显示多余小数位。
- 日期 `YYYY-MM-DD`，时间 `YYYY-MM-DD HH:mm`；不用「3 天前」这类相对时间。
- 百分比保留 1 位小数；文件大小保留 1 位（KB/MB）。
- 空值统一显示 `—`，不要混用「无」「N/A」「-」。
- 发票号码等宽、不换行、可一键复制。

## 9. 文案

- 中文、短句、动词开头。按钮写「保存审核结果」「导出 xlsx」，不写「确定」「提交」。
- 错误信息 = 发生了什么 + 怎么处理；不向普通用户暴露堆栈、SQL、trace_id（可折叠进「详情」）。
- 空状态 = 为什么空 + 下一步做什么。
- 破坏性操作写清后果与范围，例如「将删除该发票及其 3 个文件版本，不可恢复」。
- 统一术语：发票、付款记录、分配、审核、对账、缺口；不要中英混用（金额单位除外）。

## 10. 交互与动效

- 微交互 150–200ms，`ease-out`；只动 `transform` / `opacity`，不动宽高与 top/left。
- `prefers-reduced-motion: reduce` 时关闭非必要动画。
- 请求超过 300ms 显示骨架屏或行内 loading；超过 1s 的批量操作显示进度。
- 提交中按钮禁用并保留宽度，避免布局跳动。
- 焦点必须可见：2px 焦点环 + 2px offset；所有操作可键盘完成。
- hover 只能作为增强，不能是唯一触发方式。

## 11. 可访问性底线

- 文本对比 ≥ 4.5:1，大字/图形 ≥ 3:1。
- 表单控件必须有 `label`（`for`/`id` 关联），错误用 `aria-live`。
- 图标按钮必须有 `aria-label`。
- 表格使用语义化 `table/thead/th[scope]`，排序状态用 `aria-sort`。
- 移动端点击区域 ≥ 44×44px；桌面 ≥ 32×32px。
- 弹窗焦点陷阱 + Esc 关闭；关闭后焦点回到触发元素。
- 颜色不是唯一信息载体。

## 12. 工程结构约束

```
frontend/src/
  api/            # 请求模块 + types.ts（与后端 schema 对齐）
  components/
    ui/           # shadcn-vue 复制进来的基础组件
    invoice/      # 领域组件（InvoiceTable、StatusBadge...）
    layout/       # AppShell、Sidebar、PageHeader
  composables/    # useInvoices、useUpload...
  lib/            # cn、money、date、format
  router/
  stores/         # auth、ui（仅全局状态）
  views/          # 页面，按领域分目录
  styles/         # theme.css（@theme token）、base.css
```

- 组件文件名 PascalCase，组合式函数 `useXxx`，页面放 `views/<domain>/`。
- 所有请求走 `src/api`；组件内禁止直接 `fetch`，禁止在页面里拼 URL。
- 金额格式化只在 `src/lib/money.ts`；日期只在 `src/lib/date.ts`。
- class 合并统一用 `cn()`（clsx + tailwind-merge）。
- Tailwind 只使用 token 对应的语义类（如 `bg-surface`、`text-muted`、`border-border`）；禁止 `bg-[#...]`、`w-[327px]` 这类任意值（栅格/图表尺寸除外）。
- 禁止 `!important`、全局标签选择器覆盖、深层 `:deep()` 改第三方组件（确需覆盖时封装在自己的 ui 组件里）。
- 允许 `<style scoped>` 仅用于 ECharts 容器、打印样式等 Tailwind 不适合的场景。
- TypeScript 不使用 `any`；API 类型集中在 `src/api/types.ts`，字段名与后端 `*_cents` 一致。
- 路由懒加载；首屏外的图表、编辑器按需 import。
- 环境变量只通过 `import.meta.env.VITE_*` 读取，不硬编码后端地址。

## 13. 明确禁止

- 引入第二套 UI 组件库、图标库或 CSS 框架。
- 渐变、玻璃拟态、霓虹、发光、3D 卡片、大插画、装饰性背景图。
- emoji 作为图标或状态标记。
- 组件里写死颜色（hex/rgb/hsl）或魔法间距。
- 只用颜色表达状态；只用 placeholder 当标签。
- 卡片套卡片、每块内容都包一层阴影卡片。
- 大面积主色背景、彩色标题。
- 桌面端直接套移动端底部导航；或反过来把后台做成手机 App 样式。
- 无确认的删除/驳回/覆盖；无 loading 的异步提交。
- 表格里金额左对齐、日期格式混用、空值写法混用。
- 未处理的空/错/加载状态。
- 引入外部 CDN 字体或图标。

## 14. 首版页面清单

| 优先级 | 页面 | 路由 |
|---|---|---|
| M0 | 登录 | `/login` |
| M0 | 上传/识别任务 | `/uploads` |
| M1 | 审核队列 | `/review` |
| M1 | 审核详情（预览 + 表单 + diff） | `/review/:jobId` |
| M2 | 发票列表 / 详情 | `/invoices`、`/invoices/:id` |
| M2 | 付款列表 / 详情 | `/payments`、`/payments/:id` |
| M2 | 对账缺口 | `/reconciliation` |
| M3 | 报表模板与导出 | `/exports` |
| M3 | 仪表盘 | `/dashboard` |
| M3 | 用户管理 / 审计日志 | `/admin/users`、`/admin/audit` |

## 15. 交付前检查清单

- [ ] 只用了锁定的技术栈，没有第二套组件库。
- [ ] 重复出现的状态徽章/金额/日期/空态/分页已复用统一组件，页面里没有复制粘贴的片段。
- [ ] 没有新增近重复组件；差异通过 variant / slot 表达。
- [ ] 没有裸 hex、魔法间距、`!important`。
- [ ] 主按钮每屏 ≤ 1 个；危险操作用 danger 且有确认。
- [ ] 金额右对齐、tabular-nums、`¥1,234.56` 格式；空值统一 `—`。
- [ ] 列表/详情均有空、错、加载三态。
- [ ] 键盘可完成主流程；焦点可见；图标按钮有 aria-label。
- [ ] 375 / 768 / 1024 / 1440 宽度无页面横向滚动。
- [ ] 中文文案无中英混排、无「确定」这类含糊按钮。
- [ ] 移动端输入 16px、点击区域 ≥ 44px。
- [ ] `prefers-reduced-motion` 下动画已降级。

## 16. 例外记录

| 日期 | 页面/组件 | 例外内容 | 原因 | 批准人 |
|---|---|---|---|---|
| — | — | — | — | — |
