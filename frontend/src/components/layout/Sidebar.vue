<script setup lang="ts">
import { computed, type Component } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ClipboardCheck,
  FileDown,
  FileText,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  ReceiptText,
  Scale,
  ScrollText,
  Upload,
  Users,
  Wallet,
  X,
} from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { cn } from '@/lib/cn'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

interface NavItem {
  label: string
  to: string
  icon: Component
}

const props = withDefaults(
  defineProps<{
    mobile?: boolean
  }>(),
  {
    mobile: false,
  },
)

const emit = defineEmits<{
  (event: 'close'): void
}>()

const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()

const collapsed = computed(() => !props.mobile && ui.sidebarCollapsed)

const mainNav: NavItem[] = [
  { label: '仪表盘', to: '/dashboard', icon: LayoutDashboard },
  { label: '上传', to: '/uploads', icon: Upload },
  { label: '审核队列', to: '/review', icon: ClipboardCheck },
  { label: '发票', to: '/invoices', icon: ReceiptText },
  { label: '付款', to: '/payments', icon: Wallet },
  { label: '对账', to: '/reconciliation', icon: Scale },
  { label: '导出', to: '/exports', icon: FileDown },
]

const adminNav: NavItem[] = [
  { label: '用户管理', to: '/admin/users', icon: Users },
  { label: '审计日志', to: '/admin/audit', icon: ScrollText },
]

const visibleAdminNav = computed(() => (auth.isAdmin ? adminNav : []))

function isActive(item: NavItem): boolean {
  if (item.to === '/dashboard') return route.path === '/dashboard'
  return route.path === item.to || route.path.startsWith(`${item.to}/`)
}
</script>

<template>
  <aside
    :class="
      cn(
        'flex h-full flex-col border-r border-border bg-surface',
        collapsed ? 'w-sidebar-collapsed' : 'w-sidebar',
      )
    "
  >
    <div
      class="flex h-topbar shrink-0 items-center gap-2 border-b border-border px-3"
      :class="collapsed ? 'justify-center px-0' : ''"
    >
      <RouterLink
        to="/dashboard"
        class="flex min-w-0 flex-1 items-center gap-3"
        :class="collapsed ? 'justify-center' : ''"
        aria-label="发票管理系统首页"
      >
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-control bg-primary text-surface"
          aria-hidden="true"
        >
          <FileText :size="18" :stroke-width="1.75" />
        </span>
        <span
          v-if="!collapsed"
          class="truncate text-body font-semibold text-text"
        >
          发票管理系统
        </span>
      </RouterLink>

      <Button
        v-if="mobile"
        variant="ghost"
        size="sm"
        class="size-11 shrink-0 px-0"
        aria-label="关闭导航菜单"
        @click="emit('close')"
      >
        <template #icon>
          <X :size="18" :stroke-width="1.75" aria-hidden="true" />
        </template>
      </Button>
    </div>

    <nav class="flex-1 overflow-y-auto p-2" aria-label="主导航">
      <ul class="space-y-1">
        <li v-for="item in mainNav" :key="item.to">
          <Tooltip
            :content="item.label"
            side="right"
            :disabled="!collapsed"
          >
            <RouterLink
              :to="item.to"
              :aria-current="isActive(item) ? 'page' : undefined"
              :aria-label="collapsed ? item.label : undefined"
              :class="
                cn(
                  'flex min-h-11 items-center gap-3 rounded-control px-3 text-body font-medium transition-colors duration-150 lg:h-9 lg:min-h-0',
                  collapsed ? 'justify-center px-0' : '',
                  isActive(item)
                    ? 'bg-primary-soft text-primary'
                    : 'text-text-secondary hover:bg-surface-muted hover:text-text',
                )
              "
            >
              <component
                :is="item.icon"
                :size="20"
                :stroke-width="1.75"
                class="shrink-0"
                aria-hidden="true"
              />
              <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
            </RouterLink>
          </Tooltip>
        </li>
      </ul>

      <div
        v-if="visibleAdminNav.length > 0"
        class="mt-4 border-t border-border pt-4"
      >
        <p
          v-if="!collapsed"
          class="px-3 pb-2 text-meta font-medium text-text-muted"
        >
          管理
        </p>
        <ul class="space-y-1">
          <li v-for="item in visibleAdminNav" :key="item.to">
            <Tooltip
              :content="item.label"
              side="right"
              :disabled="!collapsed"
            >
              <RouterLink
                :to="item.to"
                :aria-current="isActive(item) ? 'page' : undefined"
                :aria-label="collapsed ? item.label : undefined"
                :class="
                  cn(
                    'flex min-h-11 items-center gap-3 rounded-control px-3 text-body font-medium transition-colors duration-150 lg:h-9 lg:min-h-0',
                    collapsed ? 'justify-center px-0' : '',
                    isActive(item)
                      ? 'bg-primary-soft text-primary'
                      : 'text-text-secondary hover:bg-surface-muted hover:text-text',
                  )
                "
              >
                <component
                  :is="item.icon"
                  :size="20"
                  :stroke-width="1.75"
                  class="shrink-0"
                  aria-hidden="true"
                />
                <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
              </RouterLink>
            </Tooltip>
          </li>
        </ul>
      </div>
    </nav>

    <div v-if="!mobile" class="shrink-0 border-t border-border p-2">
      <Button
        variant="ghost"
        size="sm"
        class="w-full"
        :class="collapsed ? 'justify-center px-0' : 'justify-start'"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        :aria-expanded="!collapsed"
        @click="ui.toggleSidebar()"
      >
        <template #icon>
          <PanelLeftOpen
            v-if="collapsed"
            :size="18"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          <PanelLeftClose
            v-else
            :size="18"
            :stroke-width="1.75"
            aria-hidden="true"
          />
        </template>
        <span v-if="!collapsed">收起侧栏</span>
      </Button>
    </div>
  </aside>
</template>
