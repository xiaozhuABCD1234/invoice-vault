<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Plus } from '@lucide/vue'

import type { Category, User } from '@/api/types'
import PageHeader from '@/components/common/PageHeader.vue'
import CategoryFormDialog from '@/components/admin/CategoryFormDialog.vue'
import CategoryTable from '@/components/admin/CategoryTable.vue'
import UserFilterBar from '@/components/admin/UserFilterBar.vue'
import UserFormDialog from '@/components/admin/UserFormDialog.vue'
import UserTable from '@/components/admin/UserTable.vue'
import Button from '@/components/ui/Button.vue'
import Tabs from '@/components/ui/Tabs.vue'
import { useAdminUsers } from '@/composables/useAdminUsers'
import { useCategories } from '@/composables/useCategories'
import { useUrlQuery } from '@/composables/useUrlQuery'
import { useAuthStore } from '@/stores/auth'

const url = useUrlQuery()
const auth = useAuthStore()

const tab = ref(
  url.readString('tab') === 'categories' ? 'categories' : 'users',
)
const tabItems = [
  { value: 'users', label: '用户' },
  { value: 'categories', label: '类别' },
]

watch(tab, () => {
  url.update({ tab: tab.value === 'categories' ? 'categories' : null })
})

const {
  q,
  role,
  isActive,
  page,
  pageSize,
  rows,
  total,
  loading: usersLoading,
  error: usersError,
  applyFilters,
  resetFilters,
  reload: reloadUsers,
} = useAdminUsers()

const {
  categories,
  loading: categoriesLoading,
  error: categoriesError,
  reload: reloadCategories,
} = useCategories()

const currentUserId = computed(() => auth.user?.id ?? null)

const userDialogOpen = ref(false)
const editingUser = ref<User | null>(null)
const categoryDialogOpen = ref(false)
const editingCategory = ref<Category | null>(null)

function openCreateUser(): void {
  editingUser.value = null
  userDialogOpen.value = true
}

function openEditUser(user: User): void {
  editingUser.value = user
  userDialogOpen.value = true
}

function openCreateCategory(): void {
  editingCategory.value = null
  categoryDialogOpen.value = true
}

function openEditCategory(category: Category): void {
  editingCategory.value = category
  categoryDialogOpen.value = true
}

function handleUserSaved(): void {
  reloadUsers()
}

function handleCategorySaved(): void {
  reloadCategories()
}
</script>

<template>
  <div>
    <PageHeader
      title="用户管理"
      description="管理账号、角色与类别，维护登录与分类基础数据。"
    >
      <template #actions>
        <Button v-if="tab === 'users'" @click="openCreateUser">
          <template #icon>
            <Plus :size="18" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建用户
        </Button>
        <Button v-else @click="openCreateCategory">
          <template #icon>
            <Plus :size="18" :stroke-width="1.75" aria-hidden="true" />
          </template>
          新建类别
        </Button>
      </template>
    </PageHeader>

    <Tabs v-model="tab" :items="tabItems">
      <template #users>
        <UserFilterBar
          v-model:q="q"
          v-model:role="role"
          v-model:active="isActive"
          @submit="applyFilters"
          @reset="resetFilters"
        />

        <div class="mt-4">
          <UserTable
            v-model:page="page"
            v-model:page-size="pageSize"
            :rows="rows"
            :loading="usersLoading"
            :error="usersError"
            :total="total"
            @edit="openEditUser"
            @create="openCreateUser"
            @retry="reloadUsers"
          />
        </div>
      </template>

      <template #categories>
        <CategoryTable
          :rows="categories"
          :loading="categoriesLoading"
          :error="categoriesError"
          @edit="openEditCategory"
          @create="openCreateCategory"
          @retry="reloadCategories"
        />
      </template>
    </Tabs>

    <UserFormDialog
      v-model:open="userDialogOpen"
      :user="editingUser"
      :current-user-id="currentUserId"
      @saved="handleUserSaved"
    />

    <CategoryFormDialog
      v-model:open="categoryDialogOpen"
      :category="editingCategory"
      @saved="handleCategorySaved"
    />
  </div>
</template>
