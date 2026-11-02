<script setup lang="ts">
import type { Component } from 'vue'

import Skeleton from '@/components/ui/Skeleton.vue'

withDefaults(
  defineProps<{
    label: string
    icon: Component
    loading?: boolean
  }>(),
  {
    loading: false,
  },
)
</script>

<template>
  <article class="flex h-full flex-col rounded-card border border-border bg-surface p-4">
    <div class="flex items-start justify-between gap-3">
      <p class="text-body text-text-secondary">{{ label }}</p>
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-control bg-surface-muted text-text-muted"
        aria-hidden="true"
      >
        <component :is="icon" :size="18" :stroke-width="1.75" />
      </span>
    </div>

    <div class="mt-2 min-h-10">
      <slot v-if="!loading" name="value" />
      <Skeleton v-else class="h-8 w-28" />
    </div>

    <div class="mt-1 min-h-5 text-meta text-text-muted">
      <slot v-if="!loading" name="meta" />
      <Skeleton v-else class="h-3 w-36" />
    </div>
  </article>
</template>
