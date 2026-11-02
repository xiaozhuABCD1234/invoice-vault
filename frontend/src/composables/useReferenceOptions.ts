import { ref } from 'vue'

import { listCategories } from '@/api/categories'
import { ApiError } from '@/api/client'
import { listUserOptions } from '@/api/users'
import type { Category, UserOption } from '@/api/types'

function useRemoteOptions<T>(
  loader: () => Promise<T[]>,
  errorMessage: string,
) {
  const options = ref<T[]>([])
  const loading = ref(false)
  const error = ref('')
  let seq = 0

  async function load(): Promise<void> {
    const current = ++seq
    loading.value = true
    error.value = ''
    try {
      const items = await loader()
      if (current !== seq) return
      options.value = items
    } catch (caught) {
      if (current !== seq) return
      error.value =
        caught instanceof ApiError ? caught.message : errorMessage
    } finally {
      if (current === seq) loading.value = false
    }
  }

  void load()

  return { options, loading, error, reload: load }
}

/** 类别下拉（发票筛选、编辑表单共用）。 */
export function useCategoryOptions() {
  const { options, loading, error, reload } = useRemoteOptions<Category>(
    async () => {
      const response = await listCategories({ include_inactive: false })
      return response.items
    },
    '类别加载失败，请重试。',
  )
  return { categories: options, loading, error, reload }
}

/** 用户下拉（申购人 / 负责人 / 付款人）。 */
export function useUserOptions() {
  const { options, loading, error, reload } = useRemoteOptions<UserOption>(
    async () => {
      const response = await listUserOptions()
      return response.items
    },
    '用户列表加载失败，请重试。',
  )
  return { users: options, loading, error, reload }
}
