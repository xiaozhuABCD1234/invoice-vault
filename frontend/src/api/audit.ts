import { request, toQueryParams } from './client'
import type { AuditLog, AuditLogListQuery, Page } from './types'

export function listAuditLogs(
  query: AuditLogListQuery = {},
): Promise<Page<AuditLog>> {
  return request<Page<AuditLog>>('/audit-logs', {
    query: toQueryParams(query),
  })
}
