<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'

import {
  getExtractionSettings,
  listExtractionSettingsRevisions,
  resetExtractionSettings,
  rollbackExtractionSettings,
  updateExtractionSettings,
} from '@/api/settings'
import type {
  ExtractionSettings,
  ExtractionSettingsRevision,
  ExtractionSettingsUpdate,
} from '@/api/types'
import ExtractionSettingsForm from '@/components/admin/ExtractionSettingsForm.vue'
import SettingsHistoryTable from '@/components/admin/SettingsHistoryTable.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { apiErrorMessage } from '@/composables/useApiError'
import { formatDateTime } from '@/lib/date'

const settings = ref<ExtractionSettings | null>(null)
const revisions = ref<ExtractionSettingsRevision[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)
const historyLoading = ref(false)
const historyError = ref<string | null>(null)
const saving = ref(false)
const saveError = ref<string | null>(null)
const resetOpen = ref(false)
const resetting = ref(false)
const rollbackTarget = ref<ExtractionSettingsRevision | null>(null)
const rollingBack = ref(false)

const rollbackOpen = computed({
  get: () => rollbackTarget.value !== null,
  set: (value: boolean) => {
    if (!value) rollbackTarget.value = null
  },
})

const rollbackConsequence = computed(() => {
  const target = rollbackTarget.value
  if (!target) return ''
  return (
    '将把当前配置替换为 ' +
    formatDateTime(target.created_at) +
    ' 的版本（#' +
    target.id +
    '），并生成一条新的回滚记录。新任务立即生效。'
  )
})

async function loadSettings(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    settings.value = await getExtractionSettings()
  } catch (error) {
    loadError.value = apiErrorMessage(error, '识别设置加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function loadRevisions(): Promise<void> {
  historyLoading.value = true
  historyError.value = null
  try {
    const response = await listExtractionSettingsRevisions(20)
    revisions.value = response.items
  } catch (error) {
    historyError.value = apiErrorMessage(error, '变更历史加载失败，请稍后重试')
  } finally {
    historyLoading.value = false
  }
}

async function loadAll(): Promise<void> {
  await Promise.all([loadSettings(), loadRevisions()])
}

onMounted(loadAll)

async function handleSubmit(payload: ExtractionSettingsUpdate): Promise<void> {
  saving.value = true
  saveError.value = null
  try {
    settings.value = await updateExtractionSettings(payload)
    toast.success('识别设置已保存，新任务将使用新配置')
    await loadRevisions()
  } catch (error) {
    saveError.value = apiErrorMessage(error, '保存设置失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

async function confirmReset(): Promise<void> {
  resetting.value = true
  try {
    settings.value = await resetExtractionSettings()
    resetOpen.value = false
    toast.success('已恢复默认配置')
    await loadRevisions()
  } catch (error) {
    toast.error(apiErrorMessage(error, '恢复默认失败，请稍后重试'))
  } finally {
    resetting.value = false
  }
}

function openRollback(revision: ExtractionSettingsRevision): void {
  rollbackTarget.value = revision
}

async function confirmRollback(): Promise<void> {
  const target = rollbackTarget.value
  if (!target) return
  rollingBack.value = true
  try {
    settings.value = await rollbackExtractionSettings(target.id)
    rollbackTarget.value = null
    toast.success('已回滚到所选版本，新任务将使用该配置')
    await loadRevisions()
  } catch (error) {
    toast.error(apiErrorMessage(error, '回滚失败，请稍后重试'))
  } finally {
    rollingBack.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="识别设置"
      description="配置发票识别引擎与调用参数；改动写入数据库，可审计、可回滚。"
    />

    <div v-if="loading" class="max-w-3xl space-y-6" aria-busy="true">
      <Skeleton class="h-56 rounded-card" />
      <Skeleton class="h-40 rounded-card" />
      <Skeleton class="h-40 rounded-card" />
    </div>

    <div
      v-else-if="loadError || !settings"
      class="max-w-3xl rounded-card border border-border bg-surface"
    >
      <ErrorState
        title="识别设置加载失败"
        :message="loadError ?? '未获取到配置，请重试。'"
        @retry="loadAll"
      />
    </div>

    <div v-else class="max-w-3xl space-y-8">
      <p
        class="rounded-control border border-border bg-surface-muted px-4 py-3 text-meta text-text-secondary"
      >
        配置优先级：数据库覆盖层 &gt; 环境变量 &gt; backend/.env &gt;
        默认值。每个字段右上角标记当前值的来源；未重新填写的 API Key
        保持原值及其来源。
      </p>

      <ExtractionSettingsForm
        :settings="settings"
        :saving="saving"
        :error="saveError"
        @submit="handleSubmit"
        @reset="resetOpen = true"
      />

      <section aria-labelledby="settings-history-heading">
        <div class="mb-3">
          <h2
            id="settings-history-heading"
            class="text-heading font-semibold text-text"
          >
            变更历史
          </h2>
          <p class="mt-0.5 text-meta text-text-muted">
            最近 20 次保存、回滚与恢复默认记录，可回滚到任意历史版本。
          </p>
        </div>

        <SettingsHistoryTable
          :items="revisions"
          :loading="historyLoading"
          :error="historyError"
          @rollback="openRollback"
          @retry="loadRevisions"
        />
      </section>
    </div>

    <ConfirmDialog
      v-model:open="resetOpen"
      title="恢复默认配置"
      consequence="将删除数据库中的全部识别配置，回到环境变量与默认值；新任务立即生效，正在运行的任务不受影响。"
      confirm-label="恢复默认"
      :loading="resetting"
      @confirm="confirmReset"
    />

    <ConfirmDialog
      v-model:open="rollbackOpen"
      title="回滚配置"
      :consequence="rollbackConsequence"
      confirm-label="确认回滚"
      :loading="rollingBack"
      @confirm="confirmRollback"
    />
  </div>
</template>
