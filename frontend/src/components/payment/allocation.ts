import type { Allocation, Invoice } from '@/api/types'

/** 分配行 + 发票摘要（列表响应未内联时由付款详情补取）。 */
export interface AllocationRow extends Allocation {
  invoice_number: string | null
  seller_name: string | null
  can_manage: boolean
}

export function buildAllocationRows(
  allocations: Allocation[],
  invoices: Map<number, Invoice>,
  canManage: (allocation: Allocation) => boolean,
): AllocationRow[] {
  return allocations.map((allocation) => {
    const invoice = invoices.get(allocation.invoice_id)
    return {
      ...allocation,
      invoice_number:
        allocation.invoice_number ?? invoice?.invoice_number ?? null,
      seller_name:
        allocation.invoice_seller_name ?? invoice?.seller_name ?? null,
      can_manage: canManage(allocation),
    }
  })
}
