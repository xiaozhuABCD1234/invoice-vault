import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type Ref,
} from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { listCategories } from '@/api/categories'
import {
  approveExtractionJob,
  getExtractionJob,
  rejectExtractionJob,
  retryExtractionJob,
} from '@/api/extraction'
import { listUserOptions } from '@/api/users'
import type {
  Category,
  ExtractionJobDetail,
  UserOption,
} from '@/api/types'
import {
  apiErrorMessage,
  canRetryExtraction,
  isActiveExtractionStatus,
  retryLimitReached,
} from '@/components/document/document-utils'
import {
  createEmptyInvoiceDraft,
  createInvoiceDraft,
  firstErrorElementId,
  validateInvoiceDraft,
  type InvoiceDraft,
  type InvoiceDraftErrors,
} from '@/components/document/extraction-fields'
import { useExtractionPolling } from './useExtractionPolling'

export function useExtractionReview(jobId: Ref<number | null>) {
  const router = useRouter()

  const detail = ref<ExtractionJobDetail | null>(null)
  const loading = ref(false)
  const error = ref('')
  const actionError = ref('')
  const pollError = ref('')

  const draft = ref<InvoiceDraft>(createEmptyInvoiceDraft())
  const errors = ref<InvoiceDraftErrors>({})

  const approving = ref(false)
  const rejecting = ref(false)
  const retrying = ref(false)
  const rejectOpen = ref(false)
  const rejectError = ref('')

  const categories = ref<Category[]>([])
  const users = ref<UserOption[]>([])
  const optionsLoading = ref(false)
  const optionsError = ref('')

  let controller: AbortController | null = null

  const job = computed(() => detail.value?.job ?? null)
  const document = computed(() => detail.value?.document ?? null)
  const diff = computed(() => detail.value?.diff ?? null)
  const fieldConfidence = computed(
    () => job.value?.validation?.field_confidence ?? null,
  )
  const validationErrors = computed(
    () => job.value?.validation?.errors ?? [],
  )
  const validationWarnings = computed(
    () => job.value?.validation?.warnings ?? [],
  )
  const isReviewable = computed(() => job.value?.status === 'review_pending')
  const canRetry = computed(
    () => (job.value ? canRetryExtraction(job.value) : false),
  )
  const retryDisabled = computed(
    () => (job.value ? retryLimitReached(job.value) : true),
  )

  const poll = useExtractionPolling<ExtractionJobDetail>({
    fetcher: (signal) => {
      const id = jobId.value
      if (id === null) return Promise.reject(new Error('missing job id'))
      return getExtractionJob(id, signal)
    },
    shouldContinue: (value) =>
      isActiveExtractionStatus(value.job.status),
    onUpdate: (value) => {
      applyDetail(value)
      pollError.value = ''
    },
    intervalMs: 3000,
    onError: (caught) => {
      pollError.value = apiErrorMessage(caught, '自动刷新失败，请手动刷新。')
    },
  })

  function applyDetail(value: ExtractionJobDetail): void {
    detail.value = value
    draft.value = createInvoiceDraft(value.job)
    errors.value = {}
  }

  async function load(showLoading = true): Promise<void> {
    poll.stop()
    controller?.abort()

    const id = jobId.value
    actionError.value = ''
    pollError.value = ''
    rejectError.value = ''

    if (id === null || !Number.isSafeInteger(id) || id <= 0) {
      detail.value = null
      loading.value = false
      error.value = '审核任务编号无效，请返回审核队列重新进入。'
      return
    }

    const current = new AbortController()
    controller = current
    if (showLoading) {
      loading.value = true
      detail.value = null
    }
    error.value = ''

    try {
      const value = await getExtractionJob(id, current.signal)
      if (current.signal.aborted) return

      applyDetail(value)
      loading.value = false
      if (isActiveExtractionStatus(value.job.status)) {
        poll.start()
      }
    } catch (caught) {
      if (current.signal.aborted) return
      detail.value = null
      loading.value = false
      error.value = apiErrorMessage(caught, '审核任务加载失败，请重试。')
    }
  }

  async function loadOptions(): Promise<void> {
    if (optionsLoading.value) return

    optionsLoading.value = true
    optionsError.value = ''
    const [categoryResult, userResult] = await Promise.allSettled([
      listCategories(),
      listUserOptions(),
    ] as const)

    if (categoryResult.status === 'fulfilled') {
      categories.value = categoryResult.value.items
    }
    if (userResult.status === 'fulfilled') {
      users.value = userResult.value.items
    }

    const failed = [categoryResult, userResult].find(
      (result) => result.status === 'rejected',
    )
    if (failed && failed.status === 'rejected') {
      optionsError.value = apiErrorMessage(
        failed.reason,
        '类别或用户选项加载失败，请重试。',
      )
    }
    optionsLoading.value = false
  }

  async function focusFirstError(): Promise<void> {
    await nextTick()
    const elementId = firstErrorElementId(errors.value)
    if (!elementId) return
    const element = window.document.getElementById(elementId)
    element?.scrollIntoView({ block: 'center' })
    if (element instanceof HTMLElement) element.focus()
  }

  async function approve(): Promise<void> {
    if (!isReviewable.value || approving.value) return
    const currentDocument = document.value
    const currentJob = job.value
    if (!currentDocument || !currentJob) return

    actionError.value = ''
    const result = validateInvoiceDraft(draft.value, currentDocument.id)
    errors.value = result.errors
    if (!result.payload) {
      actionError.value = '请先修正表单中的必填项或校验错误。'
      await focusFirstError()
      return
    }

    approving.value = true
    try {
      const response = await approveExtractionJob(currentJob.id, result.payload)
      toast.success('审核通过，发票已创建。')
      await router.push({
        name: 'invoice-detail',
        params: { id: response.invoice.id },
      })
    } catch (caught) {
      actionError.value = apiErrorMessage(caught, '审核通过失败，请稍后重试。')
      toast.error(actionError.value)
    } finally {
      approving.value = false
    }
  }

  function openReject(): void {
    if (!isReviewable.value) return
    rejectError.value = ''
    rejectOpen.value = true
  }

  function closeReject(): void {
    if (rejecting.value) return
    rejectOpen.value = false
  }

  async function confirmReject(note: string): Promise<void> {
    if (!isReviewable.value || rejecting.value) return
    const currentJob = job.value
    if (!currentJob) return

    rejecting.value = true
    rejectError.value = ''
    try {
      const rejected = await rejectExtractionJob(currentJob.id, { note })
      if (detail.value) {
        detail.value = { ...detail.value, job: rejected }
      }
      rejectOpen.value = false
      toast.success('已驳回识别结果。')
      await load(false)
    } catch (caught) {
      rejectError.value = apiErrorMessage(caught, '驳回失败，请稍后重试。')
    } finally {
      rejecting.value = false
    }
  }

  async function retry(): Promise<void> {
    const currentJob = job.value
    if (!currentJob || retrying.value || retryDisabled.value) return

    retrying.value = true
    actionError.value = ''
    pollError.value = ''
    try {
      const queued = await retryExtractionJob(currentJob.id)
      if (detail.value) {
        detail.value = { ...detail.value, job: queued }
      }
      errors.value = {}
      toast.success('已重新排队，页面将自动刷新识别状态。')
      if (isActiveExtractionStatus(queued.status)) {
        poll.start()
      } else {
        await load(false)
      }
    } catch (caught) {
      actionError.value = apiErrorMessage(caught, '重试失败，请稍后重试。')
      toast.error(actionError.value)
    } finally {
      retrying.value = false
    }
  }

  watch(
    jobId,
    () => {
      void load()
    },
    { immediate: true },
  )

  watch(
    draft,
    () => {
      if (actionError.value) actionError.value = ''
    },
    { deep: true },
  )

  onMounted(() => {
    void loadOptions()
  })

  onBeforeUnmount(() => {
    controller?.abort()
    poll.stop()
  })

  return {
    detail,
    job,
    document,
    loading,
    error,
    actionError,
    pollError,
    draft,
    errors,
    fieldConfidence,
    validationErrors,
    validationWarnings,
    diff,
    isReviewable,
    canRetry,
    retryDisabled,
    approving,
    rejecting,
    retrying,
    rejectOpen,
    rejectError,
    categories,
    users,
    optionsLoading,
    optionsError,
    polling: poll.polling,
    load,
    loadOptions,
    approve,
    openReject,
    closeReject,
    confirmReject,
    retry,
  }
}
