<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  ExportJob,
  InvoicePaymentStatus,
  InvoiceStatus,
  ReportFilters,
  ReportTemplate,
} from '@/api/types'
import { createExport } from '@/api/reports'
import FormErrorAlert from '@/components/admin/FormErrorAlert.vue'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { apiErrorMessage } from '@/composables/useApiError'

const props = defineProps<{
  templates: ReportTemplate[]
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'created', job: ExportJob): void
}>()

const ALL = 'all'

const templateId = ref('')
const status = ref(ALL)
const paymentStatus = ref(ALL)
const dateFrom = ref('')
const dateTo = ref('')
const saving = ref(false)
const formError = ref<string | null>(null)
const templateError = ref('')
const dateError = ref('')

const templateOptions = computed(() =>
  props.templates.map((template) => ({
    value: String(template.id),
    label: template.id === 0 ? `${template.name}（内置）` : template.name,
  })),
)

const statusOptions = [
  { value: ALL, label: '全部状态' },
  { value: 'active', label: '已生效' },
  { value: 'review_pending', label: '待审核' },
  { value: 'void', label: '已作废' },
  { value: 'duplicate', label: '重复' },
]

const paymentStatusOptions = [
  { value: ALL, label: '全部付款状态' },
  { value: 'unpaid', label: '未付款' },
  { value: 'partial', label: '部分付款' },
  { value: 'paid', label: '已付款' },
]

function resetForm(): void {
  const firstTemplate = props.templates[0]
  templateId.value = firstTemplate ? String(firstTemplate.id) : ''
  status.value = ALL
  paymentStatus.value = ALL
  dateFrom.value = ''
  dateTo.value = ''
  saving.value = false
  formError.value = null
  templateError.value = ''
  dateError.value = ''
}

watch(open, (value) => {
  if (value) resetForm()
})

watch(
  () => props.templates,
  (templates) => {
    if (!open.value) return
    if (templateId.value === '' && templates.length > 0) {
      const first = templates[0]
      if (first) templateId.value = String(first.id)
    }
  },
  { immediate: true },
)

function validate(): boolean {
  templateError.value = templateId.value === '' ? '请选择导出模板' : ''
  dateError.value =
    dateFrom.value !== '' &&
    dateTo.value !== '' &&
    dateFrom.value > dateTo.value
      ? '开始日期不能晚于结束日期'
      : ''
  return templateError.value === '' && dateError.value === ''
}

async function submit(): Promise<void> {
  formError.value = null
  if (!validate()) return

  const filters: ReportFilters = {}
  if (status.value !== ALL) filters.status = status.value as InvoiceStatus
  if (paymentStatus.value !== ALL) {
    filters.payment_status = paymentStatus.value as InvoicePaymentStatus
  }
  if (dateFrom.value !== '') filters.date_from = dateFrom.value
  if (dateTo.value !== '') filters.date_to = dateTo.value

  saving.value = true
  try {
    const response = await createExport({
      template_id: Number(templateId.value),
      filters: Object.keys(filters).length > 0 ? filters : undefined,
    })
    open.value = false
    emit('created', response.export)
  } catch (error) {
    formError.value = apiErrorMessage(error, '创建导出任务失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    title="新建导出"
    description="选择模板和可选筛选条件，任务将在后台生成 xlsx。"
    :show-close="!saving"
  >
    <div class="space-y-4">
      <FormErrorAlert :message="formError" />

      <FormField
        id="export-template"
        label="导出模板"
        required
        :error="templateError"
        :hint="
          templates.length === 0
            ? '请先在模板区新建模板。'
            : '内置模板与共享模板均可使用。'
        "
      >
        <template #default="{ id, invalid, describedBy }">
          <Select
            :id="id"
            v-model="templateId"
            :options="templateOptions"
            :invalid="invalid"
            :aria-describedby="describedBy"
            :disabled="templates.length === 0"
            placeholder="请选择模板"
          />
        </template>
      </FormField>

      <div class="grid gap-4 sm:grid-cols-2">
        <FormField id="export-status" label="发票状态">
          <template #default="{ id, describedBy }">
            <Select
              :id="id"
              v-model="status"
              :options="statusOptions"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="export-payment-status" label="付款状态">
          <template #default="{ id, describedBy }">
            <Select
              :id="id"
              v-model="paymentStatus"
              :options="paymentStatusOptions"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <FormField id="export-date-from" label="开始日期">
          <template #default="{ id, describedBy }">
            <Input
              :id="id"
              v-model="dateFrom"
              type="date"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="export-date-to" label="结束日期">
          <template #default="{ id, describedBy }">
            <Input
              :id="id"
              v-model="dateTo"
              type="date"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <p v-if="dateError" class="text-meta text-danger" role="alert" aria-live="polite">
        {{ dateError }}
      </p>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button
        :loading="saving"
        :disabled="templates.length === 0"
        @click="submit"
      >
        创建导出
      </Button>
    </template>
  </Dialog>
</template>
