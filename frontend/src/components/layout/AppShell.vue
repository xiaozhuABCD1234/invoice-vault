<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'

import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'
import { cn } from '@/lib/cn'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()

const mobileOpen = ref(false)

const sidebarOffsetClass = computed(() =>
  ui.sidebarCollapsed ? 'lg:pl-sidebar-collapsed' : 'lg:pl-sidebar',
)

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
  },
)
</script>

<template>
  <div class="min-h-dvh bg-canvas">
    <div class="fixed inset-y-0 left-0 z-30 hidden lg:block">
      <Sidebar />
    </div>

    <div
      :class="
        cn(
          'flex min-h-dvh min-w-0 flex-col transition-none',
          sidebarOffsetClass,
        )
      "
    >
      <Topbar @open-menu="mobileOpen = true" />

      <main id="main-content" class="min-w-0 flex-1 p-6 wide:p-8">
        <RouterView />
      </main>
    </div>

    <DialogRoot v-model:open="mobileOpen">
      <DialogPortal>
        <DialogOverlay class="fixed inset-0 z-40 bg-text/40 lg:hidden" />
        <DialogContent
          class="fixed inset-y-0 left-0 z-50 h-dvh w-sidebar border-r border-border bg-surface p-0 shadow-dialog focus-visible:outline-none lg:hidden"
        >
          <DialogTitle class="sr-only">导航菜单</DialogTitle>
          <DialogDescription class="sr-only">
            选择要前往的页面，按 Esc 关闭。
          </DialogDescription>
          <Sidebar mobile @close="mobileOpen = false" />
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </div>
</template>
