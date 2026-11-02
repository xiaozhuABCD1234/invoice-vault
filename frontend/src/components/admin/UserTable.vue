<script setup lang="ts">
import { Pencil, Plus } from '@lucide/vue'

import type { User } from '@/api/types'
import DataTable from '@/components/common/DataTable.vue'
import DateText from '@/components/common/DateText.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DataTableColumn } from '@/components/common/data-table'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Pagination from '@/components/ui/Pagination.vue'
import { activeStatusLabel, roleLabel } from './admin-labels'

withDefaults(
  defineProps<{
    rows: User[]
    loading?: boolean
    error?: string | null
    page: number
    pageSize: number
    total: number
  }>(),
  {
    loading: false,
    error: null,
  },
)

const emit = defineEmits<{
  (event: 'edit', user: User): void
  (event: 'create'): void
  (event: 'retry'): void
  (event: 'update:page', page: number): void
  (event: 'update:pageSize', pageSize: number): void
}>()

const columns: DataTableColumn[] = [
  { key: 'username', label: '用户名', width: 160, nowrap: true },
  { key: 'display_name', label: '显示名', width: 160 },
  { key: 'role', label: '角色', width: 110, align: 'center' },
  { key: 'is_active', label: '状态', width: 100, align: 'center' },
  { key: 'created_at', label: '创建时间', width: 150, nowrap: true },
  { key: 'last_login_at', label: '最后登录', width: 150, nowrap: true },
  { key: 'actions', label: '操作', width: 90, align: 'right', fixed: 'right' },
]
</script>

<template>
  <div class="min-w-0">
    <DataTable
      :rows="rows"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :error="error"
      empty="暂无用户"
      empty-description="新建用户后，账号与角色会显示在这里。"
      @retry="emit('retry')"
    >
      <template #cell-username="{ value }">
        <span class="font-mono text-table">{{ value }}</span>
      </template>

      <template #cell-role="{ value }">
        <Badge :tone="value === 'admin' ? 'info' : 'neutral'" :dot="false">
          {{ roleLabel(String(value)) }}
        </Badge>
      </template>

      <template #cell-is_active="{ row }">
        <StatusBadge
          :tone="row.is_active ? 'success' : 'neutral'"
          :label="activeStatusLabel(row.is_active)"
        />
      </template>

      <template #cell-created_at="{ value }">
        <DateText :value="String(value)" mode="datetime" />
      </template>

      <template #cell-last_login_at="{ value }">
        <DateText :value="String(value)" mode="datetime" />
      </template>

      <template #cell-actions="{ row }">
        <div class="flex justify-end">
          <Button
            variant="secondary"
            size="sm"
            :aria-label="`编辑用户 ${row.display_name}`"
            @click="emit('edit', row)"
          >
            <template #icon>
              <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            编辑
          </Button>
        </div>
      </template>

      <template #empty-action>
        <Button variant="secondary" size="sm" @click="emit('create')">
          <template #icon>
            <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建用户
        </Button>
      </template>
    </DataTable>

    <Pagination
      v-if="total > 0 && !error"
      class="mt-3 rounded-card border border-border bg-surface"
      :page="page"
      :page-size="pageSize"
      :total="total"
      @update:page="emit('update:page', $event)"
      @update:page-size="emit('update:pageSize', $event)"
    />
  </div>
</template>
