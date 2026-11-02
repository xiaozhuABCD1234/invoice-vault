import type { CategoryKind, Role } from '@/api/types'

export const ROLE_OPTIONS: Array<{ value: Role; label: string }> = [
  { value: 'admin', label: '管理员' },
  { value: 'user', label: '普通用户' },
]

/** Reka Select 不允许空字符串 value，用 all 作为“全部”哨兵。 */
export const ROLE_FILTER_OPTIONS = [
  { value: 'all', label: '全部角色' },
  ...ROLE_OPTIONS,
]

export const CATEGORY_KIND_OPTIONS: Array<{
  value: CategoryKind
  label: string
}> = [
  { value: 'purchase', label: '采购' },
  { value: 'expense', label: '费用' },
]

export function roleLabel(role: Role | string): string {
  return role === 'admin' ? '管理员' : '普通用户'
}

export function categoryKindLabel(kind: CategoryKind | string): string {
  return kind === 'purchase' ? '采购' : '费用'
}

export function activeStatusLabel(isActive: boolean): string {
  return isActive ? '已启用' : '已停用'
}
