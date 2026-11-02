import { request, toQueryParams } from './client'
import type {
  ExtractionApproveResponse,
  ExtractionJob,
  ExtractionJobDetail,
  ExtractionJobListQuery,
  ExtractionRejectRequest,
  InvoiceCreate,
  Page,
} from './types'

export function listExtractionJobs(
  query: ExtractionJobListQuery = {},
): Promise<Page<ExtractionJob>> {
  return request<Page<ExtractionJob>>('/extraction-jobs', {
    query: toQueryParams(query),
  })
}

export function getExtractionJob(id: number): Promise<ExtractionJobDetail> {
  return request<ExtractionJobDetail>(`/extraction-jobs/${id}`)
}

export function retryExtractionJob(id: number): Promise<ExtractionJob> {
  return request<ExtractionJob>(`/extraction-jobs/${id}/retry`, {
    method: 'POST',
  })
}

export function approveExtractionJob(
  id: number,
  body: InvoiceCreate,
): Promise<ExtractionApproveResponse> {
  return request<ExtractionApproveResponse>(
    `/extraction-jobs/${id}/approve`,
    { method: 'POST', body },
  )
}

export function rejectExtractionJob(
  id: number,
  body: ExtractionRejectRequest,
): Promise<ExtractionJob> {
  return request<ExtractionJob>(`/extraction-jobs/${id}/reject`, {
    method: 'POST',
    body,
  })
}
