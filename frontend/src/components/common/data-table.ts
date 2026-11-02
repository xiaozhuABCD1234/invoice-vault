export type DataTableAlign = 'left' | 'center' | 'right'
export type DataTableSortOrder = 'asc' | 'desc'

export interface DataTableColumn {
  key: string
  label: string
  align?: DataTableAlign
  /** 列宽（px），用于保持金额 / 状态列节奏稳定。 */
  width?: number
  sortable?: boolean
  /** 内容不换行（发票号、日期、金额等）。 */
  nowrap?: boolean
  /** 宽表格中固定操作列或首列。 */
  fixed?: 'left' | 'right'
}

export interface DataTableSort {
  key: string
  order: DataTableSortOrder
}
