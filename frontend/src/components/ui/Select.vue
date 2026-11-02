<script setup lang="ts">
import { Check, ChevronDown } from '@lucide/vue'
import {
  SelectContent,
  SelectIcon,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'reka-ui'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

withDefaults(
  defineProps<{
    options: SelectOption[]
    placeholder?: string
    disabled?: boolean
    invalid?: boolean
    id?: string
    name?: string
    ariaLabel?: string
  }>(),
  {
    placeholder: '请选择',
    disabled: false,
    invalid: false,
  },
)

const model = defineModel<string>({ default: '' })
</script>

<template>
  <SelectRoot v-model="model" :disabled="disabled" :name="name">
    <SelectTrigger
      :id="id"
      :aria-label="ariaLabel"
      :aria-invalid="invalid || undefined"
      class="flex h-11 w-full items-center justify-between gap-2 rounded-control border bg-surface px-3 text-input text-text transition-colors duration-150 data-[disabled]:cursor-not-allowed data-[disabled]:bg-surface-muted data-[disabled]:text-text-muted md:h-9"
      :class="
        invalid
          ? 'border-danger hover:border-danger'
          : 'border-border hover:border-border-strong focus:border-primary'
      "
    >
      <SelectValue :placeholder="placeholder" />
      <SelectIcon as-child>
        <ChevronDown
          class="shrink-0 text-text-muted"
          :size="16"
          :stroke-width="1.75"
          aria-hidden="true"
        />
      </SelectIcon>
    </SelectTrigger>

    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="4"
        class="z-50 min-w-40 overflow-hidden rounded-control border border-border bg-surface shadow-float"
      >
        <SelectViewport class="max-h-72 overflow-y-auto p-1">
          <SelectItem
            v-for="option in options"
            :key="option.value"
            :value="option.value"
            :disabled="option.disabled"
            class="relative flex min-h-11 cursor-pointer select-none items-center rounded-tag py-1 pl-2 pr-8 text-body text-text outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-surface-muted"
          >
            <SelectItemText>{{ option.label }}</SelectItemText>
            <SelectItemIndicator class="absolute right-2 inline-flex">
              <Check
                :size="16"
                :stroke-width="1.75"
                aria-hidden="true"
              />
            </SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
