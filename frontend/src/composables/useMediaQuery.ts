import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/** 响应式媒体查询；仅在浏览器端监听，组件卸载时清理。 */
export function useMediaQuery(query: string): Ref<boolean> {
  const matches = ref(
    typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia(query).matches,
  )
  let media: MediaQueryList | null = null

  function update(event?: MediaQueryListEvent): void {
    matches.value = event ? event.matches : (media?.matches ?? false)
  }

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return
    }
    media = window.matchMedia(query)
    update()
    media.addEventListener('change', update)
  })

  onBeforeUnmount(() => {
    media?.removeEventListener('change', update)
  })

  return matches
}
