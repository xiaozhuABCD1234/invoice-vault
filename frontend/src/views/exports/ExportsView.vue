<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus } from '@lucide/vue'
import { toast } from 'vue-sonner'

import { downloadExport } from '@/api/reports'
import type { ExportJob, ReportTemplate } from '@/api/types'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import Button from '@/components/ui/Button.vue'
import ExportCreateDialog from '@/components/report/ExportCreateDialog.vue'
import ExportTable from '@/components/report/ExportTable.vue'
import ReportTemplateDialog from '@/components/report/ReportTemplateDialog.vue'
import ReportTemplateTable from '@/components/report/ReportTemplateTable.vue'
import { exportFileName } from '@/components/report/report-fields'
import { apiErrorMessage } from '@/composables/useApiError'
import { useExports } from '@/composables/useExports'
import { useReportTemplates } from '@/composables/useReportTemplates'

const {
  templates,
  loading: templatesLoading,
  error: templatesError,
  deletingId,
  reload: reloadTemplates,
  removeTemplate,
} = useReportTemplates()

const {
  page,
  pageSize,
  rows,
  total,
  loading: exportsLoading,
  error: exportsError,
  reload: reloadExports,
  track,
} = useExports()

const templateDialogOpen = ref(false)
const editingTemplate = ref<ReportTemplate | null>(null)
const exportDialogOpen = ref(false)
const templateToDelete = ref<ReportTemplate | null>(null)
const confirmOpen = ref(false)
const downloadingId = ref<number | null>(null)

const deleteConsequence = computed(() =>
  templateToDelete.value
    ? `将删除模板「${templateToDelete.value.name}」，不可恢复；已创建的导出任务不受影响。`
    : '',
)

function openCreateTemplate(): void {
  editingTemplate.value = null
  templateDialogOpen.value = true
}

function openEditTemplate(template: ReportTemplate): void {
  editingTemplate.value = template
  templateDialogOpen.value = true
}

function requestDelete(template: ReportTemplate): void {
  templateToDelete.value = template
  confirmOpen.value = true
}

async function confirmDelete(): Promise<void> {
  const template = templateToDelete.value
  if (!template) return

  const removed = await removeTemplate(template.id)
  if (removed) {
    confirmOpen.value = false
    templateToDelete.value = null
  }
}

function handleTemplateSaved(): void {
  reloadTemplates()
}

function handleExportCreated(job: ExportJob): void {
  exportDialogOpen.value = false
  toast.success('导出任务已创建，正在生成')
  if (page.value !== 1) {
    page.value = 1
  } else {
    reloadExports()
  }
  track(job.id)
}

async function handleDownload(job: ExportJob): Promise<void> {
  downloadingId.value = job.id
  try {
    const blob = await downloadExport(job.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = exportFileName(job)
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    toast.success('导出文件已开始下载')
  } catch (error) {
    toast.error(apiErrorMessage(error, '下载失败，请稍后重试'))
  } finally {
    downloadingId.value = null
  }
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="导出"
      description="配置报表模板，异步生成并下载 xlsx。"
    >
      <template #actions>
        <Button @click="exportDialogOpen = true">
          <template #icon>
            <Plus :size="18" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建导出
        </Button>
      </template>
    </PageHeader>

    <section class="space-y-3">
      <div class="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-section font-semibold text-text">报表模板</h2>
          <p class="text-body text-text-secondary">
            模板保存列顺序与列名，内置模板不可修改。
          </p>
        </div>
        <Button variant="secondary" size="sm" @click="openCreateTemplate">
          <template #icon>
            <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建模板
        </Button>
      </div>

      <ReportTemplateTable
        :templates="templates"
        :loading="templatesLoading"
        :error="templatesError"
        :deleting-id="deletingId"
        @create="openCreateTemplate"
        @edit="openEditTemplate"
        @delete="requestDelete"
        @retry="reloadTemplates"
      />
    </section>

    <section class="space-y-3">
      <div>
        <h2 class="text-section font-semibold text-text">导出任务</h2>
        <p class="text-body text-text-secondary">
          导出在后台生成，成功后可在操作列下载；失败时显示原因。
        </p>
      </div>

      <ExportTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :rows="rows"
        :templates="templates"
        :loading="exportsLoading"
        :error="exportsError"
        :total="total"
        :downloading-id="downloadingId"
        @download="handleDownload"
        @create="exportDialogOpen = true"
        @retry="reloadExports"
      />
    </section>

    <ReportTemplateDialog
      v-model:open="templateDialogOpen"
      :template="editingTemplate"
      @saved="handleTemplateSaved"
    />

    <ExportCreateDialog
      v-model:open="exportDialogOpen"
      :templates="templates"
      @created="handleExportCreated"
    />

    <ConfirmDialog
      v-model:open="confirmOpen"
      title="删除报表模板"
      :consequence="deleteConsequence"
      confirm-label="删除模板"
      :loading="deletingId !== null"
      @confirm="confirmDelete"
    />
  </div>
</template>
