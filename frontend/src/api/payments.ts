import { request, toQueryParams } from './client'
import type {
  Allocation,
  AllocationCreate,
  AllocationUpdate,
  Page,
  Payment,
  PaymentCreate,
  PaymentListQuery,
  PaymentUpdate,
} from './types'

export function listPayments(
  query: PaymentListQuery = {},
): Promise<Page<Payment>> {
  return request<Page<Payment>>('/payments', {
    query: toQueryParams(query),
  })
}

export function getPayment(id: number): Promise<Payment> {
  return request<Payment>(`/payments/${id}`)
}

export function createPayment(body: PaymentCreate): Promise<Payment> {
  return request<Payment>('/payments', { method: 'POST', body })
}

export function updatePayment(
  id: number,
  body: PaymentUpdate,
): Promise<Payment> {
  return request<Payment>(`/payments/${id}`, {
    method: 'PATCH',
    body,
  })
}

export function createAllocation(
  paymentId: number,
  body: AllocationCreate,
): Promise<Allocation> {
  return request<Allocation>(`/payments/${paymentId}/allocations`, {
    method: 'POST',
    body,
  })
}

export function updateAllocation(
  allocationId: number,
  body: AllocationUpdate,
): Promise<Allocation> {
  return request<Allocation>(`/allocations/${allocationId}`, {
    method: 'PATCH',
    body,
  })
}

export function deleteAllocation(allocationId: number): Promise<void> {
  return request<void>(`/allocations/${allocationId}`, {
    method: 'DELETE',
  })
}
