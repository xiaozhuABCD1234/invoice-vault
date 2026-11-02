import { request, toQueryParams } from './client'
import type { DashboardQuery, DashboardSummary } from './types'

export function getDashboardSummary(
  query: DashboardQuery = {},
): Promise<DashboardSummary> {
  return request<DashboardSummary>('/dashboard/summary', {
    query: toQueryParams(query),
  })
}
