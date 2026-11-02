import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  getReconciliationSummary,
  listReconciliationIssues,
} from '@/api/reconciliation'
import { ApiError } from '@/api/client'
import type {
  ReconciliationIssue,
  ReconciliationIssueListQuery,
  ReconciliationIssueType,
  ReconciliationSummary,
} from '@/api/types'
import { parseBoolean, parseEnum, parsePage, parsePageSize } from './listQuery'
import { useListUrlState } from './useListUrlState'

export const ISSUE_TYPE_VALUES: ReconciliationIssueType[] = [
  'invoice_unpaid',
  'invoice_partial',
  'payment_unallocated',
  'payment_partial',
  'missing_evidence',
  'duplicate_invoice',
  'item_mismatch',
  'amount_anomaly',
  'date_anomaly',
]

export function useReconciliation() {
  const { state } = useListUrlState<{
    type: string
    include_ignored: boolean
    page: number
    page_size: number
  }>({
    defaults: {
      type: '',
      include_ignored: false,
      page: 1,
      page_size: 20,
    },
    parsers: {
      type: (raw) => parseEnum(ISSUE_TYPE_VALUES, raw),
      include_ignored: parseBoolean,
      page: parsePage,
      page_size: parsePageSize,
    },
  })

  const issues = ref<ReconciliationIssue[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  const summary = ref<ReconciliationSummary | null>(null)
  const summaryLoading = ref(false)
  const summaryError = ref('')
  let issueSeq = 0
  let summarySeq = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  const issueCount = computed(() => {
    if (!summary.value) return 0
    return Object.values(summary.value.issue_counts).reduce(
      (sum, count) => sum + count,
      0,
    )
  })

  function buildQuery(): ReconciliationIssueListQuery {
    return {
      page: state.page,
      page_size: state.page_size,
      type: (state.type || undefined) as ReconciliationIssueType | undefined,
      include_ignored: state.include_ignored || undefined,
    }
  }

  async function loadIssues(): Promise<void> {
    const current = ++issueSeq
    loading.value = true
    error.value = ''
    try {
      const page = await listReconciliationIssues(buildQuery())
      if (current !== issueSeq) return
      issues.value = page.items
      total.value = page.total
      if (page.items.length === 0 && state.page > 1 && page.total > 0) {
        state.page = Math.max(1, Math.ceil(page.total / state.page_size))
      }
    } catch (caught) {
      if (current !== issueSeq) return
      issues.value = []
      total.value = 0
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '对账问题加载失败，请稍后重试。'
    } finally {
      if (current === issueSeq) loading.value = false
    }
  }

  async function loadSummary(): Promise<void> {
    const current = ++summarySeq
    summaryLoading.value = true
    summaryError.value = ''
    try {
      const data = await getReconciliationSummary()
      if (current !== summarySeq) return
      summary.value = data
    } catch (caught) {
      if (current !== summarySeq) return
      summary.value = null
      summaryError.value =
        caught instanceof ApiError
          ? caught.message
          : '对账汇总加载失败，请稍后重试。'
    } finally {
      if (current === summarySeq) summaryLoading.value = false
    }
  }

  function scheduleLoad(): void {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      void loadIssues()
    }, 150)
  }

  watch(state, scheduleLoad, { deep: true })

  function setType(type: string): void {
    state.type = type
    state.page = 1
  }

  function setIncludeIgnored(value: boolean): void {
    state.include_ignored = value
    state.page = 1
  }

  function goToPage(page: number): void {
    state.page = page
  }

  function setPageSize(size: number): void {
    state.page_size = size
    state.page = 1
  }

  function resetFilters(): void {
    state.type = ''
    state.include_ignored = false
    state.page = 1
  }

  function reloadAll(): void {
    void loadSummary()
    void loadIssues()
  }

  void loadSummary()
  void loadIssues()

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return {
    state,
    issues,
    total,
    loading,
    error,
    summary,
    summaryLoading,
    summaryError,
    issueCount,
    loadIssues,
    loadSummary,
    reloadAll,
    setType,
    setIncludeIgnored,
    goToPage,
    setPageSize,
    resetFilters,
  }
}
