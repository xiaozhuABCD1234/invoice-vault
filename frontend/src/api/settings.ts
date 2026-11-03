import { request, toQueryParams } from './client'
import type {
  ExtractionSettings,
  ExtractionSettingsRevision,
  ExtractionSettingsUpdate,
  ItemsResponse,
} from './types'

export function getExtractionSettings(): Promise<ExtractionSettings> {
  return request<ExtractionSettings>('/admin/settings/extraction')
}

export function updateExtractionSettings(
  body: ExtractionSettingsUpdate,
): Promise<ExtractionSettings> {
  return request<ExtractionSettings>('/admin/settings/extraction', {
    method: 'PUT',
    body,
  })
}

/** 清空数据库覆盖层，回到 .env / 默认值。 */
export function resetExtractionSettings(): Promise<ExtractionSettings> {
  return request<ExtractionSettings>('/admin/settings/extraction', {
    method: 'DELETE',
  })
}

export function listExtractionSettingsRevisions(
  limit = 20,
): Promise<ItemsResponse<ExtractionSettingsRevision>> {
  return request<ItemsResponse<ExtractionSettingsRevision>>(
    '/admin/settings/extraction/history',
    { query: toQueryParams({ limit }) },
  )
}

export function rollbackExtractionSettings(
  revisionId: number,
): Promise<ExtractionSettings> {
  return request<ExtractionSettings>('/admin/settings/extraction/rollback', {
    method: 'POST',
    body: { revision_id: revisionId },
  })
}
