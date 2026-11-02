<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleAlert, FileText } from '@lucide/vue'
import { toast } from 'vue-sonner'

import { ApiError } from '@/api/client'
import Button from '@/components/ui/Button.vue'
import FormField from '@/components/ui/FormField.vue'
import Input from '@/components/ui/Input.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({
  username: '',
  password: '',
})

const errors = reactive({
  username: '',
  password: '',
})

const formError = ref('')
const submitting = ref(false)

const redirectTarget = computed(() => {
  const value = route.query.redirect
  if (
    typeof value === 'string' &&
    value.startsWith('/') &&
    !value.startsWith('//') &&
    value !== '/login' &&
    !value.startsWith('/login?')
  ) {
    return value
  }
  return '/dashboard'
})

watch(
  () => form.username,
  () => {
    if (errors.username) errors.username = ''
    if (formError.value) formError.value = ''
  },
)

watch(
  () => form.password,
  () => {
    if (errors.password) errors.password = ''
    if (formError.value) formError.value = ''
  },
)

function validate(): boolean {
  errors.username = form.username.trim() === '' ? '请输入用户名' : ''
  errors.password = form.password === '' ? '请输入密码' : ''
  return errors.username === '' && errors.password === ''
}

function resolveLoginError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) return '用户名或密码错误，请重试。'
    if (caught.status === 423) {
      return '连续登录失败次数过多，账号已被锁定，请稍后再试。'
    }
    if (caught.status === 0) return '无法连接到服务器，请检查网络后重试。'
    return caught.message
  }
  return '登录失败，请稍后重试。'
}

async function handleSubmit(): Promise<void> {
  if (submitting.value) return

  formError.value = ''
  if (!validate()) return

  submitting.value = true
  try {
    await auth.login({
      username: form.username.trim(),
      password: form.password,
    })
    toast.success('登录成功')
    await router.replace(redirectTarget.value)
  } catch (caught) {
    formError.value = resolveLoginError(caught)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-canvas p-6">
    <div class="w-full max-w-login rounded-card border border-border bg-surface p-8">
      <div class="mb-6 flex flex-col items-center text-center">
        <span
          class="mb-3 flex size-10 items-center justify-center rounded-control bg-primary-soft text-primary"
          aria-hidden="true"
        >
          <FileText :size="20" :stroke-width="1.75" />
        </span>
        <h1 class="text-section font-semibold tracking-heading text-text">
          发票管理系统
        </h1>
        <p class="mt-1 text-body text-text-secondary">内部财务票据工作台</p>
      </div>

      <div
        v-if="formError"
        class="mb-4 flex items-start gap-2 rounded-control border border-danger/30 bg-danger-soft px-3 py-2 text-body text-danger"
        role="alert"
        aria-live="assertive"
      >
        <CircleAlert
          class="mt-1 shrink-0"
          :size="18"
          :stroke-width="1.75"
          aria-hidden="true"
        />
        <span>{{ formError }}</span>
      </div>

      <form class="space-y-4" novalidate @submit.prevent="handleSubmit">
        <FormField
          id="login-username"
          label="用户名"
          required
          :error="errors.username"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              v-model="form.username"
              autocomplete="username"
              placeholder="请输入用户名"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="submitting"
              autofocus
            />
          </template>
        </FormField>

        <FormField
          id="login-password"
          label="密码"
          required
          :error="errors.password"
        >
          <template #default="{ id, invalid, describedBy }">
            <Input
              :id="id"
              v-model="form.password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              :invalid="invalid"
              :aria-describedby="describedBy"
              :disabled="submitting"
            />
          </template>
        </FormField>

        <Button
          type="submit"
          class="w-full"
          :loading="submitting"
        >
          登录
        </Button>
      </form>

      <p class="mt-6 text-center text-meta text-text-muted">
        如无账号，请联系管理员开通。
      </p>
    </div>
  </div>
</template>
