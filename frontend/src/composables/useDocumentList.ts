import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { LocationQuery } from 'vue-router'

import { ApiError } from '@/api/client'
import { getDocument, listDocuments } from '@/api/documents'
import type { Document, DocumentType, ExtractionJob } from '@/api/types'

import {
  DEFAULT_PAGE_SIZE,
  isDocumentType,
  isPageSize,
  latestExtractionJob,
  PAGE_SIZES,
} from '@/components/document/document-utils'
import {
  queryPositiveInt,
  queryString,
  useUrlFilters,
} from './useUrlFilters'

export interface DocumentFilters {
  page: number
  pageSize: number
  docType: DocumentType | 'all'
  q: string
}

function parseFilters(query: LocationQuery): DocumentFilters {
  const docType = queryString(query.doc_type)
  const pageSize = queryPositiveInt(query.page_size, DEFAULT_PAGE_SIZE)

  return {
    page: queryPositiveInt(query.page, 1),
    pageSize: isPageSize(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
    docType: isDocumentType(docType) ? docType : 'all',
    q: queryString(query.q).trim(),
  }
}

function serializeFilters(filters: DocumentFilters): Record<string, string> {
  const query: Record<string, string> = {}
  if (filters.page > 1) query.page = String(filters.page)
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) {
    query.page_size = String(filters.pageSize)
  }
  if (filters.docType !== 'all') query.doc_type = filters.docType
  if (filters.q !== '') query.q = filters.q
  return query
}

export function useDocumentList() {
  const { filters, commit } = useUrlFilters(
    parseFilters,
    serializeFilters,
    () => {
      void load()
    },
  )

  const rows = ref<Document[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  const latestJobs = ref<Record<number, ExtractionJob | null>>({})

  let listController: AbortController | null = null
  let jobsController: AbortController | null = null

  async function loadJobs(
    documents: Document[],
    signal: AbortSignal,
  ): Promise<void> {
    const invoiceDocuments = documents.filter(
      (document) => document.doc_type === 'invoice',
    )
    if (invoiceDocuments.length === 0) {
      latestJobs.value = {}
      return
    }

    const results = await Promise.allSettled(
      invoiceDocuments.map((document) =>
        getDocument(document.id, signal),
      ),
    )
    if (signal.aborted) return

    const next: Record<number, ExtractionJob | null> = {}
    results.forEach((result, index) => {
      const document = invoiceDocuments[index]
      if (!document) return
      next[document.id] =
        result.status === 'fulfilled'
          ? latestExtractionJob(result.value.extraction_jobs)
          : null
    })
    latestJobs.value = next
  }

  async function load(showLoading = true): Promise<void> {
    listController?.abort()
    jobsController?.abort()

    const current = new AbortController()
    listController = current
    const jobsSignal = new AbortController()
    jobsController = jobsSignal

    if (showLoading) loading.value = true
    error.value = ''

    try {
      const page = await listDocuments(
        {
          page: filters.page,
          page_size: filters.pageSize,
          doc_type: filters.docType === 'all' ? undefined : filters.docType,
          q: filters.q === '' ? undefined : filters.q,
        },
        current.signal,
      )
      if (current.signal.aborted) return

      rows.value = page.items
      total.value = page.total
      loading.value = false
      void loadJobs(page.items, jobsSignal.signal)
    } catch (caught) {
      if (current.signal.aborted) return
      rows.value = []
      total.value = 0
      latestJobs.value = {}
      loading.value = false
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '文档列表加载失败，请重试。'
    }
  }

  function refresh(): void {
    void load(false)
  }

  function setPage(value: number): void {
    if (value === filters.page) return
    filters.page = value
    commit()
  }

  function setPageSize(value: number): void {
    if (!isPageSize(value)) return
    filters.pageSize = value
    filters.page = 1
    commit()
  }

  function setDocType(value: string): void {
    const next = isDocumentType(value) ? value : 'all'
    if (filters.docType === next) return
    filters.docType = next
    filters.page = 1
    commit()
  }

  function setQuery(value: string): void {
    const next = value.trim()
    if (filters.q === next) return
    filters.q = next
    filters.page = 1
    commit()
  }

  function resetFilters(): void {
    filters.docType = 'all'
    filters.q = ''
    filters.page = 1
    commit()
  }

  function setLatestJob(job: ExtractionJob): void {
    latestJobs.value = {
      ...latestJobs.value,
      [job.document_id]: job,
    }
  }

  onMounted(() => {
    void load()
  })

  onBeforeUnmount(() => {
    listController?.abort()
    jobsController?.abort()
  })

  return {
    filters,
    rows,
    total,
    loading,
    error,
    latestJobs,
    pageSizes: PAGE_SIZES,
    load,
    refresh,
    setPage,
    setPageSize,
    setDocType,
    setQuery,
    resetFilters,
    setLatestJob,
  }
}
