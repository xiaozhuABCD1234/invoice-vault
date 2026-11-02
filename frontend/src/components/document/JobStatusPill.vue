<script setup lang="ts">
import type { ExtractionStatus } from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

import StatusBadge from '@/components/common/StatusBadge.vue'

withDefaults(
  defineProps<{
    status?: ExtractionStatus | null
    emptyText?: string
  }>(),
  {
    status: null,
    emptyText: EMPTY_TEXT,
  },
)
</script>

<template>
  <StatusBadge
    v-if="status"
    kind="job_status"
    :status="status"
  />
  <span v-else class="text-text-muted">{{ emptyText }}</span>
</template>
