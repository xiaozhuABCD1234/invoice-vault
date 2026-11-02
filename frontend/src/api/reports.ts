import { getBlob, request, toQueryParams } from './client'
import type {
  ExportCreate,
  ExportCreateResponse,
  ExportJob,
  ExportListQuery,
  Page,
  ReportTemplate,
  ReportTemplateCreate,
  ReportTemplateUpdate,
} from './types'

export function listReportTemplates(): Promise<{ items: ReportTemplate[] }> {
  return request<{ items: ReportTemplate[] }>('/report-templates')
}

export function createReportTemplate(
  body: ReportTemplateCreate,
): Promise<ReportTemplate> {
  return request<ReportTemplate>('/report-templates', {
    method: 'POST',
    body,
  })
}

export function updateReportTemplate(
  id: number,
  body: ReportTemplateUpdate,
): Promise<ReportTemplate> {
  return request<ReportTemplate>(`/report-templates/${id}`, {
    method: 'PATCH',
    body,
  })
}

export function deleteReportTemplate(id: number): Promise<void> {
  return request<void>(`/report-templates/${id}`, { method: 'DELETE' })
}

export function createExport(body: ExportCreate): Promise<ExportCreateResponse> {
  return request<ExportCreateResponse>('/exports', {
    method: 'POST',
    body,
  })
}

export function listExports(query: ExportListQuery = {}): Promise<Page<ExportJob>> {
  return request<Page<ExportJob>>('/exports', {
    query: toQueryParams(query),
  })
}

export function getExport(id: number): Promise<ExportJob> {
  return request<ExportJob>(`/exports/${id}`)
}

/** xlsx 下载同样需要 Authorization，必须走 blob 请求。 */
export function downloadExport(id: number): Promise<Blob> {
  return getBlob(`/exports/${id}/download`)
}
