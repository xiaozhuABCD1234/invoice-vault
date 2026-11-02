<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { ApiError } from '@/api/client'
import { unignoreReconciliationIssue } from '@/api/reconciliation'
import type { ReconciliationIssue } from '@/api/types'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Pagination from '@/components/ui/Pagination.vue'
import IssueIgnoreDialog from '@/components/reconciliation/IssueIgnoreDialog.vue'
import IssueTable from '@/components/reconciliation/IssueTable.vue'
import ReconciliationFilters from '@/components/reconciliation/ReconciliationFilters.vue'
import ReconciliationSummary from '@/components/reconciliation/ReconciliationSummary.vue'
import { useReconciliation } from '@/composables/useReconciliation'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const {
  state,
  issues,
  total,
  loading,
  error,
  summary,
  summaryLoading,
  summaryError,
  issueCount,
  loadIssues,
  loadSummary,
  reloadAll,
  setType,
  setIncludeIgnored,
  goToPage,
  setPageSize,
  resetFilters,
} = useReconciliation()

const ignoring = ref<ReconciliationIssue | null>(null)
const ignoreOpen = ref(false)
const unignoring = ref<ReconciliationIssue | null>(null)
const unignoreOpen = ref(false)
const unignoreLoading = ref(false)

function viewIssue(issue: ReconciliationIssue): void {
  if (issue.entity_type === 'invoice') {
    void router.push('/invoices/' + issue.entity_id)
  } else if (issue.entity_type === 'payment') {
    void router.push('/payments/' + issue.entity_id)
  }
}

function openIgnore(issue: ReconciliationIssue): void {
  ignoring.value = issue
  ignoreOpen.value = true
}

function openUnignore(issue: ReconciliationIssue): void {
  unignoring.value = issue
  unignoreOpen.value = true
}

async function confirmUnignore(): Promise<void> {
  const issue = unignoring.value
  if (!issue) return
  unignoreLoading.value = true
  try {
    await unignoreReconciliationIssue(issue.id)
    toast.success('已取消忽略')
    unignoreOpen.value = false
    unignoring.value = null
    reloadAll()
  } catch (caught) {
    toast.error(
      caught instanceof ApiError ? caught.message : '取消忽略失败，请稍后重试。',
    )
  } finally {
    unignoreLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader
      title="对账"
      description="核对开票、付款与分配之间的缺口，及时处理异常。"
    />

    <ReconciliationSummary
      :summary="summary"
      :loading="summaryLoading"
      :error="summaryError || null"
      :issue-count="issueCount"
      @retry="loadSummary"
    />

    <ReconciliationFilters
      :type="state.type"
      :include-ignored="state.include_ignored"
      @update:type="setType"
      @update:includeIgnored="setIncludeIgnored"
      @reset="resetFilters"
    />

    <div>
      <IssueTable
        :rows="issues"
        :loading="loading"
        :error="error || null"
        :is-admin="auth.isAdmin"
        @view="viewIssue"
        @ignore="openIgnore"
        @unignore="openUnignore"
        @retry="loadIssues"
      />
      <Pagination
        v-if="!loading && !error && total > 0"
        class="mt-3 rounded-card border border-border bg-surface"
        :page="state.page"
        :page-size="state.page_size"
        :total="total"
        @update:page="goToPage"
        @update:page-size="setPageSize"
      />
    </div>

    <IssueIgnoreDialog
      v-model:open="ignoreOpen"
      :issue="ignoring"
      @ignored="reloadAll"
    />

    <ConfirmDialog
      v-model:open="unignoreOpen"
      title="取消忽略"
      :consequence="
        unignoring
          ? '将恢复「' + unignoring.title + '」为待处理状态。'
          : '将恢复该问题为待处理状态。'
      "
      confirm-label="取消忽略"
      :loading="unignoreLoading"
      @confirm="confirmUnignore"
    />
  </div>
</template>
