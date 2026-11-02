<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { CircleAlert, FileText, X } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import { cn } from '@/lib/cn'
import { fileSize } from '@/lib/format'

import {
  MAX_UPLOAD_BYTES,
  UPLOAD_ACCEPT,
  validateUploadFile,
} from './document-utils'

const props = withDefaults(
  defineProps<{
    disabled?: boolean
  }>(),
  {
    disabled: false,
  },
)

const file = defineModel<File | null>({ default: null })
const error = defineModel<string>('error', { default: '' })

const input = ref<HTMLInputElement | null>(null)
const inputId = useId()
const dragging = ref(false)
let dragDepth = 0

const maxSizeText = computed(() =>
  `${Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)}MB`,
)

const displayName = computed(() => file.value?.name ?? '')
const displaySize = computed(() => fileSize(file.value?.size))

function resetInput(): void {
  if (input.value) input.value.value = ''
}

function applyFile(candidate: File | null | undefined): void {
  if (!candidate) return

  const message = validateUploadFile(candidate)
  if (message) {
    error.value = message
    resetInput()
    return
  }

  file.value = candidate
  error.value = ''
}

function handleChange(event: Event): void {
  const target = event.target as HTMLInputElement
  applyFile(target.files?.[0])
}

function handleDrop(event: DragEvent): void {
  dragDepth = 0
  dragging.value = false
  if (props.disabled) return

  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return
  if (files.length > 1) {
    error.value = '一次只能上传一个文件。'
    return
  }
  applyFile(files[0])
}

function handleDragEnter(): void {
  if (props.disabled) return
  dragDepth += 1
  dragging.value = true
}

function handleDragLeave(): void {
  if (props.disabled) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragging.value = false
}

function clearFile(): void {
  file.value = null
  error.value = ''
  resetInput()
}

watch(file, (value) => {
  if (!value) resetInput()
})
</script>

<template>
  <div class="space-y-2">
    <label
      :for="inputId"
      :class="
        cn(
          'flex min-h-32 w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-card border border-dashed px-4 py-6 text-center transition-colors duration-150 focus-within:border-primary focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring',
          dragging
            ? 'border-primary bg-primary-soft'
            : 'border-border-strong bg-surface hover:bg-surface-muted',
          disabled && 'pointer-events-none cursor-not-allowed bg-surface-muted opacity-60',
        )
      "
      @dragenter.prevent="handleDragEnter"
      @dragover.prevent
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <span
        class="flex size-10 items-center justify-center rounded-pill bg-surface-muted text-text-muted"
        aria-hidden="true"
      >
        <FileText :size="20" :stroke-width="1.75" />
      </span>
      <span class="text-body font-medium text-text">
        {{
          disabled
            ? '上传暂不可用'
            : dragging
              ? '松开鼠标即可选择文件'
              : '拖拽文件到此处，或点击选择文件'
        }}
      </span>
      <span class="text-meta text-text-muted">
        支持 PDF、JPG、JPEG、PNG、WEBP，单文件不超过 {{ maxSizeText }}
      </span>
      <input
        :id="inputId"
        ref="input"
        type="file"
        class="sr-only"
        :accept="UPLOAD_ACCEPT"
        :disabled="disabled"
        :aria-invalid="error ? true : undefined"
        :aria-describedby="error ? `${inputId}-error` : undefined"
        @change="handleChange"
      />
    </label>

    <div
      v-if="file"
      class="flex flex-wrap items-center justify-between gap-2 rounded-control border border-border bg-surface-muted px-3 py-2"
    >
      <span class="min-w-0 break-words text-body text-text">
        {{ displayName }}
        <span class="text-meta text-text-muted">（{{ displaySize }}）</span>
      </span>
      <Button
        variant="ghost"
        size="sm"
        :disabled="disabled"
        aria-label="移除已选文件"
        @click="clearFile"
      >
        <template #icon>
          <X :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        移除
      </Button>
    </div>

    <p
      v-if="error"
      :id="`${inputId}-error`"
      class="flex items-start gap-1 text-meta text-danger"
      aria-live="polite"
    >
      <CircleAlert
        class="mt-1 shrink-0"
        :size="16"
        :stroke-width="1.75"
        aria-hidden="true"
      />
      <span>{{ error }}</span>
    </p>
  </div>
</template>
