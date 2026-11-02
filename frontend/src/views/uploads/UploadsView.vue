<script setup lang="ts">
import { ref } from 'vue'
import { Upload } from '@lucide/vue'

import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Pagination from '@/components/ui/Pagination.vue'
import Select from '@/components/ui/Select.vue'
import DocumentPreviewDialog from '@/components/document/DocumentPreviewDialog.vue'
import DocumentTable from '@/components/document/DocumentTable.vue'
import DocumentUploadCard from '@/components/document/DocumentUploadCard.vue'
import { DOCUMENT_TYPE_FILTER_OPTIONS } from '@/components/document/document-utils'
import { useUploadsPage } from '@/composables/useUploadsPage'

const {
  isAdmin,
  filters,
  rows,
  total,
  loading,
  error,
  latestJobs,
  pageSizes,
  file,
  docType,
  title,
  submitting,
  uploadError,
  uploadOutcome,
  uploadDisabledReason,
  queryInput,
  previewOpen,
  previewTarget,
  deleteOpen,
  deleting,
  downloadingId,
  deleteConsequence,
  polling,
  pollError,
  reload,
  submitSearch,
  resetSearch,
  handleDocType,
  handlePage,
  handlePageSize,
  handleUpload,
  openPreview,
  handleDownload,
  askDelete,
  confirmDelete,
} = useUploadsPage()

const uploadSection = ref<HTMLElement | null>(null)

function scrollToUpload(): void {
  uploadSection.value?.scrollIntoView({ block: 'start' })
}
</script>

<template>
  <div>
    <PageHeader
      class="break-words"
      title="上传与识别"
      description="上传发票或付款凭证后自动识别，识别结果需人工审核。"
    />

    <div class="space-y-6">
      <section
        ref="uploadSection"
        class="scroll-mt-20"
        aria-label="上传文档"
      >
        <DocumentUploadCard
          v-model:file="file"
          v-model:doc-type="docType"
          v-model:title="title"
          :submitting="submitting"
          :upload-error="uploadError"
          :outcome="uploadOutcome"
          :polling="polling"
          :poll-error="pollError"
          :disabled="uploadDisabledReason !== ''"
          :disabled-reason="uploadDisabledReason"
          @submit="handleUpload"
        />
      </section>

      <section class="space-y-3" aria-labelledby="document-list-title">
        <div>
          <h2 id="document-list-title" class="text-section font-semibold text-text">
            文档列表
          </h2>
          <p class="mt-1 text-body text-text-secondary">
            筛选条件会同步到地址栏，刷新后保持。
          </p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <div class="w-full sm:w-40">
            <Select
              :model-value="filters.docType"
              :options="DOCUMENT_TYPE_FILTER_OPTIONS"
              aria-label="按文档类型筛选"
              @update:model-value="handleDocType"
            />
          </div>
          <div class="w-full sm:max-w-xs">
            <Input
              v-model="queryInput"
              placeholder="搜索文件名或标题"
              aria-label="按关键词搜索文档"
              @keydown.enter.prevent="submitSearch"
            />
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button variant="secondary" size="sm" @click="submitSearch">
              搜索
            </Button>
            <Button variant="ghost" size="sm" @click="resetSearch">
              重置
            </Button>
          </div>
        </div>

        <p class="text-meta text-text-muted xl:hidden">
          表格可左右滑动查看完整列与操作。
        </p>

        <DocumentTable
          :rows="rows"
          :latest-jobs="latestJobs"
          :loading="loading"
          :error="error"
          :is-admin="isAdmin"
          :downloading-id="downloadingId"
          @preview="openPreview"
          @download="handleDownload"
          @delete="askDelete"
          @retry="reload"
        >
          <template #empty-action>
            <Button variant="secondary" size="sm" @click="scrollToUpload">
              <template #icon>
                <Upload :size="16" :stroke-width="1.75" aria-hidden="true" />
              </template>
              上传文件
            </Button>
          </template>
        </DocumentTable>

        <Pagination
          v-if="total > 0 && !error"
          class="mt-3 rounded-card border border-border bg-surface"
          :page="filters.page"
          :page-size="filters.pageSize"
          :total="total"
          :page-sizes="pageSizes"
          @update:page="handlePage"
          @update:page-size="handlePageSize"
        />
      </section>
    </div>

    <DocumentPreviewDialog
      v-model:open="previewOpen"
      :document="previewTarget"
    />

    <ConfirmDialog
      v-model:open="deleteOpen"
      title="删除文档"
      :consequence="deleteConsequence"
      confirm-label="删除文档"
      :loading="deleting"
      @confirm="confirmDelete"
    />
  </div>
</template>
