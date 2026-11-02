<script setup lang="ts">
import { computed, nextTick } from 'vue'
import { Plus, Trash2, TriangleAlert } from '@lucide/vue'

import EmptyState from '@/components/common/EmptyState.vue'
import MoneyText from '@/components/common/MoneyText.vue'
import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import type {
  InvoiceDraftErrors,
  InvoiceItemDraft,
} from './extraction-fields'
import {
  createEmptyItemDraft,
  itemFieldError,
  sumItemAmountCents,
} from './extraction-fields'

const props = withDefaults(
  defineProps<{
    errors?: InvoiceDraftErrors
    disabled?: boolean
    invoiceTotalCents?: number | null
  }>(),
  {
    errors: () => ({}),
    disabled: false,
    invoiceTotalCents: null,
  },
)

const items = defineModel<InvoiceItemDraft[]>({ required: true })

const itemsTotalCents = computed(() => sumItemAmountCents(items.value))
const differenceCents = computed(() =>
  props.invoiceTotalCents === null
    ? null
    : itemsTotalCents.value - props.invoiceTotalCents,
)
const hasMismatch = computed(
  () =>
    differenceCents.value !== null &&
    Math.abs(differenceCents.value) > 1,
)

function addItem(): void {
  items.value = [...items.value, createEmptyItemDraft()]
  void nextTick(() => {
    const input = document.getElementById(
      `review-item-${items.value.length - 1}-name`,
    )
    input?.focus()
  })
}

function removeItem(index: number): void {
  items.value = items.value.filter((_, current) => current !== index)
}

function updateItem<K extends keyof InvoiceItemDraft>(
  index: number,
  key: K,
  value: InvoiceItemDraft[K],
): void {
  items.value = items.value.map((item, current) =>
    current === index ? { ...item, [key]: value } : item,
  )
}

type ItemField = 'name' | 'quantity' | 'unitPrice' | 'amount'

function fieldError(index: number, field: ItemField): string {
  return itemFieldError(props.errors, index, field)
}
</script>

<template>
  <section class="space-y-4" aria-labelledby="review-items-title">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 id="review-items-title" class="text-heading font-semibold text-text">
          发票明细
        </h3>
        <p class="mt-1 text-body text-text-secondary">
          金额按元填写，明细合计与发票价税合计不一致时需人工核对。
        </p>
      </div>
      <Button
        variant="secondary"
        size="sm"
        :disabled="disabled"
        @click="addItem"
      >
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        添加明细
      </Button>
    </div>

    <p
      v-if="errors.items"
      class="text-meta text-danger"
      role="alert"
    >
      {{ errors.items }}
    </p>

    <div
      v-if="items.length === 0"
      id="review-items"
      tabindex="-1"
      class="rounded-control border border-dashed border-border-strong"
    >
      <EmptyState
        title="暂无发票明细"
        description="审核通过前至少添加一行明细，名称、数量、单价和金额需填写完整。"
      >
        <template #action>
          <Button
            variant="secondary"
            size="sm"
            :disabled="disabled"
            @click="addItem"
          >
            添加明细
          </Button>
        </template>
      </EmptyState>
    </div>

    <div v-else id="review-items" class="space-y-4" tabindex="-1">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="rounded-control border border-border p-4"
      >
        <div class="mb-3 flex items-center justify-between gap-2">
          <p class="text-body font-medium text-text">
            明细 {{ index + 1 }}
          </p>
          <Button
            variant="ghost"
            size="sm"
            class="text-danger hover:bg-danger-soft hover:text-danger"
            :disabled="disabled"
            :aria-label="`删除第 ${index + 1} 行明细`"
            @click="removeItem(index)"
          >
            <template #icon>
              <Trash2 :size="16" :stroke-width="1.75" aria-hidden="true" />
            </template>
            删除
          </Button>
        </div>

        <div class="grid gap-3 xl:grid-cols-2">
          <FormField
            :id="`review-item-${index}-name`"
            label="名称"
            required
            :error="fieldError(index, 'name')"
          >
            <template #default="{ id, invalid, describedBy }">
              <Input
                :id="id"
                :model-value="item.name"
                :invalid="invalid"
                :aria-describedby="describedBy"
                :disabled="disabled"
                @update:model-value="updateItem(index, 'name', $event)"
              />
            </template>
          </FormField>

          <FormField
            :id="`review-item-${index}-quantity`"
            label="数量"
            required
            :error="fieldError(index, 'quantity')"
          >
            <template #default="{ id, invalid, describedBy }">
              <Input
                :id="id"
                :model-value="item.quantity"
                inputmode="decimal"
                :invalid="invalid"
                :aria-describedby="describedBy"
                :disabled="disabled"
                @update:model-value="updateItem(index, 'quantity', $event)"
              />
            </template>
          </FormField>

          <FormField
            :id="`review-item-${index}-unit-price`"
            label="单价（元）"
            required
            :error="fieldError(index, 'unitPrice')"
          >
            <template #default="{ id, invalid, describedBy }">
              <Input
                :id="id"
                :model-value="item.unitPrice"
                inputmode="decimal"
                placeholder="0.00"
                :invalid="invalid"
                :aria-describedby="describedBy"
                :disabled="disabled"
                @update:model-value="updateItem(index, 'unitPrice', $event)"
              />
            </template>
          </FormField>

          <FormField
            :id="`review-item-${index}-amount`"
            label="金额（元）"
            required
            :error="fieldError(index, 'amount')"
          >
            <template #default="{ id, invalid, describedBy }">
              <Input
                :id="id"
                :model-value="item.amount"
                inputmode="decimal"
                placeholder="0.00"
                :invalid="invalid"
                :aria-describedby="describedBy"
                :disabled="disabled"
                @update:model-value="updateItem(index, 'amount', $event)"
              />
            </template>
          </FormField>

          <div class="xl:col-span-2">
            <FormField
              :id="`review-item-${index}-note`"
              label="备注"
            >
              <template #default="{ id, invalid, describedBy }">
                <Textarea
                  :id="id"
                  :model-value="item.note"
                  :rows="2"
                  :invalid="invalid"
                  :aria-describedby="describedBy"
                  :disabled="disabled"
                  @update:model-value="updateItem(index, 'note', $event)"
                />
              </template>
            </FormField>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-2 rounded-control border border-border bg-surface-muted px-4 py-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-body text-text-secondary">明细合计</span>
        <MoneyText :cents="itemsTotalCents" strong />
      </div>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-body text-text-secondary">发票价税合计</span>
        <MoneyText :cents="invoiceTotalCents" strong />
      </div>

      <p
        v-if="hasMismatch && differenceCents !== null"
        class="flex flex-wrap items-center gap-1 text-body text-warning"
        role="status"
      >
        <TriangleAlert
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>明细合计与发票价税合计相差</span>
        <MoneyText
          :cents="Math.abs(differenceCents)"
          align="left"
          class="text-warning"
        />
        <span>，审核通过前请核对。</span>
      </p>
    </div>
  </section>
</template>
