import { ref, shallowRef, type Ref, type ShallowRef } from 'vue'

import { apiErrorMessage } from './useApiError'

export interface AsyncData<T> {
  data: ShallowRef<T | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  load: () => Promise<void>
}

/**
 * 单次请求的加载 / 错误 / 数据三态。
 * 通过递增序号丢弃过期响应，避免快速切换筛选时旧结果覆盖新结果。
 */
export function useAsyncData<T>(
  loader: () => Promise<T>,
  fallbackMessage = '加载失败，请稍后重试',
): AsyncData<T> {
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  let requestId = 0

  async function load(): Promise<void> {
    const current = ++requestId
    loading.value = true
    error.value = null

    try {
      const result = await loader()
      if (current === requestId) data.value = result
    } catch (loadError) {
      if (current === requestId) {
        error.value = apiErrorMessage(loadError, fallbackMessage)
      }
    } finally {
      if (current === requestId) loading.value = false
    }
  }

  return { data, loading, error, load }
}
