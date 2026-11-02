<script setup lang="ts">
import { computed } from 'vue'

import DateText from '@/components/common/DateText.vue'
import FilePreview from '@/components/common/FilePreview.vue'
import type { Document } from '@/api/types'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { EMPTY_TEXT, fileSize } from '@/lib/format'

import {
  documentFileName,
  documentTypeLabel,
} from './document-utils'

defineProps<{
  document: Document
}>()

const widePreview = useMediaQuery('(min-width: 768px)')
const previewHeight = computed(() => (widePreview.value ? 720 : 480))
</script>

<template>
  <div class="space-y-3 lg:sticky lg:top-20">
    <FilePreview
      :document-id="document.id"
      :height="previewHeight"
    />

    <section
      class="rounded-card border border-border bg-surface p-4"
      aria-labelledby="review-file-title"
    >
      <h2 id="review-file-title" class="text-heading font-semibold text-text">
        文件信息
      </h2>
      <dl class="mt-3 grid gap-3 text-body sm:grid-cols-2">
        <div class="min-w-0">
          <dt class="text-meta text-text-muted">文件名</dt>
          <dd class="break-words text-text">
            {{ documentFileName(document) }}
          </dd>
        </div>
        <div class="min-w-0">
          <dt class="text-meta text-text-muted">原始文件名</dt>
          <dd class="break-words text-text">
            {{ document.current_version.original_name || EMPTY_TEXT }}
          </dd>
        </div>
        <div>
          <dt class="text-meta text-text-muted">文档类型</dt>
          <dd class="text-text">{{ documentTypeLabel(document.doc_type) }}</dd>
        </div>
        <div>
          <dt class="text-meta text-text-muted">文件大小</dt>
          <dd class="tabular-nums text-text">
            {{ fileSize(document.current_version.size_bytes) }}
          </dd>
        </div>
        <div>
          <dt class="text-meta text-text-muted">上传时间</dt>
          <dd>
            <DateText :value="document.created_at" mode="datetime" />
          </dd>
        </div>
        <div>
          <dt class="text-meta text-text-muted">上传人</dt>
          <dd class="text-text">
            {{ document.owner_name?.trim() || EMPTY_TEXT }}
          </dd>
        </div>
        <div class="min-w-0 sm:col-span-2">
          <dt class="text-meta text-text-muted">SHA-256</dt>
          <dd class="break-all font-mono text-meta text-text-secondary">
            {{ document.current_version.sha256 || EMPTY_TEXT }}
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>
