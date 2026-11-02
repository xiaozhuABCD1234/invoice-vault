import { getBlob, request, toQueryParams } from './client'
import type {
  Document,
  DocumentDetail,
  DocumentListQuery,
  DocumentPreviewVersion,
  DocumentUploadInput,
  DocumentUploadResponse,
  Page,
} from './types'

export function listDocuments(
  query: DocumentListQuery = {},
): Promise<Page<Document>> {
  return request<Page<Document>>('/documents', {
    query: toQueryParams(query),
  })
}

export function getDocument(id: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`)
}

export function uploadDocument(
  input: DocumentUploadInput,
): Promise<DocumentUploadResponse> {
  const form = new FormData()
  form.append('file', input.file)
  form.append('doc_type', input.doc_type)
  if (input.title && input.title.trim() !== '') {
    form.append('title', input.title)
  }
  return request<DocumentUploadResponse>('/documents', {
    method: 'POST',
    body: form,
  })
}

export function uploadDocumentVersion(
  id: number,
  file: File,
): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  return request<Document>(`/documents/${id}/versions`, {
    method: 'POST',
    body: form,
  })
}

export function deleteDocument(id: number): Promise<void> {
  return request<void>(`/documents/${id}`, { method: 'DELETE' })
}

function versionQuery(
  version: DocumentPreviewVersion,
): Record<string, string | number> {
  return typeof version === 'number'
    ? { version_id: version }
    : { version }
}

/** 预览必须走带 token 的 blob 请求，再由调用方生成 object URL。 */
export function getDocumentPreview(
  id: number,
  version: DocumentPreviewVersion = 'latest',
  signal?: AbortSignal,
): Promise<Blob> {
  return getBlob(`/documents/${id}/preview`, {
    query: versionQuery(version),
    signal,
  })
}

/** 下载（admin）同样走 blob 请求，由页面触发保存。 */
export function downloadDocument(
  id: number,
  version: DocumentPreviewVersion = 'latest',
  signal?: AbortSignal,
): Promise<Blob> {
  return getBlob(`/documents/${id}/download`, {
    query: versionQuery(version),
    signal,
  })
}
