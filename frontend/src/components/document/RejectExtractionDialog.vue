<script setup lang="ts">
import { ref, watch } from 'vue'
import { CircleAlert } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Textarea from '@/components/ui/Textarea.vue'

const props = withDefaults(
  defineProps<{
    loading?: boolean
    error?: string
    documentName?: string
  }>(),
  {
    loading: false,
    error: '',
    documentName: '',
  },
)

const open = defineModel<boolean>('open', { default: false })
const note = ref('')
const noteError = ref('')

const emit = defineEmits<{
  (event: 'confirm', note: string): void
}>()

watch(open, (value) => {
  if (value) {
    note.value = ''
    noteError.value = ''
  }
})

watch(note, () => {
  if (noteError.value) noteError.value = ''
})

function cancel(): void {
  if (props.loading) return
  open.value = false
}

function confirm(): void {
  if (props.loading) return
  const value = note.value.trim()
  if (value === '') {
    noteError.value = '请填写驳回原因。'
    return
  }
  noteError.value = ''
  emit('confirm', value)
}
</script>

<template>
  <Dialog
    v-model:open="open"
    title="驳回识别结果"
    :description="
      documentName
        ? `驳回「${documentName}」的识别结果，需重新识别后才能再次审核。`
        : '驳回后该任务将标记为已驳回，需重新识别后才能再次审核。'
    "
    width="md"
    :show-close="!loading"
  >
    <div class="space-y-4">
      <div
        v-if="error"
        class="flex items-start gap-2 break-words rounded-control border border-danger/30 bg-danger-soft px-3 py-2 text-body text-danger"
        role="alert"
      >
        <CircleAlert
          class="mt-1 shrink-0"
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>{{ error }}</span>
      </div>

      <FormField
        id="review-reject-note"
        label="驳回原因"
        required
        hint="将记录到审核备注，方便后续追溯。"
        :error="noteError"
      >
        <template #default="{ id, invalid, describedBy }">
          <Textarea
            :id="id"
            v-model="note"
            :rows="4"
            placeholder="请说明驳回原因，例如：发票号码识别错误、金额与票面不符。"
            :invalid="invalid"
            :aria-describedby="describedBy"
            :disabled="loading"
            autofocus
          />
        </template>
      </FormField>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="loading" @click="cancel">
        取消
      </Button>
      <Button variant="danger" :loading="loading" @click="confirm">
        确认驳回
      </Button>
    </template>
  </Dialog>
</template>
