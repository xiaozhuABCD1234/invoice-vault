import { watch, type Ref } from 'vue'

/** 删除 / 筛选后总数变小，把越界页码拉回最后一页。 */
export function usePageClamp(
  page: Ref<number>,
  pageSize: Ref<number>,
  total: Ref<number>,
): void {
  watch(total, (value) => {
    const maxPage = Math.max(1, Math.ceil(value / pageSize.value))
    if (page.value > maxPage) page.value = maxPage
  })
}
