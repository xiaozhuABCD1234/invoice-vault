<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Loader2, RotateCw, TriangleAlert } from '@lucide/vue'
import { toast } from 'vue-sonner'

import { retryExtractionJob } from '@/api/extraction'
import type { ExtractionJob } from '@/api/types'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/ui/Button.vue'
import Pagination from '@/components/ui/Pagination.vue'
import Select from '@/components/ui/Select.vue'
import { apiErrorMessage, JOB_STATUS_OPTIONS, PROVIDER_FILTER_OPTIONS } from '@/components/document/document-utils'
import ReviewQueueTable from '@/components/document/ReviewQueueTable.vue'
import { useReviewQueue } from '@/composables/useReviewQueue'

const router = useRouter()

const {
  filters,
  rows,
  total,
  loading,
  error,
  pollError,
  polling,
  pageSizes,
  load,
  refresh,
  setStatus,
  setProvider,
  setPage,
  setPageSize,
  resetFilters,
} = useReviewQueue()

const retryingId = ref<number | null>(null)

async function handleRetry(job: ExtractionJob): Promise<void> {
  if (retryingId.value !== null) return

  retryingId.value = job.id
  try {
    await retryExtractionJob(job.id)
    toast.success('已重新排队，将自动刷新识别状态。')
    refresh()
  } catch (caught) {
    toast.error(apiErrorMessage(caught, '重试失败，请稍后重试。'))
  } finally {
    retryingId.value = null
  }
}

function openUploads(): void {
  void router.push({ name: 'uploads' })
}
</script>

<template>
  <div>
    <PageHeader
      class="break-words"
      title="审核队列"
      description="查看自动识别结果，核对字段后完成审核。"
    >
      <template #actions>
        <Button
          variant="secondary"
          size="sm"
          :loading="loading"
          @click="refresh"
        >
          <template #icon>
            <RotateCw :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          刷新
        </Button>
      </template>
    </PageHeader>

    <section class="mt-0 space-y-3" aria-labelledby="review-list-title">
      <div>
        <h2 id="review-list-title" class="text-section font-semibold text-text">
          识别任务
        </h2>
        <p class="mt-1 text-body text-text-secondary">
          默认展示待审核任务，筛选条件会同步到地址栏。
        </p>
      </div>

      <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div class="w-full sm:w-40">
          <Select
            :model-value="filters.status"
            :options="JOB_STATUS_OPTIONS"
            aria-label="按任务状态筛选"
            @update:model-value="setStatus"
          />
        </div>
        <div class="w-full sm:w-48">
          <Select
            :model-value="filters.provider"
            :options="PROVIDER_FILTER_OPTIONS"
            aria-label="按识别器筛选"
            @update:model-value="setProvider"
          />
        </div>
        <Button
          variant="ghost"
          size="sm"
          class="self-start"
          @click="resetFilters"
        >
          重置
        </Button>

        <p
          v-if="polling"
          class="inline-flex items-center gap-1 self-start text-meta text-info sm:ml-auto"
          role="status"
        >
          <Loader2
            class="animate-spin"
            :size="16"
            :stroke-width="1.75"
            aria-hidden="true"
          />
          自动刷新中（每 5 秒）
        </p>
      </div>

      <div
        v-if="pollError"
        class="flex flex-wrap items-center gap-2 break-words rounded-control border border-warning/40 bg-warning-soft px-3 py-2 text-body text-warning"
        role="status"
      >
        <TriangleAlert
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>自动刷新已暂停：{{ pollError }}</span>
        <Button variant="secondary" size="sm" @click="refresh">
          立即刷新
        </Button>
      </div>

      <p class="text-meta text-text-muted wide:hidden">
        表格可左右滑动查看完整列与操作。
      </p>

      <ReviewQueueTable
        :rows="rows"
        :loading="loading"
        :error="error"
        :retrying-id="retryingId"
        @retry="handleRetry"
        @reload="load()"
      >
        <template #empty-action>
          <Button variant="secondary" size="sm" @click="openUploads">
            上传发票
          </Button>
        </template>
      </ReviewQueueTable>

      <Pagination
        v-if="total > 0 && !error"
        class="mt-3 rounded-card border border-border bg-surface"
        :page="filters.page"
        :page-size="filters.pageSize"
        :total="total"
        :page-sizes="pageSizes"
        @update:page="setPage"
        @update:page-size="setPageSize"
      />
    </section>
  </div>
</template>
