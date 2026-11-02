<script setup lang="ts">
import { Search } from '@lucide/vue'

import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { ROLE_FILTER_OPTIONS } from './admin-labels'

const q = defineModel<string>('q', { default: '' })
const role = defineModel<string>('role', { default: '' })
const active = defineModel<string>('active', { default: '' })

const emit = defineEmits<{
  (event: 'submit'): void
  (event: 'reset'): void
}>()

const activeOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'true', label: '已启用' },
  { value: 'false', label: '已停用' },
]
</script>

<template>
  <form
    class="rounded-card border border-border bg-surface p-4"
    @submit.prevent="emit('submit')"
  >
    <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
      <div class="w-full sm:w-64">
        <FormField id="user-filter-q" label="关键词">
          <template #default="{ id, describedBy }">
            <Input
              :id="id"
              v-model="q"
              type="search"
              :aria-describedby="describedBy"
              placeholder="用户名或显示名"
            />
          </template>
        </FormField>
      </div>

      <div class="w-full sm:w-40">
        <FormField id="user-filter-role" label="角色">
          <template #default="{ id, describedBy }">
            <Select
              :id="id"
              v-model="role"
              :options="ROLE_FILTER_OPTIONS"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <div class="w-full sm:w-36">
        <FormField id="user-filter-active" label="启用状态">
          <template #default="{ id, describedBy }">
            <Select
              :id="id"
              v-model="active"
              :options="activeOptions"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </div>

      <div class="flex items-center gap-2">
        <Button type="submit" variant="secondary">
          <template #icon>
            <Search :size="18" :stroke-width="1.75" aria-hidden="true" />
          </template>
          查询
        </Button>
        <Button variant="ghost" @click="emit('reset')">重置</Button>
      </div>
    </div>
  </form>
</template>
