<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ChevronDown,
  ChevronRight,
  LogOut,
  Menu,
} from '@lucide/vue'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from 'reka-ui'
import { toast } from 'vue-sonner'

import Button from '@/components/ui/Button.vue'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{
  (event: 'open-menu'): void
}>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentTitle = computed(() =>
  typeof route.meta.title === 'string' ? route.meta.title : '工作台',
)

const isDashboard = computed(() => route.path === '/dashboard')

const displayName = computed(
  () => auth.user?.display_name ?? auth.user?.username ?? '用户',
)

const roleLabel = computed(() =>
  auth.user?.role === 'admin' ? '管理员' : '普通用户',
)

const initials = computed(() => {
  const name = displayName.value.trim()
  return name.length > 0 ? name.slice(0, 1).toUpperCase() : '?'
})

async function handleLogout(): Promise<void> {
  await auth.logout()
  toast.success('已退出登录')
  await router.replace({ name: 'login' })
}
</script>

<template>
  <header
    class="sticky top-0 z-20 flex h-topbar items-center justify-between gap-4 border-b border-border bg-surface px-4 wide:px-6"
  >
    <div class="flex min-w-0 items-center gap-2">
      <Button
        variant="ghost"
        size="sm"
        class="size-11 shrink-0 px-0 lg:hidden"
        aria-label="打开导航菜单"
        @click="emit('open-menu')"
      >
        <template #icon>
          <Menu :size="20" :stroke-width="1.75" aria-hidden="true" />
        </template>
      </Button>

      <nav aria-label="面包屑" class="min-w-0">
        <ol class="flex min-w-0 items-center gap-1 text-body">
          <li v-if="!isDashboard" class="flex shrink-0 items-center gap-1">
            <RouterLink
              to="/dashboard"
              class="inline-flex min-h-11 items-center px-1 text-text-muted transition-colors duration-150 hover:text-text md:min-h-0"
            >
              工作台
            </RouterLink>
            <ChevronRight
              :size="16"
              :stroke-width="1.75"
              class="text-text-muted"
              aria-hidden="true"
            />
          </li>
          <li class="truncate font-medium text-text" aria-current="page">
            {{ currentTitle }}
          </li>
        </ol>
      </nav>
    </div>

    <DropdownMenuRoot>
      <DropdownMenuTrigger as-child>
        <button
          type="button"
          class="flex h-11 min-w-11 items-center gap-2 rounded-control px-1 text-left transition-colors duration-150 hover:bg-surface-muted sm:h-9 sm:min-w-0"
          :title="displayName"
          aria-label="用户菜单"
        >
          <span
            class="flex size-8 shrink-0 items-center justify-center rounded-pill bg-primary-soft text-body font-semibold text-primary"
            aria-hidden="true"
          >
            {{ initials }}
          </span>
          <span class="hidden min-w-0 flex-col sm:flex">
            <span class="truncate text-body font-medium text-text">
              {{ displayName }}
            </span>
            <span class="text-meta text-text-muted">{{ roleLabel }}</span>
          </span>
          <ChevronDown
            :size="16"
            :stroke-width="1.75"
            class="hidden text-text-muted sm:block"
            aria-hidden="true"
          />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuPortal>
        <DropdownMenuContent
          align="end"
          :side-offset="8"
          class="z-50 w-48 rounded-card border border-border bg-surface p-1 shadow-float"
        >
          <DropdownMenuLabel class="px-2 py-1">
            <span class="block truncate text-body font-medium text-text">
              {{ displayName }}
            </span>
            <span class="block text-meta text-text-muted">{{ roleLabel }}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator class="my-1 h-px bg-border" />
          <DropdownMenuItem
            class="flex min-h-11 cursor-pointer select-none items-center gap-2 rounded-tag px-2 py-2 text-body text-danger outline-none data-[highlighted]:bg-danger-soft"
            @select="handleLogout"
          >
            <LogOut :size="16" :stroke-width="1.75" aria-hidden="true" />
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenuRoot>
  </header>
</template>
