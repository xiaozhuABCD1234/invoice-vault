<script setup lang="ts">
import { RouterView } from 'vue-router'
import { Toaster } from 'vue-sonner'

const toasterStyle = {
  '--normal-bg': 'var(--color-surface)',
  '--normal-border': 'var(--color-border)',
  '--normal-text': 'var(--color-text)',
  '--border-radius': 'var(--radius-card)',
}
</script>

<template>
  <RouterView />
  <Toaster
    position="top-right"
    theme="light"
    :duration="4000"
    :close-button="false"
    :rich-colors="false"
    container-aria-label="通知"
    :style="toasterStyle"
  />
</template>
