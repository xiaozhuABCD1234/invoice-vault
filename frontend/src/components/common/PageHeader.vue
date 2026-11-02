<script setup lang="ts">
import { ArrowLeft, ChevronRight } from '@lucide/vue'
import { RouterLink } from 'vue-router'

defineProps<{
  title: string
  description?: string
  backTo?: string
  breadcrumbs?: Array<{ label: string; to?: string }>
}>()
</script>

<template>
  <header class="mb-6 space-y-3">
    <nav v-if="breadcrumbs && breadcrumbs.length > 0" aria-label="面包屑">
      <ol class="flex flex-wrap items-center gap-1 text-meta text-text-muted">
        <li
          v-for="(crumb, index) in breadcrumbs"
          :key="`${crumb.label}-${index}`"
          class="flex items-center gap-1"
        >
          <ChevronRight
            v-if="index > 0"
            :size="16"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          <RouterLink
            v-if="crumb.to"
            :to="crumb.to"
            class="hover:text-text"
          >
            {{ crumb.label }}
          </RouterLink>
          <span
            v-else
            :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined"
          >
            {{ crumb.label }}
          </span>
        </li>
      </ol>
    </nav>

    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex min-w-0 items-start gap-2">
        <RouterLink
          v-if="backTo"
          :to="backTo"
          class="mt-1 inline-flex size-11 shrink-0 items-center justify-center rounded-control text-text-secondary transition-colors duration-150 hover:bg-surface-muted hover:text-text md:size-8"
          aria-label="返回上一页"
        >
          <ArrowLeft :size="18" :stroke-width="1.75" aria-hidden="true" />
        </RouterLink>
        <div class="min-w-0 space-y-1">
          <h1 class="text-page font-semibold tracking-heading text-text">
            {{ title }}
          </h1>
          <p v-if="description" class="text-body text-text-secondary">
            {{ description }}
          </p>
          <slot name="meta" />
        </div>
      </div>

      <div
        v-if="$slots.actions"
        class="flex shrink-0 flex-wrap items-center gap-2"
      >
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
