<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import type { Category, CategoryKind } from '@/api/types'
import { createCategory, updateCategory } from '@/api/categories'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import FormErrorAlert from './FormErrorAlert.vue'
import ToggleField from './ToggleField.vue'
import { CATEGORY_KIND_OPTIONS } from './admin-labels'
import { apiErrorMessage } from '@/composables/useApiError'

const props = defineProps<{
  category: Category | null
}>()

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved'): void
}>()

const name = ref('')
const kind = ref('purchase')
const sortOrder = ref('0')
const isActive = ref(true)

const saving = ref(false)
const formError = ref<string | null>(null)
const nameError = ref('')
const sortError = ref('')

const isEditing = computed(() => props.category !== null)
const dialogTitle = computed(() =>
  isEditing.value ? '编辑类别' : '新建类别',
)

function resetForm(): void {
  name.value = props.category?.name ?? ''
  kind.value = props.category?.kind ?? 'purchase'
  sortOrder.value = String(props.category?.sort_order ?? 0)
  isActive.value = props.category?.is_active ?? true

  saving.value = false
  formError.value = null
  nameError.value = ''
  sortError.value = ''
}

watch(open, (value) => {
  if (value) resetForm()
})

watch(
  () => props.category?.id,
  () => {
    if (open.value) resetForm()
  },
)

function validate(): boolean {
  nameError.value = name.value.trim() === '' ? '请填写类别名称' : ''

  const parsed = sortOrder.value.trim() === '' ? 0 : Number(sortOrder.value)
  sortError.value =
    !Number.isInteger(parsed) || parsed < 0
      ? '排序需为不小于 0 的整数'
      : ''

  return nameError.value === '' && sortError.value === ''
}

async function submit(): Promise<void> {
  formError.value = null
  if (!validate()) return

  const selectedKind: CategoryKind =
    kind.value === 'expense' ? 'expense' : 'purchase'
  const sortValue = sortOrder.value.trim() === '' ? 0 : Number(sortOrder.value)

  saving.value = true
  try {
    if (props.category) {
      await updateCategory(props.category.id, {
        name: name.value.trim(),
        sort_order: sortValue,
        is_active: isActive.value,
      })
      toast.success('类别已更新')
    } else {
      await createCategory({
        name: name.value.trim(),
        kind: selectedKind,
        sort_order: sortValue,
      })
      toast.success('类别已创建')
    }

    open.value = false
    emit('saved')
  } catch (error) {
    formError.value = apiErrorMessage(error, '保存类别失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    :title="dialogTitle"
    description="类别用于发票分类，采购与费用分开维护。"
    :show-close="!saving"
  >
    <div class="space-y-4">
      <FormErrorAlert :message="formError" />

      <FormField
        id="category-name"
        label="名称"
        required
        :error="nameError"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="name"
            :invalid="invalid"
            :aria-describedby="describedBy"
            placeholder="例如：标准件"
          />
        </template>
      </FormField>

      <FormField
        id="category-kind"
        label="类型"
        required
        :hint="isEditing ? '类别类型创建后不可修改。' : ''"
      >
        <template #default="{ id, describedBy }">
          <Select
            :id="id"
            v-model="kind"
            :options="CATEGORY_KIND_OPTIONS"
            :aria-describedby="describedBy"
            :disabled="isEditing"
          />
        </template>
      </FormField>

      <FormField
        id="category-sort"
        label="排序"
        :error="sortError"
        hint="数字越小越靠前。"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="sortOrder"
            type="text"
            inputmode="numeric"
            :invalid="invalid"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>

      <ToggleField
        v-if="isEditing"
        id="category-active"
        v-model="isActive"
        label="启用类别"
        description="停用后不会出现在新建发票的类别选择中。"
      />
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">
        {{ isEditing ? '保存类别' : '创建类别' }}
      </Button>
    </template>
  </Dialog>
</template>
