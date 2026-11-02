import { ref } from 'vue'
import { defineStore } from 'pinia'

const SIDEBAR_STORAGE_KEY = 'invoice-vault:ui:sidebar-collapsed'

function readSidebarCollapsed(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(readSidebarCollapsed())

  function setSidebarCollapsed(value: boolean): void {
    sidebarCollapsed.value = value
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, value ? '1' : '0')
    } catch {
      // 隐私模式等场景下持久化失败不影响本次会话。
    }
  }

  function toggleSidebar(): void {
    setSidebarCollapsed(!sidebarCollapsed.value)
  }

  return {
    sidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar,
  }
})
