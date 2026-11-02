<script setup lang="ts">
import { ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { CircleAlert } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { ignoreReconciliationIssue } from '@/api/reconciliation'
import type { ReconciliationIssue } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Textarea from '@/components/ui/Textarea.vue'

const props = defineProps<{
  issue: ReconciliationIssue | null
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'ignored'): void
}>()

const note = ref('')
const error = ref('')
const formError = ref('')
const saving = ref(false)

watch(open, (value) => {
  if (!value) return
  note.value = ''
  error.value = ''
  formError.value = ''
})

async function submit(): Promise<void> {
  if (!props.issue) return
  formError.value = ''
  if (note.value.trim() === '') {
    error.value = '请填写忽略原因，便于后续追溯。'
    return
  }
  error.value = ''

  saving.value = true
  try {
    await ignoreReconciliationIssue(props.issue.id, {
      note: note.value.trim(),
    })
    toast.success('问题已忽略')
    emit('ignored')
    open.value = false
  } catch (caught) {
    formError.value =
      caught instanceof ApiError ? caught.message : '忽略失败，请稍后重试。'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    title="忽略对账问题"
    description="忽略后问题仍保留在列表中，默认不再展示；需填写原因。"
    width="md"
  >
    <form class="space-y-4" novalidate @submit.prevent="submit">
      <div
        v-if="formError"
        class="flex items-start gap-2 rounded-control border border-danger bg-danger-soft p-3 text-body text-danger"
        role="alert"
      >
        <CircleAlert
          class="mt-1 shrink-0"
          :size="16"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>{{ formError }}</span>
      </div>

      <div v-if="issue" class="rounded-control border border-border bg-surface-muted p-3">
        <p class="text-body font-medium text-text">{{ issue.title }}</p>
        <p class="mt-1 line-clamp-3 text-meta text-text-secondary">
          {{ issue.detail || '—' }}
        </p>
      </div>

      <FormField
        id="issue-ignore-note"
        label="忽略原因"
        required
        :error="error"
      >
        <template #default="{ id, invalid, describedBy }">
          <Textarea
            :id="id"
            v-model="note"
            :rows="3"
            :invalid="invalid"
            :aria-describedby="describedBy"
            placeholder="例如：已线下确认，待补充凭证。"
          />
        </template>
      </FormField>
    </form>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">忽略问题</Button>
    </template>
  </Dialog>
</template>
