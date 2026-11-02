<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import type { Role, User, UserUpdate } from '@/api/types'
import { createUser, updateUser } from '@/api/users'
import Button from '@/components/ui/Button.vue'
import Dialog from '@/components/ui/Dialog.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import FormErrorAlert from './FormErrorAlert.vue'
import ToggleField from './ToggleField.vue'
import { ROLE_OPTIONS } from './admin-labels'
import { apiErrorMessage } from '@/composables/useApiError'

const props = withDefaults(
  defineProps<{
    user: User | null
    currentUserId?: number | null
  }>(),
  {
    currentUserId: null,
  },
)

const open = defineModel<boolean>('open', { default: false })

const emit = defineEmits<{
  (event: 'saved'): void
}>()

const username = ref('')
const displayName = ref('')
const password = ref('')
const role = ref('user')
const isActive = ref(true)

const saving = ref(false)
const formError = ref<string | null>(null)
const usernameError = ref('')
const displayNameError = ref('')
const passwordError = ref('')

const isEditing = computed(() => props.user !== null)
const isSelf = computed(
  () => props.user !== null && props.user.id === props.currentUserId,
)
const dialogTitle = computed(() => (isEditing.value ? '编辑用户' : '新建用户'))
const passwordHint = computed(() =>
  isEditing.value
    ? '留空表示不修改密码；填写时至少 8 位。'
    : '至少 8 位，用于首次登录。',
)

function resetForm(): void {
  username.value = props.user?.username ?? ''
  displayName.value = props.user?.display_name ?? ''
  password.value = ''
  role.value = props.user?.role ?? 'user'
  isActive.value = props.user?.is_active ?? true

  saving.value = false
  formError.value = null
  usernameError.value = ''
  displayNameError.value = ''
  passwordError.value = ''
}

watch(open, (value) => {
  if (value) resetForm()
})

watch(
  () => props.user?.id,
  () => {
    if (open.value) resetForm()
  },
)

function validate(): boolean {
  usernameError.value =
    !isEditing.value && username.value.trim() === '' ? '请填写用户名' : ''
  displayNameError.value =
    displayName.value.trim() === '' ? '请填写显示名' : ''
  passwordError.value =
    !isEditing.value && password.value === ''
      ? '请设置密码'
      : password.value !== '' && password.value.length < 8
        ? '密码至少 8 位'
        : ''

  return (
    usernameError.value === '' &&
    displayNameError.value === '' &&
    passwordError.value === ''
  )
}

async function submit(): Promise<void> {
  formError.value = null
  if (!validate()) return

  const selectedRole: Role = role.value === 'admin' ? 'admin' : 'user'
  saving.value = true

  try {
    if (props.user) {
      const payload: UserUpdate = {
        display_name: displayName.value.trim(),
        role: selectedRole,
        is_active: isActive.value,
      }
      if (password.value !== '') payload.password = password.value
      await updateUser(props.user.id, payload)
      toast.success('用户已更新')
    } else {
      await createUser({
        username: username.value.trim(),
        display_name: displayName.value.trim(),
        password: password.value,
        role: selectedRole,
      })
      toast.success('用户已创建')
    }

    open.value = false
    emit('saved')
  } catch (error) {
    formError.value = apiErrorMessage(error, '保存用户失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:open="open"
    :title="dialogTitle"
    description="账号由管理员创建，不开放注册。"
    :show-close="!saving"
  >
    <div class="space-y-4">
      <FormErrorAlert :message="formError" />

      <FormField
        v-if="!isEditing"
        id="user-username"
        label="用户名"
        required
        :error="usernameError"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="username"
            :invalid="invalid"
            :aria-describedby="describedBy"
            autocomplete="off"
            placeholder="登录用户名"
          />
        </template>
      </FormField>

      <FormField v-else id="user-username" label="用户名">
        <template #default="{ id }">
          <Input
            :id="id"
            :model-value="user?.username ?? ''"
            readonly
          />
        </template>
      </FormField>

      <FormField
        id="user-display-name"
        label="显示名"
        required
        :error="displayNameError"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="displayName"
            :invalid="invalid"
            :aria-describedby="describedBy"
            placeholder="例如：杨泽"
          />
        </template>
      </FormField>

      <FormField
        id="user-password"
        :label="isEditing ? '重置密码' : '密码'"
        :required="!isEditing"
        :error="passwordError"
        :hint="passwordHint"
      >
        <template #default="{ id, invalid, describedBy }">
          <Input
            :id="id"
            v-model="password"
            type="password"
            :invalid="invalid"
            :aria-describedby="describedBy"
            autocomplete="new-password"
          />
        </template>
      </FormField>

      <FormField id="user-role" label="角色" required>
        <template #default="{ id, describedBy }">
          <Select
            :id="id"
            v-model="role"
            :options="ROLE_OPTIONS"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>

      <ToggleField
        v-if="isEditing"
        id="user-active"
        v-model="isActive"
        label="启用账号"
        :description="
          isSelf
            ? '当前登录账号不能停用。'
            : '停用后该用户将无法登录，已有会话失效。'
        "
      />
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="saving" @click="open = false">
        取消
      </Button>
      <Button :loading="saving" @click="submit">
        {{ isEditing ? '保存用户' : '创建用户' }}
      </Button>
    </template>
  </Dialog>
</template>
