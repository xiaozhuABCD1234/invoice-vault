import { onBeforeUnmount, readonly, ref, type Ref } from 'vue'

export interface ExtractionPollingOptions<T> {
  /** 每轮请求；必须把 signal 传给 api，卸载/停止时中止。 */
  fetcher: (signal: AbortSignal) => Promise<T>
  /** 返回 true 时继续下一轮。 */
  shouldContinue: (value: T) => boolean
  onUpdate: (value: T) => void
  intervalMs?: number
  onError?: (error: unknown) => void
}

export interface ExtractionPollingHandle {
  polling: Readonly<Ref<boolean>>
  start: () => void
  stop: () => void
}

/**
 * 抽取任务轮询：setTimeout 串行调度，避免请求重叠；
 * 停止 / 卸载时清理 timer 与 AbortController。
 */
export function useExtractionPolling<T>(
  options: ExtractionPollingOptions<T>,
): ExtractionPollingHandle {
  const polling = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null
  let generation = 0

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function stop(): void {
    generation += 1
    polling.value = false
    clearTimer()
    controller?.abort()
    controller = null
  }

  function schedule(currentGeneration: number): void {
    clearTimer()
    timer = setTimeout(() => {
      timer = null
      void tick(currentGeneration)
    }, options.intervalMs ?? 3000)
  }

  async function tick(currentGeneration: number): Promise<void> {
    if (!polling.value || currentGeneration !== generation) return

    const current = new AbortController()
    controller = current

    try {
      const value = await options.fetcher(current.signal)
      if (
        !polling.value ||
        currentGeneration !== generation ||
        current.signal.aborted
      ) {
        return
      }

      options.onUpdate(value)
      if (!polling.value || currentGeneration !== generation) return

      if (options.shouldContinue(value)) {
        schedule(currentGeneration)
      } else {
        polling.value = false
      }
    } catch (error) {
      if (current.signal.aborted || currentGeneration !== generation) return
      polling.value = false
      options.onError?.(error)
    } finally {
      if (controller === current) controller = null
    }
  }

  function start(): void {
    stop()
    const currentGeneration = generation
    polling.value = true
    schedule(currentGeneration)
  }

  onBeforeUnmount(stop)

  return { polling: readonly(polling), start, stop }
}
