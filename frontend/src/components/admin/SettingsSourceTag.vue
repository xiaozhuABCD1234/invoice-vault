<script setup lang="ts">
import { computed } from 'vue'

import type { ExtractionSettingSource } from '@/api/types'

const props = defineProps<{
  source: ExtractionSettingSource
}>()

const label = computed(() => {
  if (props.source === 'database') return '数据库'
  if (props.source === 'env') return '环境变量'
  return '默认值'
})
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center rounded-tag border border-border bg-surface-muted px-2 py-0.5 text-meta font-normal text-text-secondary"
    :title="`当前值来自${label}`"
  >
    {{ label }}
  </span>
</template>
