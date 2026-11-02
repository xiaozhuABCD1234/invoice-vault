# 前端（发票管理系统）

内部财务票据工作台前端。技术栈与 UI 规范以仓库根的 [UI_STYLE.md](../UI_STYLE.md) 为准，接口以 [docs/API_CONTRACT.md](../docs/API_CONTRACT.md) 为准。

## 命令

```bash
pnpm install
pnpm dev        # http://127.0.0.1:5173，/api 代理到 http://127.0.0.1:8000
pnpm test       # Vitest
pnpm typecheck  # vue-tsc -b
pnpm build      # vue-tsc -b && vite build
pnpm preview
```

## 目录

```
src/
  api/          # fetch 客户端、契约类型、按领域的请求函数
  components/
    ui/         # 基础组件（Button、Input、Dialog、Select、Pagination…）
    common/     # 领域通用组件（DataTable、StatusBadge、MoneyText、FilePreview…）
    layout/     # AppShell、Sidebar、Topbar
  composables/  # 页面级组合式函数（后续页面补充）
  lib/          # cn、money、date、format、status
  router/       # 路由与守卫
  stores/       # auth、ui
  styles/       # theme.css（@theme token）、base.css
  views/        # 页面，按领域分目录
```

## 硬约束

- 颜色、字号、圆角、阴影、布局尺寸只能使用 `src/styles/theme.css` 中的语义 token；组件里不写裸 hex / rgb、任意值、`!important`。
- 金额只在 `src/lib/money.ts` 格式化；日期只在 `src/lib/date.ts`。金额传输与存储一律整数分。
- 请求只能经 `src/api`；组件/页面内禁止直接 `fetch`，禁止拼接后端地址。
- 业务字段统一 `snake_case`（`invoice_number`、`total_cents`、`page_size`、`created_at`），类型见 `src/api/types.ts`。
- 不使用 `any`（确需第三方边界时加注释）；组件使用 `<script setup lang="ts">`。
- 空值统一 `—`；每个数据区域必须有加载 / 空 / 错三态。

## API 客户端

```ts
import { ApiError, getBlob, request } from '@/api/client'
import { listInvoices } from '@/api/invoices'
```

- `request<T>(path, { method, query, body, signal })`：JSON 请求；query 自动跳过空值。
- `getBlob(path, { query, signal })`：带 Authorization 的二进制请求。文档预览 / 下载与 xlsx 导出必须使用它或对应 api 函数，**不要**把带鉴权的 URL 直接放进 iframe/img。
- access token 只存内存；`setAccessToken()` 由 auth store 调用。401 时客户端自动只重试一次 refresh。
- 错误统一为 `ApiError`，含 `status / code / message / details / traceId`。

`getDocumentPreview(documentId, version, signal)` 支持 `version='latest'` 或数字版本 id；`downloadDocument`、`downloadExport` 返回 `Blob`。

## 认证与路由

- `useAuthStore()`：`user / accessToken / initialized / isAuthenticated / isAdmin`；
  `login / logout / restore / refresh / fetchMe`。应用首次导航由路由守卫调用 `restore()`。
- 路由 meta：`requiresAuth`、`roles`、`title`；父路由 `AppShell` 统一提供外壳。
- 登录页已完整实现；其余页面为占位文件，后续按领域替换，不要修改路由契约。
- 路由名：`login / dashboard / uploads / review / review-detail / invoices / invoice-detail /
  payments / payment-detail / reconciliation / exports / admin-users / admin-audit / not-found`。

## 统一组件

### DataTable

```ts
import DataTable from '@/components/common/DataTable.vue'
import type { DataTableColumn, DataTableSort } from '@/components/common/data-table'

const columns: DataTableColumn[] = [
  { key: 'invoice_number', label: '发票号码', width: 160, sortable: true, nowrap: true, fixed: 'left' },
  { key: 'issue_date', label: '开票日期', width: 120, nowrap: true },
  { key: 'total_cents', label: '金额', width: 130, align: 'right', sortable: true },
  { key: 'status', label: '状态', width: 110, align: 'center' },
]
const sort = ref<DataTableSort | null>(null)
```

