import { computed, onMounted, reactive, ref, watch } from 'vue'

import { listUsers } from '@/api/users'
import type { Role } from '@/api/types'
import { useAsyncData } from './useAsyncData'
import { usePageClamp } from './usePageClamp'
import { normalizePageSize, useUrlQuery } from './useUrlQuery'

export type UserActiveFilter = '' | 'true' | 'false'

function normalizeRole(value: string): Role | '' {
  return value === 'admin' || value === 'user' ? value : ''
}

function normalizeActive(value: string): UserActiveFilter {
  return value === 'true' || value === 'false' ? value : ''
}

export function useAdminUsers() {
  const url = useUrlQuery()

  const initialQ = url.readString('q')
  const initialRole = normalizeRole(url.readString('role'))
  const initialActive = normalizeActive(url.readString('is_active'))

  const q = ref(initialQ)
  const role = ref<string>(initialRole === '' ? 'all' : initialRole)
  const isActive = ref<string>(
    initialActive === '' ? 'all' : initialActive,
  )

  const page = ref(url.readInt('page', 1, 1))
  const pageSize = ref(normalizePageSize(url.readInt('page_size', 20, 1)))

  const applied = reactive({
    q: initialQ.trim(),
    role: initialRole,
    isActive: initialActive,
  })

  const state = useAsyncData(
    () =>
      listUsers({
        page: page.value,
        page_size: pageSize.value,
        q: applied.q || undefined,
        role: applied.role || undefined,
        is_active:
          applied.isActive === ''
            ? undefined
            : applied.isActive === 'true',
      }),
    '用户列表加载失败，请稍后重试',
  )

  const rows = computed(() => state.data.value?.items ?? [])
  const total = computed(() => state.data.value?.total ?? 0)
  usePageClamp(page, pageSize, total)

  function syncUrl(): void {
    url.update({
      q: applied.q || null,
      role: applied.role || null,
      is_active: applied.isActive || null,
      page: page.value > 1 ? page.value : null,
      page_size: pageSize.value !== 20 ? pageSize.value : null,
    })
  }

  function reload(): void {
    void state.load()
  }

  function applyFilters(): void {
    applied.q = q.value.trim()
    applied.role =
      role.value === 'admin' || role.value === 'user' ? role.value : ''
    applied.isActive =
      isActive.value === 'true' || isActive.value === 'false'
        ? isActive.value
        : ''

    if (page.value !== 1) {
      page.value = 1
    } else {
      syncUrl()
      reload()
    }
  }

  function resetFilters(): void {
    q.value = ''
    role.value = 'all'
    isActive.value = 'all'
    applied.q = ''
    applied.role = ''
    applied.isActive = ''

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
    q,
    role,
    isActive,
    page,
    pageSize,
    rows,
    total,
    loading: state.loading,
    error: state.error,
    applyFilters,
    resetFilters,
    reload,
  }
}
