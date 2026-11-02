import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  login as loginRequest,
  logout as logoutRequest,
  me as fetchMeRequest,
  refresh as refreshRequest,
} from '@/api/auth'
import { setAccessToken, setAccessTokenListener } from '@/api/client'
import type { LoginRequest, RefreshResponse, User } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const initialized = ref(false)

  let restorePromise: Promise<void> | null = null

  // 自动 refresh 在 client 内部完成，这里同步 store 中的内存 token。
  setAccessTokenListener((token) => {
    accessToken.value = token
    if (token === null) user.value = null
  })

  const isAuthenticated = computed(
    () => user.value !== null && accessToken.value !== null,
  )
  const isAdmin = computed(() => user.value?.role === 'admin')

  function applyToken(token: string): void {
    accessToken.value = token
    setAccessToken(token)
  }

  function clearSession(): void {
    user.value = null
    accessToken.value = null
    setAccessToken(null)
  }

  async function login(credentials: LoginRequest): Promise<User> {
    const response = await loginRequest(credentials)
    applyToken(response.access_token)
    user.value = response.user
    initialized.value = true
    return response.user
  }

  async function fetchMe(): Promise<User> {
    const current = await fetchMeRequest()
    user.value = current
    return current
  }

  async function refresh(): Promise<User | null> {
    try {
      const response: RefreshResponse = await refreshRequest()
      applyToken(response.access_token)
      if (response.user) {
        user.value = response.user
        return response.user
      }
      return await fetchMe()
    } catch (error) {
      clearSession()
      throw error
    }
  }

  /** 应用启动时尝试用 refresh cookie 恢复会话，失败则静默保持未登录。 */
  async function restore(): Promise<void> {
    if (initialized.value) return
    if (restorePromise) return restorePromise

    restorePromise = (async () => {
      try {
        await refresh()
      } catch {
        clearSession()
      } finally {
        initialized.value = true
        restorePromise = null
      }
    })()

    return restorePromise
  }

  async function logout(): Promise<void> {
    try {
      await logoutRequest()
    } catch {
      // 登出接口失败也要清理本地会话，避免 UI 卡在已登录状态。
    } finally {
      clearSession()
      initialized.value = true
    }
  }

  return {
    user,
    accessToken,
    initialized,
    isAuthenticated,
    isAdmin,
    login,
    logout,
    restore,
    refresh,
    fetchMe,
  }
})
