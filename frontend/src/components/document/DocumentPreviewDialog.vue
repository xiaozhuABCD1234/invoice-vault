<script setup lang="ts">
import { computed } from 'vue'

import type { Document } from '@/api/types'
import Dialog from '@/components/ui/Dialog.vue'
import FilePreview from '@/components/common/FilePreview.vue'

import { documentFileName } from './document-utils'

const props = defineProps<{
  document: Document | null
}>()

const open = defineModel<boolean>('open', { default: false })

const description = computed(() => {
  if (!props.document) return '预览上传的文档'
  const name = documentFileName(props.document)
  return name.length > 80 ? `${name.slice(0, 80)}…` : name
})
</script>

<template>
  <Dialog
    v-model:open="open"
    title="文档预览"
    :description="description"
    width="lg"
  >
    <FilePreview
      v-if="props.document"
      :document-id="props.document.id"
      :height="640"
    />
  </Dialog>
</template>
