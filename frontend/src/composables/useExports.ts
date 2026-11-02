import { computed, onMounted, onScopeDispose, ref, watch } from 'vue'

import { ApiError } from '@/api/client'
import { getExport, listExports } from '@/api/reports'
import type { ExportJob } from '@/api/types'
import { useAsyncData } from './useAsyncData'
import { usePageClamp } from './usePageClamp'
import { normalizePageSize, useUrlQuery } from './useUrlQuery'

const POLL_INTERVAL_MS = 3000

export function useExports() {
  const url = useUrlQuery()

  const page = ref(url.readInt('page', 1, 1))
  const pageSize = ref(normalizePageSize(url.readInt('page_size', 20, 1)))

  const state = useAsyncData(
    () => listExports({ page: page.value, page_size: pageSize.value }),
    '导出任务加载失败，请稍后重试',
  )

  const rows = computed(() => state.data.value?.items ?? [])
  const total = computed(() => state.data.value?.total ?? 0)
  usePageClamp(page, pageSize, total)

  const timers = new Map<number, ReturnType<typeof setTimeout>>()
  let disposed = false

  function syncUrl(): void {
    url.update({
      page: page.value > 1 ? page.value : null,
      page_size: pageSize.value !== 20 ? pageSize.value : null,
    })
  }

  function reload(): void {
    void state.load()
  }

  function upsert(job: ExportJob): void {
    const current = state.data.value
    if (!current) return
    if (!current.items.some((item) => item.id === job.id)) return

    state.data.value = {
      ...current,
      items: current.items.map((item) => (item.id === job.id ? job : item)),
    }
  }

  function schedule(id: number): void {
    if (disposed || timers.has(id)) return
    timers.set(
      id,
      setTimeout(() => {
        timers.delete(id)
        void poll(id)
      }, POLL_INTERVAL_MS),
    )
  }

  async function poll(id: number): Promise<void> {
    try {
      const job = await getExport(id)
      upsert(job)
      if (job.status === 'queued' || job.status === 'running') {
        schedule(id)
      }
    } catch (error) {
      // 任务不存在时停止轮询；其他临时错误继续下一次轮询。
      if (error instanceof ApiError && error.status === 404) return
      schedule(id)
    }
  }

  function track(id: number): void {
    schedule(id)
  }

  function stopAll(): void {
    disposed = true
    for (const timer of timers.values()) clearTimeout(timer)
    timers.clear()
  }

  onScopeDispose(stopAll)

  watch([page, pageSize], () => {
    syncUrl()
    reload()
  })

  watch(
    () => state.data.value,
    (pageData) => {
      if (!pageData) return
      for (const job of pageData.items) {
        if (job.status === 'queued' || job.status === 'running') {
          track(job.id)
        }
      }
    },
  )

  onMounted(reload)

  return {
    page,
    pageSize,
    rows,
    total,
    loading: state.loading,
    error: state.error,
    reload,
    track,
  }
}
