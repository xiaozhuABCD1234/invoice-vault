<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { getDocumentPreview } from '@/api/documents'
import { ApiError } from '@/api/client'
import type { DocumentPreviewVersion } from '@/api/types'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const props = withDefaults(
  defineProps<{
    documentId: number
    /** latest，或 admin 可用的版本 id。 */
    version?: DocumentPreviewVersion
    /** 预览容器高度（px）。 */
    height?: number
  }>(),
  {
    version: 'latest',
    height: 640,
  },
)

const loading = ref(true)
const error = ref('')
const objectUrl = ref<string | null>(null)
const mimeType = ref('')

let controller: AbortController | null = null

const previewKind = computed<'pdf' | 'image' | 'other'>(() => {
  if (mimeType.value.includes('pdf')) return 'pdf'
  if (mimeType.value.startsWith('image/')) return 'image'
  return 'other'
})

const containerStyle = computed(() => ({ height: `${props.height}px` }))

function revokeObjectUrl(): void {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = null
  }
}

async function load(): Promise<void> {
  controller?.abort()
  const current = new AbortController()
  controller = current

  revokeObjectUrl()
  mimeType.value = ''
  error.value = ''
  loading.value = true

  try {
    const blob = await getDocumentPreview(
      props.documentId,
      props.version,
      current.signal,
    )
    if (controller !== current || current.signal.aborted) return
    mimeType.value = blob.type
    objectUrl.value = URL.createObjectURL(blob)
    loading.value = false
  } catch (caught) {
    if (current.signal.aborted) return
    if (controller !== current) return
    error.value =
      caught instanceof ApiError
        ? caught.message
        : '无法加载文档预览，请重试。'
    loading.value = false
  }
}

watch(
  [() => props.documentId, () => props.version],
  () => {
    void load()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  controller?.abort()
  revokeObjectUrl()
})
</script>

<template>
  <div :style="containerStyle" class="w-full">
    <div
      v-if="loading"
      class="flex h-full items-center justify-center rounded-card border border-border bg-surface-muted"
      role="status"
      aria-live="polite"
    >
      <Skeleton class="h-4 w-32" />
      <span class="sr-only">正在加载文档预览</span>
    </div>

    <div
      v-else-if="error"
      class="flex h-full items-center justify-center rounded-card border border-border bg-surface"
    >
      <ErrorState
        title="预览加载失败"
        :message="error"
        @retry="load"
      />
    </div>

    <iframe
      v-else-if="previewKind === 'pdf' && objectUrl"
      :src="objectUrl"
      :title="`文档 ${documentId} 预览`"
      class="h-full w-full rounded-card border border-border bg-surface"
    />

    <div
      v-else-if="previewKind === 'image' && objectUrl"
      class="flex h-full items-center justify-center overflow-auto rounded-card border border-border bg-surface-muted"
    >
      <img
        :src="objectUrl"
        :alt="`文档 ${documentId} 预览`"
        class="max-h-full max-w-full object-contain"
      />
    </div>

    <div
      v-else
      class="flex h-full items-center justify-center rounded-card border border-border bg-surface"
    >
      <EmptyState
        title="暂不支持预览该文件类型"
        description="请下载文件后使用本地应用查看。"
      />
    </div>
  </div>
</template>
