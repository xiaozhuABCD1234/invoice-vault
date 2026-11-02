import { request, toQueryParams } from './client'
import type { AuditLog, AuditLogListQuery, Page } from './types'

/** 审计实体 ID 可能是数字或字符串，列表查询放宽为字符串以支持两种后端形态。 */
export type AuditLogQuery = Omit<AuditLogListQuery, 'entity_id'> & {
  entity_id?: string | number
}

export function listAuditLogs(
  query: AuditLogQuery = {},
): Promise<Page<AuditLog>> {
  return request<Page<AuditLog>>('/audit-logs', {
    query: toQueryParams(query),
  })
}
