import { computed, onMounted, reactive, ref, watch } from 'vue'

import { listAuditLogs } from '@/api/audit'
import { useAsyncData } from './useAsyncData'
import { usePageClamp } from './usePageClamp'
import { normalizePageSize, useUrlQuery } from './useUrlQuery'

interface AuditFilterValues {
  action: string
  entityType: string
  entityId: string
  actorId: string
  dateFrom: string
  dateTo: string
}

function sanitizeId(value: string): string {
  return /^\d+$/.test(value) ? value : ''
}

function validateFilters(filters: AuditFilterValues): string {
  if (filters.actorId !== '' && !/^\d+$/.test(filters.actorId)) {
    return '操作人 ID 需为数字'
  }
  if (
    filters.dateFrom !== '' &&
    filters.dateTo !== '' &&
    filters.dateFrom > filters.dateTo
  ) {
    return '开始日期不能晚于结束日期'
  }
  return ''
}

export function useAuditLogs() {
  const url = useUrlQuery()

  const initial: AuditFilterValues = {
    action: url.readString('action'),
    entityType: url.readString('entity_type'),
    entityId: url.readString('entity_id'),
    actorId: sanitizeId(url.readString('actor_id')),
    dateFrom: url.readString('date_from'),
    dateTo: url.readString('date_to'),
  }

  const action = ref(initial.action)
  const entityType = ref(initial.entityType)
  const entityId = ref(initial.entityId)
  const actorId = ref(initial.actorId)
  const dateFrom = ref(initial.dateFrom)
  const dateTo = ref(initial.dateTo)

  const applied = reactive({ ...initial })

  const page = ref(url.readInt('page', 1, 1))
  const pageSize = ref(normalizePageSize(url.readInt('page_size', 20, 1)))
  const filterError = ref('')

  const state = useAsyncData(
    () =>
      listAuditLogs({
        page: page.value,
        page_size: pageSize.value,
        action: applied.action || undefined,
        entity_type: applied.entityType || undefined,
        entity_id: applied.entityId || undefined,
        actor_id: applied.actorId === '' ? undefined : Number(applied.actorId),
        date_from: applied.dateFrom || undefined,
        date_to: applied.dateTo || undefined,
      }),
    '审计日志加载失败，请稍后重试',
  )

  const rows = computed(() => state.data.value?.items ?? [])
  const total = computed(() => state.data.value?.total ?? 0)
  usePageClamp(page, pageSize, total)

  function syncUrl(): void {
    url.update({
      action: applied.action || null,
      entity_type: applied.entityType || null,
      entity_id: applied.entityId || null,
      actor_id: applied.actorId || null,
      date_from: applied.dateFrom || null,
      date_to: applied.dateTo || null,
      page: page.value > 1 ? page.value : null,
      page_size: pageSize.value !== 20 ? pageSize.value : null,
    })
  }

  function reload(): void {
    void state.load()
  }

  function currentDraft(): AuditFilterValues {
    return {
      action: action.value.trim(),
      entityType: entityType.value.trim(),
      entityId: entityId.value.trim(),
      actorId: actorId.value.trim(),
      dateFrom: dateFrom.value,
      dateTo: dateTo.value,
    }
  }

  function applyFilters(): void {
    const next = currentDraft()
    const error = validateFilters(next)
    filterError.value = error
    if (error !== '') return

    Object.assign(applied, next)
    if (page.value !== 1) {
      page.value = 1
    } else {
      syncUrl()
      reload()
    }
  }

  function resetFilters(): void {
    action.value = ''
    entityType.value = ''
    entityId.value = ''
    actorId.value = ''
    dateFrom.value = ''
    dateTo.value = ''
    filterError.value = ''

    applied.action = ''
    applied.entityType = ''
    applied.entityId = ''
    applied.actorId = ''
    applied.dateFrom = ''
    applied.dateTo = ''

    if (page.value !== 1) {
      page.value = 1
    } else {
      syncUrl()
      reload()
    }
  }

  watch([page, pageSize], () => {
    syncUrl()
    reload()
  })

  onMounted(reload)

  return {
    action,
    entityType,
    entityId,
    actorId,
    dateFrom,
    dateTo,
    page,
    pageSize,
    rows,
    total,
    loading: state.loading,
    error: state.error,
    filterError,
    applyFilters,
    resetFilters,
    reload,
  }
}