```vue
<DataTable
  v-model:sort="sort"
  :rows="rows"
  :columns="columns"
  row-key="id"
  :loading="loading"
  :error="error"
  :selected-key="selectedId"
  empty="暂无发票"
  empty-description="上传发票后会显示在这里。"
  @retry="load"
>
  <template #cell-total_cents="{ value }">
    <MoneyText :cents="Number(value)" />
  </template>
  <template #cell-status="{ value }">
    <StatusBadge kind="invoice_status" :status="String(value)" />
  </template>
  <template #cell-invoice_number="{ value }">
    <span class="whitespace-nowrap font-mono">{{ value }}</span>
  </template>
  <template #empty-action>
    <Button>上传发票</Button>
  </template>
</DataTable>
```

- 排序只 emit `update:sort`，不自行排序；页面根据 sort 重新取数。
- 可用 `#cell-<key>` 或统一 `#cell` 自定义单元格；`#empty-action` 放入空状态主操作。
- 表格容器内部横向滚动；`fixed` 列可固定首列 / 操作列。
- 分页使用独立的 `Pagination` 组件，页面负责取数与状态。

### 其他领域组件

| 组件 | API |
|---|---|
| `StatusBadge` | `kind`（invoice_status / payment_status / job_status / export_status / allocation_status）+ `status`；或 `tone` + `label` |
| `MoneyText` | `cents`、`strong`、`align='right'`；null/undefined → `—` |
| `DateText` | `value`、`mode='date' \| 'datetime'`、`align` |
| `EmptyState` | `title`、`description`、`icon`、`#action` |
| `ErrorState` | `title`、`message`、`retryLabel`，emit `retry` |
| `TableSkeleton` | `rows`、`columns` |
| `ConfirmDialog` | `v-model:open`、`title`、`consequence`、`confirmLabel`、`loading`，emit `confirm` |
| `FilePreview` | `documentId`、`version`（latest/版本 id）、`height`；内部用 blob 请求，自动 revoke |
| `PageHeader` | `title`、`description`、`backTo`、`breadcrumbs`、`#meta`、`#actions` |

### 基础组件

- `Button`：`variant`（primary/secondary/ghost/danger）、`size`（sm/md/lg）、`loading`、`disabled`；`#icon` 前缀图标。
- `Input` / `Textarea`：`v-model`、`invalid`、`disabled`；输入字号 16px。
- `FormField`：`id`、`label`、`required`、`hint`、`error`；默认 slot 透传 `{ id, invalid, describedBy }`，用于绑定 `aria-describedby`。
- `Select`：`v-model`、`options: { value, label, disabled? }[]`、`placeholder`、`invalid`、`ariaLabel`。
- `Dialog`：`v-model:open`、`title`、`description`、`width`（sm/md/lg）、`#footer`、`#trigger`。
- `Pagination`：`v-model:page`、`v-model:page-size`、`total`、`pageSizes`。
- `Tabs`：`v-model` + `items: { value, label }[]`，具名 slot 对应每个 value。
- `Tooltip`：`content`、`side`、`disabled`。
- `Badge`：`tone`、`dot`、`icon`；`Skeleton` 通过 class 传尺寸。

## 设计 token（摘要）

`bg-canvas / bg-surface / bg-surface-muted / border-border / border-border-strong`；
`text-text / text-text-secondary / text-text-muted`；
`bg-primary / bg-primary-hover / bg-primary-soft / text-primary`；
状态色 `success / warning / danger / info` 及 `-soft` 浅底；
`text-meta / text-table / text-body / text-heading / text-input / text-section / text-page / text-kpi`；
`rounded-tag / rounded-control / rounded-card / rounded-dialog / rounded-pill`；
`shadow-float / shadow-dialog`；布局 `w-sidebar / w-sidebar-collapsed / h-topbar`；`wide:` 断点 1440px。

## 测试

`src/lib/__tests__` 覆盖金额解析/格式化、负金额、千分位、空值、非法日期、文件大小与百分比。新增 lib 逻辑必须补单测。
