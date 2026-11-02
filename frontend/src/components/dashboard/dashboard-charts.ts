import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

import type {
  DashboardCategorySummary,
  DashboardMonthSummary,
  DashboardPayerSummary,
} from '@/api/types'
import { formatCents } from '@/lib/money'

// 只注册实际使用的模块，避免把完整 echarts 打进首屏。
use([
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  CanvasRenderer,
])

export interface ChartTheme {
  primary: string
  primaryHover: string
  text: string
  textSecondary: string
  textMuted: string
  border: string
  borderStrong: string
  surface: string
}

/** 从 theme.css 的语义 token 读取颜色，图表中不出现裸 hex。 */
export function readCssVar(token: string): string {
  if (typeof document === 'undefined') return 'transparent'
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(token)
    .trim()
  return value === '' ? 'transparent' : value
}

export function readChartTheme(): ChartTheme {
  return {
    primary: readCssVar('--color-primary'),
    primaryHover: readCssVar('--color-primary-hover'),
    text: readCssVar('--color-text'),
    textSecondary: readCssVar('--color-text-secondary'),
    textMuted: readCssVar('--color-text-muted'),
    border: readCssVar('--color-border'),
    borderStrong: readCssVar('--color-border-strong'),
    surface: readCssVar('--color-surface'),
  }
}

/** tooltip 内容来自接口数据，必须转义后再拼 HTML。 */
export function escapeHtml(value: string): string {
  const replacements: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }
  return value.replace(/[&<>"']/g, (character) => replacements[character] ?? character)
}

function truncateLabel(value: string, maxLength = 12): string {
  const characters = Array.from(value)
  return characters.length > maxLength
    ? `${characters.slice(0, maxLength).join('')}…`
    : value
}

function moneyAxisFormatter(value: string | number): string {
  return formatCents(Number(value))
}

function categoryAxisFormatter(value: string | number): string {
  return truncateLabel(String(value))
}

function numericValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (Array.isArray(value)) {
    for (const item of value) {
      if (typeof item === 'number' && Number.isFinite(item)) return item
    }
  }
  return null
}

interface TooltipParam {
  name: string
  value: number | null
  marker: string
}

function toTooltipParam(value: unknown): TooltipParam | null {
  if (typeof value !== 'object' || value === null) return null
  const record = value as Record<string, unknown>
  const name =
    typeof record.name === 'string'
      ? record.name
      : typeof record.axisValueLabel === 'string'
        ? record.axisValueLabel
        : ''
  return {
    name,
    value: numericValue(record.value),
    marker: typeof record.marker === 'string' ? record.marker : '',
  }
}

function tooltipParams(value: unknown): TooltipParam[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => toTooltipParam(item))
      .filter((item): item is TooltipParam => item !== null)
  }
  const single = toTooltipParam(value)
  return single ? [single] : []
}

function tooltipHtml(params: unknown, valueLabel: string): string {
  const items = tooltipParams(params)
  if (items.length === 0) return ''

  return items
    .map((item) => {
      const amount = item.value === null ? '—' : formatCents(item.value)
      return `${item.marker}${escapeHtml(item.name)}<br/><strong>${escapeHtml(valueLabel)}：${amount}</strong>`
    })
    .join('<br/>')
}

function baseTooltip(theme: ChartTheme, valueLabel: string) {
  return {
    trigger: 'axis' as const,
    confine: true,
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    textStyle: { color: theme.text, fontSize: 12 },
    axisPointer: {
      type: 'shadow' as const,
      lineStyle: { color: theme.borderStrong },
    },
    formatter: (params: unknown) => tooltipHtml(params, valueLabel),
  }
}

function baseGrid() {
  return { left: 8, right: 24, top: 16, bottom: 8, containLabel: true }
}

function valueAxis(theme: ChartTheme) {
  return {
    type: 'value' as const,
    splitNumber: 4,
    axisLabel: {
      color: theme.textMuted,
      fontSize: 12,
      formatter: moneyAxisFormatter,
      hideOverlap: true,
    },
    splitLine: { lineStyle: { color: theme.border } },
    axisLine: { show: false },
    axisTick: { show: false },
  }
}

function horizontalBarOption(
  names: string[],
  values: number[],
  seriesName: string,
  color: string,
  emphasisColor: string,
): EChartsOption {
  const theme = readChartTheme()

  return {
    animationDuration: 200,
    aria: { enabled: true },
    grid: baseGrid(),
    // 窄屏下旋转金额轴标签，避免 ¥1,234.56 这类标签互相重叠。
    media: [
      {
        query: { maxWidth: 520 },
        option: {
          grid: { bottom: 28 },
          xAxis: { axisLabel: { rotate: 30 } },
        },
      },
    ],
    tooltip: baseTooltip(theme, seriesName),
    xAxis: valueAxis(theme),
    yAxis: {
      type: 'category',
      inverse: true,
      data: names,
      axisLabel: {
        color: theme.textSecondary,
        fontSize: 12,
        formatter: categoryAxisFormatter,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        name: seriesName,
        data: values,
        barMaxWidth: 16,
        itemStyle: {
          color,
          borderRadius: [0, 4, 4, 0],
        },
        emphasis: { itemStyle: { color: emphasisColor } },
      },
    ],
  }
}

/** 按类别开票金额：金额降序的横向条形图，长名称截断并交给 tooltip 展示全文。 */
export function buildCategoryOption(
  rows: DashboardCategorySummary[],
): EChartsOption {
  const theme = readChartTheme()
  const sorted = [...rows].sort((a, b) => b.total_cents - a.total_cents)
  return horizontalBarOption(
    sorted.map((row) => row.name),
    sorted.map((row) => row.total_cents),
    '开票金额',
    theme.primary,
    theme.primaryHover,
  )
}

/** 按付款人付款金额：金额降序的横向条形图。 */
export function buildPayerOption(rows: DashboardPayerSummary[]): EChartsOption {
  const theme = readChartTheme()
  const sorted = [...rows].sort((a, b) => b.total_cents - a.total_cents)
  return horizontalBarOption(
    sorted.map((row) => row.payer_name),
    sorted.map((row) => row.total_cents),
    '付款金额',
    theme.primary,
    theme.primaryHover,
  )
}

/** 按月份开票金额趋势：折线 + 低透明度面积。 */
export function buildMonthOption(rows: DashboardMonthSummary[]): EChartsOption {
  const theme = readChartTheme()
  const sorted = [...rows].sort((a, b) => a.month.localeCompare(b.month))

  return {
    animationDuration: 200,
    aria: { enabled: true },
    grid: baseGrid(),
    tooltip: baseTooltip(theme, '开票金额'),
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: sorted.map((row) => row.month),
      axisLabel: {
        color: theme.textMuted,
        fontSize: 12,
        hideOverlap: true,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: valueAxis(theme),
    series: [
      {
        type: 'line',
        name: '开票金额',
        data: sorted.map((row) => row.total_cents),
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: theme.primary },
        itemStyle: { color: theme.primary },
        areaStyle: { color: theme.primary, opacity: 0.08 },
      },
    ],
  }
}
