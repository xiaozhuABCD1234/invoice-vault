<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import type { ReportColumn, ReportTemplate } from '@/api/types'
import { createReportTemplate, updateReportTemplate } from '@/api/reports'
import FormErrorAlert from '@/components/admin/FormErrorAlert.vue'
import ToggleField from '@/components/admin/ToggleField.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import { apiErrorMessage } from '@/composables/useApiError'
import ReportColumnEditor from './ReportColumnEditor.vue'
import { createDefaultReportColumns } from './report-fields'

const props = defineProps<{
  template: ReportTemplate | null
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved'): void
}>()

const name = ref('')
const isShared = ref(false)
const columns = ref<ReportColumn[]>([])
const saving = ref(false)
const formError = ref<string | null>(null)
const nameError = ref('')
const columnsError = ref('')

const dialogTitle = computed(() =>
  props.template ? '编辑报表模板' : '新建报表模板',
)

function resetForm(): void {
  name.value = props.template?.name ?? ''
  isShared.value = props.template?.is_shared ?? false
  columns.value = props.template
    ? props.template.columns.map((column) => ({ ...column }))
    : createDefaultReportColumns()
  saving.value = false
  formError.value = null
  nameError.value = ''
  columnsError.value = ''
}

watch(open, (value) => {
  if (value) resetForm()
})

watch(
  () => props.template?.id,
  () => {
    if (open.value) resetForm()
  },
)

function validate(): boolean {
  nameError.value = name.value.trim() === '' ? '请填写模板名称' : ''
  columnsError.value =
    columns.value.length === 0
      ? '至少选择一列'
      : columns.value.some((column) => column.label.trim() === '')
        ? '列名不能为空'
        : ''
  return nameError.value === '' && columnsError.value === ''
}

async function submit(): Promise<void> {
  formError.value = null
  if (props.template?.id === 0) {
    formError.value = '内置模板不可编辑'
    return
  }
  if (!validate()) return

  saving.value = true
  try {
    const payload = {
      name: name.value.trim(),
      columns: columns.value.map((column) => ({
        ...column,
        label: column.label.trim(),
      })),
      filters: props.template?.filters,
      sort: props.template?.sort,
      is_shared: isShared.value,
    }

    if (props.template) {
      await updateReportTemplate(props.template.id, payload)
      toast.success('模板已更新')
    } else {
      await createReportTemplate(payload)
      toast.success('模板已创建')
    }

    open.value = false
    emit('saved')
  } catch (error) {
    formError.value = apiErrorMessage(error, '保存模板失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    :title="dialogTitle"
    description="选择导出列并调整顺序，列名可修改。"
    width="lg"
    :show-close="!saving"
  >
    <div class="space-y-5">
      <FormErrorAlert :message="formError" />

      <FormField
        id="report-template-name"
        label="模板名称"
        required
        :error="nameError"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="name"
            :invalid="invalid"
            :aria-describedby="describedBy"
            placeholder="例如：月度采购汇总"
          />
        </template>
      </FormField>

      <ToggleField
        id="report-template-shared"
        v-model="isShared"
        label="共享模板"
        description="共享后其他用户可以选用此模板。"
      />

      <ReportColumnEditor v-model="columns" :error="columnsError" />
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">
        {{ template ? '保存模板' : '创建模板' }}
      </Button>
    </template>
  </Dialog>
</template>
