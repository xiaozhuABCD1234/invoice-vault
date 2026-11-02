import { request, toQueryParams } from './client'
import type {
  Invoice,
  InvoiceCreate,
  InvoiceListQuery,
  InvoicePaymentsResponse,
  InvoiceUpdate,
  Page,
} from './types'

export function listInvoices(
  query: InvoiceListQuery = {},
): Promise<Page<Invoice>> {
  return request<Page<Invoice>>('/invoices', {
    query: toQueryParams(query),
  })
}

export function getInvoice(id: number): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}`)
}

export function createInvoice(body: InvoiceCreate): Promise<Invoice> {
  return request<Invoice>('/invoices', { method: 'POST', body })
}

export function updateInvoice(
  id: number,
  body: InvoiceUpdate,
): Promise<Invoice> {
  return request<Invoice>(`/invoices/${id}`, {
    method: 'PATCH',
    body,
  })
}

export function deleteInvoice(id: number): Promise<void> {
  return request<void>(`/invoices/${id}`, { method: 'DELETE' })
}

export function listInvoicePayments(
  id: number,
): Promise<InvoicePaymentsResponse> {
  return request<InvoicePaymentsResponse>(`/invoices/${id}/payments`)
}
