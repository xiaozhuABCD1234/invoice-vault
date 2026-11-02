import { EMPTY_TEXT } from '@/lib/format'

function groupThousands(value: number): string {
  return Math.trunc(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 单价（1/1000 元）→ ¥1.00 / ¥1.005。
 * 金额展示统一走 MoneyText；单价保留千分位精度，只在发票明细内使用。
 */
export function formatUnitPrice(millis: number | null | undefined): string {
  if (typeof millis !== 'number' || !Number.isFinite(millis)) return EMPTY_TEXT

  const rounded = Math.round(millis)
  const negative = rounded < 0
  const absolute = Math.abs(rounded)
  const yuan = Math.floor(absolute / 1000)
  const remainder = absolute % 1000

  let fraction = '00'
  if (remainder === 0) {
    fraction = '00'
  } else if (remainder % 10 === 0) {
    fraction = String(remainder / 10).padStart(2, '0')
  } else {
    fraction = String(remainder).padStart(3, '0')
  }

  return (negative ? '-' : '') + '¥' + groupThousands(yuan) + '.' + fraction
}

/** 元字符串（最多 3 位小数）→ 1/1000 元整数；非法输入返回 null。 */
export function parseYuanToMillis(input: string | null | undefined): number | null {
  if (typeof input !== 'string') return null

  const normalized = input.trim().replace(/[¥￥,\s]/g, '')
  const match = /^(-?)(\d+)(?:\.(\d{1,3}))?$/.exec(normalized)
  if (!match) return null

  const sign = match[1] === '-' ? -1 : 1
  const integerPart = match[2] ?? ''
  const fractionPart = (match[3] ?? '').padEnd(3, '0')
  const millis = Number(integerPart + fractionPart)
  if (!Number.isSafeInteger(millis)) return null
  return sign * millis
}

/** 1/1000 元 → 可编辑的元字符串（最多 3 位小数，去掉末尾 0）。 */
export function millisToYuanInput(millis: number | null | undefined): string {
  if (typeof millis !== 'number' || !Number.isFinite(millis)) return ''

  const rounded = Math.round(millis)
  const negative = rounded < 0
  const absolute = Math.abs(rounded)
  const yuan = Math.floor(absolute / 1000)
  const remainder = absolute % 1000
  const sign = negative ? '-' : ''
  if (remainder === 0) return sign + String(yuan)
  return sign + String(yuan) + '.' + String(remainder).padStart(3, '0').replace(/0+$/, '')
}

/** 税率（bp，100bp = 1%）→ 13% / 6.5%；空值 → —。 */
export function formatTaxRateBp(bp: number | null | undefined): string {
  if (typeof bp !== 'number' || !Number.isFinite(bp)) return EMPTY_TEXT
  const percent = bp / 100
  return Number.isInteger(percent) ? percent.toFixed(0) + '%' : percent.toFixed(1) + '%'
}
