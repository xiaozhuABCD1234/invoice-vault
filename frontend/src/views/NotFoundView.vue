<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Home } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'

const router = useRouter()

function goHome(): void {
  void router.replace({ name: 'dashboard' })
}
</script>

<template>
  <div class="flex min-h-dvh flex-col items-center justify-center bg-canvas p-6 text-center">
    <p class="text-kpi font-semibold tabular-nums text-text-muted">404</p>
    <h1 class="mt-2 text-section font-semibold tracking-heading text-text">
      页面不存在
    </h1>
    <p class="mt-2 max-w-md text-body text-text-secondary">
      该链接可能已失效，或你没有访问权限。请返回工作台继续操作。
    </p>
    <Button class="mt-6" @click="goHome">
      <template #icon>
        <Home :size="18" :stroke-width="1.75" aria-hidden="true" />
      </template>
      返回工作台
    </Button>
  </div>
</template>
