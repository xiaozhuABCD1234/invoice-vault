<script setup lang="ts">
import { computed } from 'vue'

import type { Category, UserOption } from '@/api/types'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { parseYuanToCents } from '@/lib/money'

import ExtractionField from './ExtractionField.vue'
import ExtractionItemsEditor from './ExtractionItemsEditor.vue'
import type {
  InvoiceDraft,
  InvoiceDraftErrors,
} from './extraction-fields'
import { getFieldConfidence } from './extraction-fields'
import type { SelectOptionItem } from './document-utils'

const props = withDefaults(
  defineProps<{
    errors?: InvoiceDraftErrors
    fieldConfidence?: Record<string, number> | null
    categories?: Category[]
    users?: UserOption[]
    disabled?: boolean
    optionsLoading?: boolean
  }>(),
  {
    errors: () => ({}),
    fieldConfidence: null,
    categories: () => [],
    users: () => [],
    disabled: false,
    optionsLoading: false,
  },
)

const model = defineModel<InvoiceDraft>({ required: true })

type TextField =
  | 'invoiceNumber'
  | 'invoiceCode'
  | 'invoiceType'
  | 'issueDate'
  | 'sellerName'
  | 'sellerTaxId'
  | 'buyerName'
  | 'buyerTaxId'
  | 'amountExTax'
  | 'tax'
  | 'total'
  | 'taxRate'
  | 'note'
  | 'productUrl'

const INVOICE_FORM_OPTIONS: SelectOptionItem[] = [
  { value: 'electronic', label: '电子发票' },
  { value: 'paper', label: '纸质发票' },
]

const categoryOptions = computed<SelectOptionItem[]>(() =>
  props.categories.map((category) => ({
    value: String(category.id),
    label: category.name,
  })),
)

const userOptions = computed<SelectOptionItem[]>(() =>
  props.users.map((user) => ({
    value: String(user.id),
    label: user.is_active ? user.display_name : `${user.display_name}（已停用）`,
  })),
)

const itemsModel = computed({
  get: () => model.value.items,
  set: (items) => {
    model.value = { ...model.value, items }
  },
})

const selectDisabled = computed(
  () => props.disabled || props.optionsLoading,
)

const invoiceTotalCents = computed(() => parseYuanToCents(model.value.total))

const productUrlDescribedBy = computed(() => {
  const ids = ['review-product-url-hint']
  if (confidence('product_url', 'productUrl') !== null) {
    ids.push('review-product-url-confidence')
  }
  if (props.errors.productUrl) ids.push('review-product-url-error')
  return ids.join(' ')
})

function confidence(...keys: string[]): number | null {
  return getFieldConfidence(props.fieldConfidence, keys)
}

function updateText(key: TextField, value: string): void {
  model.value = { ...model.value, [key]: value }
}

function updateCategory(value: string): void {
  model.value = { ...model.value, categoryId: value }
}

function updateRequester(value: string): void {
  model.value = { ...model.value, requesterId: value }
}

function updateOwner(value: string): void {
  model.value = { ...model.value, ownerId: value }
}

function updateInvoiceForm(value: string): void {
  model.value = {
    ...model.value,
    invoiceForm: value === 'paper' ? 'paper' : 'electronic',
  }
}
</script>

