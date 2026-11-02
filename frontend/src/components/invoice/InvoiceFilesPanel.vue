<script setup lang="ts">
import { FileText } from '@lucide/vue'

import DateText from '@/components/common/DateText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilePreview from '@/components/common/FilePreview.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Button from '@/components/ui/Button.vue'
import { fileSize } from '@/lib/format'
import type { DocumentDetail } from '@/api/types'

defineProps<{
  documentId: number | null
  document: DocumentDetail | null
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  (event: 'retry'): void
}>()
</script>

<template>
  <section class="space-y-3" aria-label="发票源文件">
    <EmptyState
      v-if="documentId === null"
      title="暂无源文件"
      description="该发票由手工录入或审核通过时未保留原始文件。"
    />

    <template v-else>
      <div class="rounded-card border border-border bg-surface p-4">
        <div v-if="loading" class="space-y-2" role="status" aria-live="polite">
          <Skeleton class="h-4 w-48" />
          <Skeleton class="h-3 w-32" />
          <span class="sr-only">正在加载文件信息</span>
        </div>

        <div v-else-if="document" class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div class="flex min-w-0 items-start gap-2">
            <FileText
              class="mt-1 shrink-0 text-text-muted"
              :size="18"
              :stroke-width="1.75"
              aria-hidden="true"
            />
            <div class="min-w-0">
              <p class="break-all text-body font-medium text-text">
                {{ document.document.current_version.original_name }}
              </p>
              <p class="mt-1 text-meta text-text-secondary">
                {{ fileSize(document.document.current_version.size_bytes) }}
                · 版本 {{ document.document.current_version.version_no }}
                · 上传于
                <DateText
                  :value="document.document.created_at"
                  mode="datetime"
                  class="inline-block"
                />
              </p>
            </div>
          </div>
          <p class="text-meta text-text-muted">
            文档 ID {{ document.document.id }}
          </p>
        </div>

        <div v-else class="flex flex-wrap items-center gap-2 text-body text-danger" role="alert">
          文件信息加载失败
          <Button variant="secondary" size="sm" @click="emit('retry')">
            重试
          </Button>
        </div>
      </div>

      <FilePreview :document-id="documentId" :height="560" />
    </template>
  </section>
</template>
