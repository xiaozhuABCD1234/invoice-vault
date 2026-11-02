<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import { emptyItemDraft, type InvoiceItemDraft } from './invoice-draft'

const items = defineModel<InvoiceItemDraft[]>('items', {
  default: () => [],
})

type ItemKey = keyof InvoiceItemDraft

function patch(index: number, key: ItemKey, value: string): void {
  items.value = items.value.map((item, itemIndex) =>
    itemIndex === index ? { ...item, [key]: value } : item,
  )
}

function addItem(): void {
  items.value = [...items.value, emptyItemDraft()]
}

function removeItem(index: number): void {
  items.value = items.value.filter((_, itemIndex) => itemIndex !== index)
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-heading font-semibold text-text">商品明细</h3>
      <Button variant="secondary" size="sm" @click="addItem">
        <template #icon>
          <Plus :size="16" :stroke-width="1.75" aria-hidden="true" />
        </template>
        添加明细
      </Button>
    </div>

    <p v-if="items.length === 0" class="text-body text-text-muted">
      暂无明细，可点击「添加明细」补充商品行。
    </p>

    <fieldset
      v-for="(item, index) in items"
      :key="index"
      class="rounded-card border border-border p-3"
    >
      <legend class="px-1 text-meta font-medium text-text-secondary">
        第 {{ index + 1 }} 行
      </legend>

      <div class="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <FormField :id="'item-name-' + index" label="名称" class="lg:col-span-2">
          <template #default="{ id }">
            <Input
              :id="id"
              :model-value="item.name"
              @update:model-value="patch(index, 'name', $event)"
            />
          </template>
        </FormField>

        <FormField :id="'item-quantity-' + index" label="数量">
          <template #default="{ id }">
            <Input
              :id="id"
              :model-value="item.quantity"
              inputmode="decimal"
              @update:model-value="patch(index, 'quantity', $event)"
            />
          </template>
        </FormField>

        <FormField :id="'item-unit-price-' + index" label="单价（元）">
          <template #default="{ id }">
            <Input
              :id="id"
              :model-value="item.unitPrice"
              inputmode="decimal"
              @update:model-value="patch(index, 'unitPrice', $event)"
            />
          </template>
        </FormField>

        <FormField :id="'item-amount-' + index" label="金额（元）">
          <template #default="{ id }">
            <Input
              :id="id"
              :model-value="item.amount"
              inputmode="decimal"
              @update:model-value="patch(index, 'amount', $event)"
            />
          </template>
        </FormField>

        <FormField
          :id="'item-note-' + index"
          label="备注"
          class="lg:col-span-5"
        >
          <template #default="{ id }">
            <Input
              :id="id"
              :model-value="item.note"
              @update:model-value="patch(index, 'note', $event)"
            />
          </template>
        </FormField>
      </div>

      <div class="mt-2 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          :aria-label="'移除第 ' + (index + 1) + ' 行明细'"
          @click="removeItem(index)"
        >
          <template #icon>
            <Trash2 :size="16" :stroke-width="1.75" aria-hidden="true" />
          </template>
          移除
        </Button>
      </div>
    </fieldset>
  </div>
</template>
