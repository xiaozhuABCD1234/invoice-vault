<script setup lang="ts">
import { SwitchRoot, SwitchThumb } from 'reka-ui'

withDefaults(
  defineProps<{
    id: string
    label: string
    description?: string
    disabled?: boolean
  }>(),
  {
    description: '',
    disabled: false,
  },
)

const model = defineModel<boolean>({ default: false })

defineSlots<{
  /** 标签右侧的补充信息（如配置来源标记）。 */
  'label-extra'?: () => unknown
}>()
</script>

<template>
  <div class="flex items-start justify-between gap-4">
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <label :for="id" class="block text-body font-medium text-text">
          {{ label }}
        </label>
        <slot name="label-extra" />
      </div>
      <p
        v-if="description"
        :id="`${id}-description`"
        class="mt-0.5 text-meta text-text-muted"
      >
        {{ description }}
      </p>
    </div>

    <SwitchRoot
      :id="id"
      v-model="model"
      :disabled="disabled"
      :aria-describedby="description ? `${id}-description` : undefined"
      class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-pill border border-border-strong bg-surface-muted transition-colors duration-150 data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50"
    >
      <SwitchThumb
        class="ml-0.5 block size-5 rounded-pill bg-surface shadow-float transition-transform duration-150 data-[state=checked]:translate-x-5"
      />
    </SwitchRoot>
  </div>
</template>
