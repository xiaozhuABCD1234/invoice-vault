<script setup lang="ts">
withDefaults(
  defineProps<{
    for?: string
    required?: boolean
  }>(),
  {
    required: false,
  },
)
</script>

<template>
  <label
    :for="for"
    class="block text-body font-medium text-text"
  >
    <slot />
    <template v-if="required">
      <span class="ml-1 text-danger" aria-hidden="true">*</span>
      <span class="sr-only">（必填）</span>
    </template>
  </label>
</template>
