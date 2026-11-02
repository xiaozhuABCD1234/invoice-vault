<script setup lang="ts">
import { ref } from 'vue'

import type { AuditLog } from '@/api/types'
import PageHeader from '@/components/common/PageHeader.vue'
import AuditDetailDialog from '@/components/admin/AuditDetailDialog.vue'
import AuditFilterBar from '@/components/admin/AuditFilterBar.vue'
import AuditTable from '@/components/admin/AuditTable.vue'
import { useAuditLogs } from '@/composables/useAuditLogs'

const {
  action,
  entityType,
  entityId,
  actorId,
  dateFrom,
  dateTo,
  page,
  pageSize,
  rows,
  total,
  loading,
  error,
  filterError,
  applyFilters,
  resetFilters,
  reload,
} = useAuditLogs()

const detailOpen = ref(false)
const selectedLog = ref<AuditLog | null>(null)

function openDetail(log: AuditLog): void {
  selectedLog.value = log
  detailOpen.value = true
}
</script>

<template>
  <div>
    <PageHeader
      title="审计日志"
      description="查询关键操作记录，查看变更前后详情。"
    />

    <AuditFilterBar
      v-model:action="action"
      v-model:entityType="entityType"
      v-model:entityId="entityId"
      v-model:actorId="actorId"
      v-model:dateFrom="dateFrom"
      v-model:dateTo="dateTo"
      :error="filterError"
      @submit="applyFilters"
      @reset="resetFilters"
    />

    <div class="mt-4">
      <AuditTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :rows="rows"
        :loading="loading"
        :error="error"
        :total="total"
        @detail="openDetail"
        @retry="reload"
      />
    </div>

    <AuditDetailDialog
      v-model:open="detailOpen"
      :log="selectedLog"
    />
  </div>
</template>
