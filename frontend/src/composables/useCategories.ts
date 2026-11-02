import { computed, onMounted } from 'vue'

import { listCategories } from '@/api/categories'
import { useAsyncData } from './useAsyncData'

export function useCategories() {
  const state = useAsyncData(
    () => listCategories({ include_inactive: true }),
    '类别列表加载失败，请稍后重试',
  )

  const categories = computed(() => state.data.value?.items ?? [])

  function reload(): void {
    void state.load()
  }

  onMounted(reload)

  return {
    categories,
    loading: state.loading,
    error: state.error,
    reload,
  }
}
