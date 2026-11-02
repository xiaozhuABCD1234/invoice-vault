import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { LocationQuery } from 'vue-router'

import { ApiError } from '@/api/client'
import { listExtractionJobs } from '@/api/extraction'
import type {
  ExtractionJob,
  ExtractionProvider,
  ExtractionStatus,
} from '@/api/types'

import {
  apiErrorMessage,
  DEFAULT_PAGE_SIZE,
  isActiveExtractionStatus,
  isExtractionProvider,
  isPageSize,
  PAGE_SIZES,
} from '@/components/document/document-utils'
import { useExtractionPolling } from './useExtractionPolling'
import {
  queryPositiveInt,
  queryString,
  useUrlFilters,
} from './useUrlFilters'

export interface ReviewFilters {
  page: number
  pageSize: number
  status: ExtractionStatus | 'all'
  provider: ExtractionProvider | 'all'
}

const STATUS_VALUES: Array<ExtractionStatus | 'all'> = [
  'all',
  'queued',
  'running',
  'review_pending',
  'approved',
  'rejected',
  'failed',
]

function isStatusFilter(value: string): value is ExtractionStatus | 'all' {
  return STATUS_VALUES.includes(value as ExtractionStatus | 'all')
}

function parseFilters(query: LocationQuery): ReviewFilters {
  const status = queryString(query.status)
  const provider = queryString(query.provider)
  const pageSize = queryPositiveInt(query.page_size, DEFAULT_PAGE_SIZE)

  return {
    page: queryPositiveInt(query.page, 1),
    pageSize: isPageSize(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
    status: isStatusFilter(status) ? status : 'review_pending',
    provider: isExtractionProvider(provider) ? provider : 'all',
  }
}

function serializeFilters(filters: ReviewFilters): Record<string, string> {
  const query: Record<string, string> = {}
  if (filters.page > 1) query.page = String(filters.page)
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) {
    query.page_size = String(filters.pageSize)
  }
  if (filters.status !== 'review_pending') query.status = filters.status
  if (filters.provider !== 'all') query.provider = filters.provider
  return query
}

export function useReviewQueue() {
  const { filters, commit } = useUrlFilters(
    parseFilters,
    serializeFilters,
    () => {
      void load()
    },
  )

  const rows = ref<ExtractionJob[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  const pollError = ref('')

  let controller: AbortController | null = null

  function buildQuery() {
    return {
      page: filters.page,
      page_size: filters.pageSize,
      status: filters.status === 'all' ? undefined : filters.status,
      provider: filters.provider === 'all' ? undefined : filters.provider,
    }
  }

  const poll = useExtractionPolling<{
    items: ExtractionJob[]
    total: number
  }>({
    fetcher: async (signal) => {
      const page = await listExtractionJobs(buildQuery(), signal)
      return { items: page.items, total: page.total }
    },
    shouldContinue: (page) => page.items.some((job) => isActiveExtractionStatus(job.status)),
    onUpdate: (page) => {
      rows.value = page.items
      total.value = page.total
      pollError.value = ''
    },
    intervalMs: 5000,
    onError: (caught) => {
      pollError.value = apiErrorMessage(caught, '自动刷新失败，请手动刷新。')
    },
  })

  async function load(showLoading = true): Promise<void> {
    poll.stop()
    controller?.abort()

    const current = new AbortController()
    controller = current
    if (showLoading) loading.value = true
    error.value = ''

    try {
      const page = await listExtractionJobs(buildQuery(), current.signal)
      if (current.signal.aborted) return

      rows.value = page.items
      total.value = page.total
      loading.value = false
      pollError.value = ''
      if (page.items.some((job) => isActiveExtractionStatus(job.status))) {
        poll.start()
      }
    } catch (caught) {
      if (current.signal.aborted) return
      rows.value = []
      total.value = 0
      loading.value = false
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '审核队列加载失败，请重试。'
    }
  }

  function refresh(): void {
    void load(false)
  }

  function setStatus(value: string): void {
    const next = isStatusFilter(value) ? value : 'review_pending'
    if (filters.status === next) return
    filters.status = next
    filters.page = 1
    commit()
  }

  function setProvider(value: string): void {
    const next = isExtractionProvider(value) ? value : 'all'
    if (filters.provider === next) return
    filters.provider = next
    filters.page = 1
    commit()
  }

  function setPage(value: number): void {
    if (filters.page === value) return
    filters.page = value
    commit()
  }

  function setPageSize(value: number): void {
    if (!isPageSize(value)) return
    filters.pageSize = value
    filters.page = 1
    commit()
  }

  function resetFilters(): void {
    filters.status = 'review_pending'
    filters.provider = 'all'
    filters.page = 1
    commit()
  }

  onMounted(() => {
    void load()
  })

  onBeforeUnmount(() => {
    controller?.abort()
    poll.stop()
  })

  return {
    filters,
    rows,
    total,
    loading,
    error,
    pollError,
    polling: poll.polling,
    pageSizes: PAGE_SIZES,
    load,
    refresh,
    setStatus,
    setProvider,
    setPage,
    setPageSize,
    resetFilters,
  }
}
