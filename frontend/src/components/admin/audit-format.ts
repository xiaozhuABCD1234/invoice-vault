import type { AuditLog, JsonValue } from '@/api/types'
import { EMPTY_TEXT } from '@/lib/format'

export function auditActorLabel(log: AuditLog): string {
  if (log.actor_name !== null && log.actor_name.trim() !== '') {
    return log.actor_name
  }
  if (log.actor_id !== null && log.actor_id !== undefined) {
    return `用户 #${log.actor_id}`
  }
  return EMPTY_TEXT
}

/** entity_id 可能是数字或字符串，展示前统一 String。 */
export function auditEntityLabel(log: AuditLog): string {
  if (log.entity_id === null || log.entity_id === undefined) {
    return log.entity_type
  }
  return `${log.entity_type} #${String(log.entity_id)}`
}

/** 详情弹窗按缩进 JSON 展示；文本插值渲染，避免 XSS。 */
export function formatAuditJson(value: JsonValue | null): string {
  if (value === null) return EMPTY_TEXT
  try {
    return JSON.stringify(value, null, 2) ?? EMPTY_TEXT
  } catch {
    return String(value)
  }
}