<template>
  <div class="space-y-8">
    <section class="space-y-4" aria-labelledby="review-invoice-base-title">
      <h3 id="review-invoice-base-title" class="text-heading font-semibold text-text">
        发票信息
      </h3>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <ExtractionField
          id="review-invoice-number"
          label="发票号码"
          required
          :error="errors.invoiceNumber"
          :confidence="confidence('invoice_number', 'invoiceNumber')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.invoiceNumber"
              class="font-mono"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('invoiceNumber', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-invoice-code"
          label="发票代码"
          :error="errors.invoiceCode"
          :confidence="confidence('invoice_code', 'invoiceCode')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.invoiceCode"
              class="font-mono"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('invoiceCode', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-invoice-type"
          label="发票类型"
          :error="errors.invoiceType"
          :confidence="confidence('invoice_type', 'invoiceType')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.invoiceType"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('invoiceType', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-issue-date"
          label="开票日期"
          required
          hint="格式：YYYY-MM-DD。"
          :error="errors.issueDate"
          :confidence="confidence('issue_date', 'issueDate')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.issueDate"
              placeholder="YYYY-MM-DD"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('issueDate', $event)"
            />
          </template>
        </ExtractionField>
      </div>
    </section>

    <section class="space-y-4 border-t border-border pt-6" aria-labelledby="review-parties-title">
      <h3 id="review-parties-title" class="text-heading font-semibold text-text">
        购销双方
      </h3>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <ExtractionField
          id="review-seller-name"
          label="销方名称"
          required
          :error="errors.sellerName"
          :confidence="confidence('seller_name', 'sellerName')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.sellerName"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('sellerName', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-seller-tax-id"
          label="销方税号"
          :error="errors.sellerTaxId"
          :confidence="confidence('seller_tax_id', 'sellerTaxId')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.sellerTaxId"
              class="font-mono"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('sellerTaxId', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-buyer-name"
          label="购方名称"
          :error="errors.buyerName"
          :confidence="confidence('buyer_name', 'buyerName')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.buyerName"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('buyerName', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-buyer-tax-id"
          label="购方税号"
          :error="errors.buyerTaxId"
          :confidence="confidence('buyer_tax_id', 'buyerTaxId')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.buyerTaxId"
              class="font-mono"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('buyerTaxId', $event)"
            />
          </template>
        </ExtractionField>
      </div>
    </section>

    <section class="space-y-4 border-t border-border pt-6" aria-labelledby="review-amounts-title">
      <h3 id="review-amounts-title" class="text-heading font-semibold text-text">
        金额与分类
      </h3>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <ExtractionField
          id="review-amount-ex-tax"
          label="不含税金额（元）"
          required
          hint="最多两位小数，例如 1234.56。"
          :error="errors.amountExTax"
          :confidence="
            confidence(
              'amount_ex_tax_cents',
              'amountExTaxCents',
              'amount_ex_tax',
              'amountExTax',
            )
          "
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.amountExTax"
              inputmode="decimal"
              placeholder="0.00"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('amountExTax', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-tax"
          label="税额（元）"
          required
          hint="最多两位小数。"
          :error="errors.tax"
          :confidence="confidence('tax_cents', 'taxCents', 'tax')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.tax"
              inputmode="decimal"
              placeholder="0.00"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('tax', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-total"
          label="价税合计（元）"
          required
          hint="需等于不含税金额 + 税额，差额超过 1 分将无法提交。"
          :error="errors.total"
          :confidence="confidence('total_cents', 'totalCents', 'total')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.total"
              inputmode="decimal"
              placeholder="0.00"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('total', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-tax-rate"
          label="税率（%）"
          hint="按百分比填写，例如 13 表示 13%。"
          :error="errors.taxRate"
          :confidence="
            confidence('tax_rate_bp', 'taxRateBp', 'tax_rate', 'taxRate')
          "
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              :model-value="model.taxRate"
              inputmode="decimal"
              placeholder="13"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="disabled"
              @update:model-value="updateText('taxRate', $event)"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-category"
          label="类别"
          required
          :error="errors.categoryId"
          :confidence="confidence('category_id', 'categoryId')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Select
              :id="id"
              :model-value="model.categoryId"
              :options="categoryOptions"
              :placeholder="optionsLoading ? '选项加载中…' : '请选择类别'"
              :invalid="invalid"
              :disabled="selectDisabled"
              :aria-describedby="describedBy"
              @update:model-value="updateCategory"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-invoice-form"
          label="发票形式"
          :error="errors.invoiceForm"
          :confidence="confidence('invoice_form', 'invoiceForm')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Select
              :id="id"
              :model-value="model.invoiceForm"
              :options="INVOICE_FORM_OPTIONS"
              :invalid="invalid"
              :disabled="disabled"
              :aria-describedby="describedBy"
              @update:model-value="updateInvoiceForm"
            />
          </template>
        </ExtractionField>
      </div>
    </section>

    <section class="space-y-4 border-t border-border pt-6" aria-labelledby="review-ownership-title">
      <h3 id="review-ownership-title" class="text-heading font-semibold text-text">
        归属与补充
      </h3>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <ExtractionField
          id="review-requester"
          label="申购人"
          required
          :error="errors.requesterId"
          :confidence="confidence('requester_id', 'requesterId')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Select
              :id="id"
              :model-value="model.requesterId"
              :options="userOptions"
              :placeholder="optionsLoading ? '选项加载中…' : '请选择申购人'"
              :invalid="invalid"
              :disabled="selectDisabled"
              :aria-describedby="describedBy"
              @update:model-value="updateRequester"
            />
          </template>
        </ExtractionField>

        <ExtractionField
          id="review-owner"
          label="负责人"
          required
          :error="errors.ownerId"
          :confidence="confidence('owner_id', 'ownerId')"
        >
          <template #default="{ id, invalid, describedBy }">
            <Select
              :id="id"
              :model-value="model.ownerId"
              :options="userOptions"
              :placeholder="optionsLoading ? '选项加载中…' : '请选择负责人'"
              :invalid="invalid"
              :disabled="selectDisabled"
              :aria-describedby="describedBy"
              @update:model-value="updateOwner"
            />
          </template>
        </ExtractionField>

        <div class="sm:col-span-2 lg:col-span-1 xl:col-span-2">
          <ExtractionField
            id="review-note"
            label="备注"
            :error="errors.note"
            :confidence="confidence('note')"
          >
            <template #default="{ id, invalid, describedBy }">
              <Textarea
                :id="id"
                :model-value="model.note"
                :rows="3"
                :invalid="invalid"
                :aria-describedby="describedBy"
                :disabled="disabled"
                @update:model-value="updateText('note', $event)"
              />
            </template>
          </ExtractionField>
        </div>

        <div class="sm:col-span-2 lg:col-span-1 xl:col-span-2">
          <ExtractionField
            id="review-product-url"
            label="商品链接"
            hint="可选，填写发票对应的商品或订单链接。"
            :error="errors.productUrl"
            :confidence="confidence('product_url', 'productUrl')"
          >
            <template #default>
              <Input
                id="review-product-url"
                :model-value="model.productUrl"
                placeholder="https://"
                :invalid="Boolean(errors.productUrl)"
                :aria-describedby="productUrlDescribedBy"
                :disabled="disabled"
                @update:model-value="updateText('productUrl', $event)"
              />
            </template>
          </ExtractionField>
        </div>
      </div>
    </section>

    <section class="border-t border-border pt-6">
      <ExtractionItemsEditor
        v-model="itemsModel"
        :errors="errors"
        :disabled="disabled"
        :invoice-total-cents="invoiceTotalCents"
      />
    </section>
  </div>
</template>
