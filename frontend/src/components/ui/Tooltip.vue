<script setup lang="ts">
import {
  TooltipContent,
  TooltipPortal,
  TooltipProvider,
  TooltipRoot,
  TooltipTrigger,
} from 'reka-ui'

withDefaults(
  defineProps<{
    content: string
    side?: 'top' | 'right' | 'bottom' | 'left'
    delay?: number
    disabled?: boolean
  }>(),
  {
    side: 'top',
    delay: 300,
    disabled: false,
  },
)
</script>

<template>
  <slot v-if="disabled" />
  <TooltipProvider v-else :delay-duration="delay">
    <TooltipRoot>
      <TooltipTrigger as-child>
        <slot />
      </TooltipTrigger>
      <TooltipPortal>
        <TooltipContent
          :side="side"
          :side-offset="4"
          class="z-50 rounded-tag bg-text px-2 py-1 text-meta text-surface shadow-float"
        >
          {{ content }}
        </TooltipContent>
      </TooltipPortal>
    </TooltipRoot>
  </TooltipProvider>
</template>
