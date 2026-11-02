<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Pencil } from '@lucide/vue'

import type { Allocation, Payment } from '@/api/types'
import Button from '@/components/ui/Button.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TableSkeleton from '@/components/common/TableSkeleton.vue'
import PaymentAllocationsPanel from '@/components/payment/PaymentAllocationsPanel.vue'
import PaymentEditDialog from '@/components/payment/PaymentEditDialog.vue'
import PaymentOverview from '@/components/payment/PaymentOverview.vue'
import {
  buildAllocationRows,
  type AllocationRow,
} from '@/components/payment/allocation'
import { usePaymentDetail } from '@/composables/usePaymentDetail'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const paymentId = computed(() => Number(route.params.id))

const {
  payment,
  invoices,
  loading,
  error,
  reload,
  applyUpdated,
} = usePaymentDetail(paymentId)

const canManagePayment = computed(() => {
  if (!payment.value) return false
  return (
    auth.isAdmin ||
    (auth.user !== null && payment.value.created_by === auth.user.id)
  )
})

function canManageAllocation(allocation: Allocation): boolean {
  if (!payment.value || allocation.status !== 'active') return false
  return (
    canManagePayment.value ||
    (auth.user !== null && allocation.created_by === auth.user.id)
  )
}

const allocationRows = computed<AllocationRow[]>(() =>
  buildAllocationRows(
    payment.value?.allocations ?? [],
    invoices.value,
    canManageAllocation,
  ),
)

const editingPayment = ref(false)

const headerTitle = computed(() =>
  payment.value ? '付款 #' + payment.value.id : '付款详情',
)

function onPaymentSaved(updated: Payment): void {
  applyUpdated(updated)
  reload()
}
</script>

<template>
  <div>
    <TableSkeleton v-if="loading" :rows="5" :columns="3" />

    <div v-else-if="error" class="rounded-card border border-border bg-surface">
      <ErrorState title="付款加载失败" :message="error" @retry="reload" />
    </div>

    <template v-else-if="payment">
      <PageHeader
        :title="headerTitle"
        description="查看付款信息、凭证与发票分配记录。"
        back-to="/payments"
        :breadcrumbs="[
          { label: '付款', to: '/payments' },
          { label: '#' + payment.id },
        ]"
      >
        <template #meta>
          <StatusBadge kind="payment_status" :status="payment.status" />
        </template>
        <template #actions>
          <Button
            v-if="canManagePayment"
            variant="secondary"
            @click="editingPayment = true"
          >
            <template #icon>
              <Pencil :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            编辑付款
          </Button>
        </template>
      </PageHeader>

      <div class="space-y-4">
        <PaymentOverview :payment="payment" />
        <PaymentAllocationsPanel
          :payment="payment"
          :rows="allocationRows"
          @changed="reload"
        />
      </div>

      <PaymentEditDialog
        v-if="canManagePayment"
        v-model:open="editingPayment"
        :payment="payment"
        @saved="onPaymentSaved"
      />
    </template>
  </div>
</template>
