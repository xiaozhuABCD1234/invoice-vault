<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { Plus } from '@lucide/vue'

import { ApiError } from '@/api/client'
import { deleteAllocation } from '@/api/payments'
import type { Allocation, Payment } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { formatCents } from '@/lib/money'
import AllocationDialog from './AllocationDialog.vue'
import AllocationTable from './AllocationTable.vue'
import type { AllocationRow } from './allocation'

defineProps<{
  payment: Payment
  rows: AllocationRow[]
}>()

const emit = defineEmits<{
  (event: 'changed'): void
}>()

const editing = ref<Allocation | null>(null)
const dialogOpen = ref(false)
const reversing = ref<AllocationRow | null>(null)
const reverseOpen = ref(false)
const reverseLoading = ref(false)

function openCreate(): void {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(row: AllocationRow): void {
  editing.value = row
  dialogOpen.value = true
}

function openReverse(row: AllocationRow): void {
  reversing.value = row
  reverseOpen.value = true
}

function onSaved(): void {
  emit('changed')
}

async function confirmReverse(): Promise<void> {
  const target = reversing.value
  if (!target) return
  reverseLoading.value = true
  try {
    await deleteAllocation(target.id)
    toast.success('分配已撤销')
    reverseOpen.value = false
    reversing.value = null
    emit('changed')
  } catch (caught) {
    toast.error(
      caught instanceof ApiError ? caught.message : '撤销失败，请稍后重试。',
    )
  } finally {
    reverseLoading.value = false
  }
}
</script>

<template>
  <section
    class="rounded-card border border-border bg-surface p-4 md:p-6"
    aria-labelledby="payment-allocations-title"
  >
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h2
        id="payment-allocations-title"
        class="text-heading font-semibold text-text"
      >
        分配记录
      </h2>
      <Button
        v-if="payment.status !== 'void'"
        variant="secondary"
        size="sm"
        @click="openCreate"
      >
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        新增分配
      </Button>
    </div>

    <AllocationTable
      :rows="rows"
      @edit="openEdit"
      @reverse="openReverse"
    />

    <AllocationDialog
      v-if="dialogOpen"
      v-model:open="dialogOpen"
      :payment="payment"
      :mode="editing ? 'edit' : 'create'"
      :allocation="editing"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-model:open="reverseOpen"
      title="撤销分配"
      :consequence="
        reversing
          ? '将撤销该分配（' + formatCents(reversing.amount_cents) + '），并重算付款与发票的已分配金额，不可恢复。'
          : '将撤销该分配并重算金额，不可恢复。'
      "
      confirm-label="撤销分配"
      :loading="reverseLoading"
      @confirm="confirmReverse"
    />
  </section>
</template>
