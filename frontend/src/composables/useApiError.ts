import { ApiError } from '@/api/client'

/**
 * 把 API 错误转换为可展示文案。
 * 后端 message 已经是面向用户的中文说明，优先原样展示。
 */
export function apiErrorMessage(
  error: unknown,
  fallback = '操作失败，请稍后重试',
): string {
  if (error instanceof ApiError) {
    return error.message.trim() !== '' ? error.message : fallback
  }
  if (error instanceof Error && error.message.trim() !== '') {
    return error.message
  }
  return fallback
}
