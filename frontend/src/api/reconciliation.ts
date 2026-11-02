import { request, toQueryParams } from './client'
import type {
  IgnoreIssueRequest,
  Page,
  ReconciliationIssue,
  ReconciliationIssueListQuery,
  ReconciliationSummary,
} from './types'

export function getReconciliationSummary(): Promise<ReconciliationSummary> {
  return request<ReconciliationSummary>('/reconciliation/summary')
}

export function listReconciliationIssues(
  query: ReconciliationIssueListQuery = {},
): Promise<Page<ReconciliationIssue>> {
  return request<Page<ReconciliationIssue>>('/reconciliation/issues', {
    query: toQueryParams(query),
  })
}

export function ignoreReconciliationIssue(
  issueKey: string,
  body: IgnoreIssueRequest,
): Promise<ReconciliationIssue> {
  return request<ReconciliationIssue>(
    `/reconciliation/issues/${encodeURIComponent(issueKey)}/ignore`,
    { method: 'POST', body },
  )
}

export function unignoreReconciliationIssue(
  issueKey: string,
): Promise<ReconciliationIssue> {
  return request<ReconciliationIssue>(
    `/reconciliation/issues/${encodeURIComponent(issueKey)}/ignore`,
    { method: 'DELETE' },
  )
}
