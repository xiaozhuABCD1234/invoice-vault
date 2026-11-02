<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Check,
  CircleAlert,
  Loader2,
  TriangleAlert,
} from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { cn } from '@/lib/cn'
import type { DocumentType } from '@/api/types'
import type { DocumentUploadOutcome } from '@/composables/useDocumentUpload'

import {
  DOCUMENT_TYPE_OPTIONS,
  isActiveExtractionStatus,
} from './document-utils'
import JobStatusPill from './JobStatusPill.vue'
import UploadDropzone from './UploadDropzone.vue'

const props = withDefaults(
  defineProps<{
    submitting?: boolean
    uploadError?: string
    outcome?: DocumentUploadOutcome | null
    polling?: boolean
    pollError?: string
    disabled?: boolean
    disabledReason?: string
  }>(),
  {
    submitting: false,
    uploadError: '',
    outcome: null,
    polling: false,
    pollError: '',
    disabled: false,
    disabledReason: '',
  },
)

const file = defineModel<File | null>('file', { default: null })
const docType = defineModel<DocumentType>('docType', { default: 'invoice' })
const title = defineModel<string>('title', { default: '' })
const fileError = ref('')

const emit = defineEmits<{
  (event: 'submit'): void
}>()

const selectedJob = computed(() => props.outcome?.job ?? null)
const outcomeTone = computed(() => {
  if (!props.outcome) return ''
  return props.outcome.reused
    ? 'border-warning/40 bg-warning-soft'
    : 'border-success/30 bg-success-soft'
})

const outcomeTitle = computed(() => {
  if (!props.outcome) return ''
  if (props.outcome.reused) return '文件已存在，未新建版本。'
  if (props.outcome.job) return '识别任务已创建。'
  if (props.outcome.document.doc_type === 'invoice') {
    return '文件已上传，识别任务未创建。'
  }
  return '文件已上传，该类文档无需识别。'
})

const outcomeIconClass = computed(() =>
  props.outcome?.reused ? 'text-warning' : 'text-success',
)

const canSubmit = computed(
  () =>
    file.value !== null &&
    fileError.value === '' &&
    !props.submitting &&
    !props.disabled,
)

watch(file, (value) => {
  if (value) fileError.value = ''
})

function handleSubmit(): void {
  if (props.disabled || props.submitting) return
  if (!file.value) {
    fileError.value = '请选择要上传的文件。'
    return
  }
  if (fileError.value !== '') return
  emit('submit')
}
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface"
    aria-labelledby="upload-card-title"
  >
    <header class="border-b border-border px-6 py-4">
      <h2 id="upload-card-title" class="text-heading font-semibold text-text">
        上传文档
      </h2>
      <p class="mt-1 text-body text-text-secondary">
        发票上传后自动创建识别任务；其他类型仅归档，不进入识别队列。
      </p>
    </header>

    <form class="space-y-5 p-6" novalidate @submit.prevent="handleSubmit">
      <div
        v-if="disabledReason"
        class="flex items-start gap-2 rounded-control border border-warning/40 bg-warning-soft px-3 py-2 text-body text-warning"
        role="status"
      >
        <TriangleAlert
          class="mt-1 shrink-0"
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>上传已暂停：{{ disabledReason }}</span>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <FormField
          id="upload-doc-type"
          label="文档类型"
          required
        >
          <template #default="{ id, invalid }">
            <Select
              :id="id"
              v-model="docType"
              :options="DOCUMENT_TYPE_OPTIONS"
              :invalid="invalid"
              :disabled="submitting || disabled"
            />
          </template>
        </FormField>

        <FormField
          id="upload-title"
          label="标题"
          hint="可选，用于在列表中快速识别；不填时使用文件名。"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              v-model="title"
              placeholder="例如：7 月差旅发票"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="submitting || disabled"
            />
          </template>
        </FormField>
      </div>

      <div class="space-y-2">
        <p class="text-body font-medium text-text">
          文件
          <span class="ml-1 text-danger" aria-hidden="true">*</span>
          <span class="sr-only">（必填）</span>
        </p>
        <UploadDropzone
          v-model="file"
          v-model:error="fileError"
          :disabled="submitting || disabled"
        />
      </div>

      <p
        v-if="uploadError"
        class="flex items-start gap-2 break-words rounded-control border border-danger/30 bg-danger-soft px-3 py-2 text-body text-danger"
        role="alert"
      >
        <CircleAlert
          class="mt-1 shrink-0"
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>{{ uploadError }}</span>
      </p>

      <div
        v-if="outcome"
        :class="cn('rounded-control border px-4 py-3', outcomeTone)"
        role="status"
        aria-live="polite"
      >
        <div class="flex flex-wrap items-center gap-2 text-body font-medium">
          <Check
            v-if="!outcome.reused"
            :class="outcomeIconClass"
            :size="18"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          <TriangleAlert
            v-else
            :class="outcomeIconClass"
            :size="18"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          <span>{{ outcomeTitle }}</span>
          <JobStatusPill
            v-if="selectedJob"
            :status="selectedJob.status"
          />
        </div>

        <p
          v-if="selectedJob && isActiveExtractionStatus(selectedJob.status)"
          class="mt-2 flex items-center gap-2 text-body text-info"
        >
          <Loader2
            :class="polling ? 'animate-spin' : ''"
            :size="16"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          {{
            polling
              ? '识别中，正在自动刷新状态…'
              : '识别中，自动刷新已暂停，请稍后刷新文档列表。'
          }}
        </p>
        <p
          v-else-if="selectedJob?.status === 'review_pending'"
          class="mt-2 text-body text-text-secondary"
        >
          识别完成，需人工审核。
          <RouterLink
            :to="{ name: 'review-detail', params: { jobId: selectedJob.id } }"
            class="font-medium text-primary hover:underline"
          >
            去审核
          </RouterLink>
        </p>
        <p
          v-else-if="selectedJob?.status === 'failed'"
          class="mt-2 break-words text-body text-danger"
        >
          识别失败：{{ selectedJob.error_message || '请到审核队列重试。' }}
        </p>

        <p
          v-if="pollError"
          class="mt-2 text-meta text-warning"
          role="status"
        >
          状态刷新失败：{{ pollError }}。请稍后刷新文档列表。
        </p>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2">
        <Button
          type="submit"
          :loading="submitting"
          :disabled="!canSubmit"
        >
          {{ submitting ? '正在上传…' : '上传并识别' }}
        </Button>
      </div>
    </form>
  </section>
</template>
