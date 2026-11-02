import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import { deleteDocument, downloadDocument } from '@/api/documents'
import { getExtractionJob } from '@/api/extraction'
import type { Document, ExtractionJob } from '@/api/types'
import {
  apiErrorMessage,
  documentDownloadFileName,
  documentFileName,
  isActiveExtractionStatus,
} from '@/components/document/document-utils'
import { useDocumentList } from './useDocumentList'
import { useDocumentUpload } from './useDocumentUpload'
import { useExtractionPolling } from './useExtractionPolling'
import { useAuthStore } from '@/stores/auth'

export function useUploadsPage() {
  const auth = useAuthStore()

  const {
    filters,
    rows,
    total,
    loading,
    error,
    latestJobs,
    pageSizes,
    refresh,
    setPage,
    setPageSize,
    setDocType,
    setQuery,
    resetFilters,
    setLatestJob,
    load,
  } = useDocumentList()

  const {
    file,
    docType,
    title,
    submitting,
    error: uploadError,
    outcome,
    submit,
  } = useDocumentUpload()

  const trackedJob = ref<ExtractionJob | null>(null)
  const pollError = ref('')
  const queryInput = ref(filters.q)

  const previewOpen = ref(false)
  const previewTarget = ref<Document | null>(null)
  const deleteTarget = ref<Document | null>(null)
  const deleting = ref(false)
  const downloadingId = ref<number | null>(null)

  const poll = useExtractionPolling<ExtractionJob>({
    fetcher: (signal) => {
      const job = trackedJob.value
      if (!job) return Promise.reject(new Error('missing tracked job'))
      return getExtractionJob(job.id, signal).then((detail) => detail.job)
    },
    shouldContinue: (job) => isActiveExtractionStatus(job.status),
    onUpdate: (job) => {
      trackedJob.value = job
      pollError.value = ''
      setLatestJob(job)
      if (outcome.value) {
        outcome.value = { ...outcome.value, job }
      }
      if (!isActiveExtractionStatus(job.status)) {
        refresh()
      }
    },
    intervalMs: 3000,
    onError: (caught) => {
      pollError.value = apiErrorMessage(caught, '状态刷新失败，请稍后重试')
    },
  })

  const uploadOutcome = computed(() => {
    if (!outcome.value) return null
    return { ...outcome.value, job: trackedJob.value ?? outcome.value.job }
  })

  const uploadDisabledReason = computed(() =>
    auth.isAuthenticated ? '' : '登录状态已失效，请重新登录后再上传。',
  )

  const deleteOpen = computed({
    get: () => deleteTarget.value !== null,
    set: (value: boolean) => {
      if (!value && !deleting.value) deleteTarget.value = null
    },
  })

  const deleteConsequence = computed(() => {
    if (!deleteTarget.value) return ''
    const name = documentFileName(deleteTarget.value)
    const displayName = name.length > 60 ? `${name.slice(0, 60)}…` : name
    return `将删除「${displayName}」及其文件版本，不可恢复。已生成的审核任务不会被删除。`
  })

  watch(
    () => filters.q,
    (value) => {
      queryInput.value = value
    },
  )

  function submitSearch(): void {
    setQuery(queryInput.value)
  }

  function resetSearch(): void {
    queryInput.value = ''
    resetFilters()
  }

  function handleDocType(value: string): void {
    setDocType(value)
  }

  function handlePage(value: number): void {
    setPage(value)
  }

  function handlePageSize(value: number): void {
    setPageSize(value)
  }

  async function handleUpload(): Promise<void> {
    const result = await submit()
    if (!result) return

    if (result.reused) {
      toast.info('文件已存在，未新建版本。')
    } else if (result.job) {
      toast.success('上传成功，识别任务已创建。')
    } else {
      toast.success('文件上传成功。')
    }

    poll.stop()
    pollError.value = ''
    trackedJob.value = result.job
    if (result.job) {
      setLatestJob(result.job)
      if (isActiveExtractionStatus(result.job.status)) poll.start()
    }
    refresh()
  }

  function openPreview(document: Document): void {
    previewTarget.value = document
    previewOpen.value = true
  }

  function saveBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  async function handleDownload(document: Document): Promise<void> {
    if (!auth.isAdmin || downloadingId.value !== null) return

    downloadingId.value = document.id
    try {
      const blob = await downloadDocument(document.id)
      saveBlob(blob, documentDownloadFileName(document))
      toast.success('已开始下载。')
    } catch (caught) {
      toast.error(apiErrorMessage(caught, '下载失败，请稍后重试。'))
    } finally {
      downloadingId.value = null
    }
  }

  function askDelete(document: Document): void {
    deleteTarget.value = document
  }

  async function confirmDelete(): Promise<void> {
    if (deleting.value) return
    const target = deleteTarget.value
    if (!target) return

    deleting.value = true
    try {
      await deleteDocument(target.id)
      toast.success('文档已删除。')
      if (previewTarget.value?.id === target.id) previewOpen.value = false

      const shouldGoBack = rows.value.length === 1 && filters.page > 1
      deleteTarget.value = null
      if (shouldGoBack) {
        setPage(filters.page - 1)
      } else {
        refresh()
      }
    } catch (caught) {
      toast.error(apiErrorMessage(caught, '删除失败，请稍后重试。'))
    } finally {
      deleting.value = false
    }
  }

  return {
    isAdmin: computed(() => auth.isAdmin),
    filters,
    rows,
    total,
    loading,
    error,
    latestJobs,
    pageSizes,
    file,
    docType,
    title,
    submitting,
    uploadError,
    uploadOutcome,
    uploadDisabledReason,
    queryInput,
    previewOpen,
    previewTarget,
    deleteOpen,
    deleting,
    downloadingId,
    deleteConsequence,
    polling: poll.polling,
    pollError,
    refresh,
    reload: () => load(true),
    submitSearch,
    resetSearch,
    handleDocType,
    handlePage,
    handlePageSize,
    handleUpload,
    openPreview,
    handleDownload,
    askDelete,
    confirmDelete,
  }
}
