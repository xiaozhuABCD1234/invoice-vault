import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'

import { deleteReportTemplate, listReportTemplates } from '@/api/reports'
import { apiErrorMessage } from './useApiError'
import { useAsyncData } from './useAsyncData'

export function useReportTemplates() {
  const state = useAsyncData(
    listReportTemplates,
    '模板列表加载失败，请稍后重试',
  )

  const templates = computed(() => state.data.value?.items ?? [])
  const deletingId = ref<number | null>(null)

  function reload(): void {
    void state.load()
  }

  async function removeTemplate(id: number): Promise<boolean> {
    deletingId.value = id
    try {
      await deleteReportTemplate(id)
      toast.success('模板已删除')
      await state.load()
      return true
    } catch (error) {
      toast.error(apiErrorMessage(error, '删除模板失败，请稍后重试'))
      return false
    } finally {
      deletingId.value = null
    }
  }

  onMounted(reload)

  return {
    templates,
    loading: state.loading,
    error: state.error,
    deletingId,
    reload,
    removeTemplate,
  }
}
