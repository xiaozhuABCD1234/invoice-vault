<script setup lang="ts">
import { computed } from 'vue'
import { Check, RotateCw, X } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'

const props = withDefaults(
  defineProps<{
    isReviewable: boolean
    approving?: boolean
    rejecting?: boolean
    retrying?: boolean
    canRetry?: boolean
    retryDisabled?: boolean
    layout?: 'header' | 'footer'
  }>(),
  {
    approving: false,
    rejecting: false,
    retrying: false,
    canRetry: false,
    retryDisabled: false,
    layout: 'header',
  },
)

const emit = defineEmits<{
  (event: 'approve'): void
  (event: 'reject'): void
  (event: 'retry'): void
}>()

const isFooter = computed(() => props.layout === 'footer')
const iconSize = computed(() => (isFooter.value ? 18 : 16))
const actionDisabled = computed(
  () =>
    !props.isReviewable ||
    props.approving ||
    props.rejecting ||
    props.retrying,
)
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <Button
      v-if="canRetry && !isFooter"
      variant="secondary"
      size="sm"
      :loading="retrying"
      :disabled="retryDisabled"
      :title="retryDisabled ? '重试次数已达上限（3 次）' : undefined"
      @click="emit('retry')"
    >
      <template #icon>
        <RotateCw :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
      </template>
      重试
    </Button>

    <Button
      variant="secondary"
      :size="isFooter ? 'md' : 'sm'"
      :disabled="actionDisabled"
      @click="emit('reject')"
    >
      <template #icon>
        <X :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
      </template>
      驳回
    </Button>

    <Button
      :variant="isFooter ? 'primary' : 'secondary'"
      :size="isFooter ? 'md' : 'sm'"
      :loading="approving"
      :disabled="actionDisabled"
      @click="emit('approve')"
    >
      <template #icon>
        <Check :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
      </template>
      {{ isFooter ? '通过并创建发票' : '通过' }}
    </Button>
  </div>
</template>
