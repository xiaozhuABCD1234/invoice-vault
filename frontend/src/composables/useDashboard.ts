import { computed, onMounted, ref, watch } from 'vue'

import { getDashboardSummary } from '@/api/dashboard'
import { useAsyncData } from './useAsyncData'
import { useUrlQuery } from './useUrlQuery'

export function useDashboard() {
  const url = useUrlQuery()

  const dateFrom = ref(url.readString('date_from'))
  const dateTo = ref(url.readString('date_to'))

  const rangeError = computed(() =>
    dateFrom.value !== '' &&
    dateTo.value !== '' &&
    dateFrom.value > dateTo.value
      ? '开始日期不能晚于结束日期'
      : '',
  )

  const state = useAsyncData(
    () =>
      getDashboardSummary({
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined,
      }),
    '仪表盘数据加载失败，请稍后重试',
  )

  const summary = computed(() => state.data.value)

  function syncUrl(): void {
    url.update({
      date_from: dateFrom.value || null,
      date_to: dateTo.value || null,
    })
  }

  function reload(): void {
    if (rangeError.value !== '') return
    void state.load()
  }

  watch([dateFrom, dateTo], () => {
    syncUrl()
    reload()
  })

  onMounted(reload)

  return {
    dateFrom,
    dateTo,
    rangeError,
    summary,
    loading: state.loading,
    error: state.error,
    reload,
  }
}
