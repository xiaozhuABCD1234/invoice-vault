<script setup lang="ts">
import type { Component } from 'vue'
import { ChevronRight } from '@lucide/vue'
import { RouterLink } from 'vue-router'

import Skeleton from '@/components/ui/Skeleton.vue'
import { EMPTY_TEXT } from '@/lib/format'

withDefaults(
  defineProps<{
    label: string
    hint: string
    count?: number | null
    icon: Component
    to: string
    loading?: boolean
  }>(),
  {
    count: null,
    loading: false,
  },
)
</script>

<template>
  <RouterLink
    :to="to"
    class="group flex min-w-0 items-center gap-3 rounded-card border border-border bg-surface p-4 transition-colors duration-150 hover:border-border-strong hover:bg-surface-muted"
  >
    <span
      class="flex size-10 shrink-0 items-center justify-center rounded-control bg-warning-soft text-warning"
      aria-hidden="true"
    >
      <component :is="icon" :size="20" :stroke-width="1.75" />
    </span>

    <div class="min-w-0 flex-1">
      <div class="flex items-baseline gap-2">
        <Skeleton v-if="loading" class="h-6 w-10" />
        <span v-else class="text-section font-semibold tabular-nums text-text">
          {{ count ?? EMPTY_TEXT }}
        </span>
        <span class="truncate text-body text-text">{{ label }}</span>
      </div>
      <p class="mt-0.5 truncate text-meta text-text-muted">{{ hint }}</p>
    </div>

    <ChevronRight
      :size="16"
      :stroke-width="1.75"
      class="shrink-0 text-text-muted transition-colors group-hover:text-text"
      aria-hidden="true"
    />
  </RouterLink>
</template>
