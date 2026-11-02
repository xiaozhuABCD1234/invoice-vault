import { describe, expect, it } from 'vitest'

import {
  bpToPercentInput,
  createEmptyInvoiceDraft,
  createInvoiceDraft,
  firstErrorElementId,
  millisToYuanInput,
  parsePercentToBp,
  parseQuantityInput,
  parseYuanToMillis,
  sumItemAmountCents,
  validateInvoiceDraft,
  type InvoiceDraft,
} from '../extraction-fields'

function validDraft(): InvoiceDraft {
  return {
    ...createEmptyInvoiceDraft(),
    invoiceNumber: 'INV-001',
    sellerName: '测试供应商',
    issueDate: '2026-07-12',
    amountExTax: '100.00',
    tax: '13.00',
    total: '113.00',
    taxRate: '13',
    categoryId: '1',
    requesterId: '2',
    ownerId: '3',
    items: [
      {
        name: '螺栓',
        quantity: '10',
        unitPrice: '10.000',
        amount: '100.00',
        note: '',
      },
    ],
  }
}

describe('extraction money parsing', () => {
  it('parses yuan with 1-3 decimals to millis using integers', () => {
    expect(parseYuanToMillis('10')).toBe(10000)
    expect(parseYuanToMillis('0.125')).toBe(125)
    expect(parseYuanToMillis('¥1,234.56')).toBe(1234560)
    expect(parseYuanToMillis('1.2345')).toBeNull()
    expect(parseYuanToMillis('abc')).toBeNull()
  })

  it('formats millis without trailing zeros', () => {
    expect(millisToYuanInput(10000)).toBe('10')
    expect(millisToYuanInput(1234)).toBe('1.234')
    expect(millisToYuanInput(1050)).toBe('1.05')
    expect(millisToYuanInput(null)).toBe('')
  })

  it('converts percent to basis points and back', () => {
    expect(parsePercentToBp('13')).toBe(1300)
    expect(parsePercentToBp('13.5')).toBe(1350)
    expect(parsePercentToBp('0.13')).toBe(13)
    expect(parsePercentToBp('13.555')).toBeNull()
    expect(bpToPercentInput(1300)).toBe('13')
    expect(bpToPercentInput(1310)).toBe('13.1')
    expect(bpToPercentInput(1305)).toBe('13.05')
  })

  it('parses quantity and sums item amounts', () => {
    expect(parseQuantityInput('2.5')).toBe(2.5)
    expect(parseQuantityInput('-1')).toBeNull()
    expect(
      sumItemAmountCents([
        { name: 'a', quantity: '1', unitPrice: '1', amount: '10.00', note: '' },
        { name: 'b', quantity: '1', unitPrice: '1', amount: '5.50', note: '' },
      ]),
    ).toBe(1550)
  })
})

describe('createInvoiceDraft', () => {
  it('maps camelCase parsed values to editable yuan inputs', () => {
    const draft = createInvoiceDraft({
      parsed: {
        invoiceNumber: '253200000001',
        invoiceCode: '044001900111',
        invoiceType: '电子发票',
        issueDate: '2026-07-12',
        sellerName: '店铺',
        amountExTaxCents: 12345,
        taxCents: 1605,
        totalCents: 13950,
        taxRateBp: 1300,
        categoryId: 1,
        requesterId: 2,
        ownerId: 3,
        invoiceForm: 'paper',
        items: [
          {
            name: '螺栓',
            quantity: 2,
            unitPriceMillis: 1234,
            amountCents: 2468,
            note: '加急',
          },
        ],
      },
    })

    expect(draft.invoiceNumber).toBe('253200000001')
    expect(draft.amountExTax).toBe('123.45')
    expect(draft.total).toBe('139.50')
    expect(draft.taxRate).toBe('13')
    expect(draft.invoiceForm).toBe('paper')
    expect(draft.categoryId).toBe('1')
    expect(draft.items[0]).toEqual({
      name: '螺栓',
      quantity: '2',
      unitPrice: '1.234',
      amount: '24.68',
      note: '加急',
    })
  })
})

describe('validateInvoiceDraft', () => {
  it('builds InvoiceCreate for a complete draft', () => {
    const result = validateInvoiceDraft(validDraft(), 9)

    expect(result.errors).toEqual({})
    expect(result.amountMismatch).toBeNull()
    expect(result.payload).toMatchObject({
      invoice_number: 'INV-001',
      issue_date: '2026-07-12',
      seller_name: '测试供应商',
      amount_ex_tax_cents: 10000,
      tax_cents: 1300,
      total_cents: 11300,
      tax_rate_bp: 1300,
      category_id: 1,
      requester_id: 2,
      owner_id: 3,
      source_document_id: 9,
      items: [
        {
          name: '螺栓',
          quantity: 10,
          unit_price_millis: 10000,
          amount_cents: 10000,
          sort_order: 1,
        },
      ],
    })
  })

  it('reports missing required fields and items', () => {
    const draft = createEmptyInvoiceDraft()
    const result = validateInvoiceDraft(draft, 1)

    expect(result.payload).toBeNull()
    expect(result.errors.invoiceNumber).toBeTruthy()
    expect(result.errors.issueDate).toBeTruthy()
    expect(result.errors.sellerName).toBeTruthy()
    expect(result.errors.categoryId).toBeTruthy()
    expect(result.errors.requesterId).toBeTruthy()
    expect(result.errors.ownerId).toBeTruthy()
    expect(result.errors.items).toBeTruthy()
  })

  it('blocks when total differs from amount + tax by more than 1 cent', () => {
    const draft = validDraft()
    draft.total = '113.02'
    const result = validateInvoiceDraft(draft, 1)

    expect(result.payload).toBeNull()
    expect(result.errors.total).toContain('相差')
    expect(result.amountMismatch).toContain('相差')
  })

  it('reports item field errors and first focus target', () => {
    const draft = validDraft()
    draft.items = [
      { name: '', quantity: '0', unitPrice: 'abc', amount: '', note: '' },
    ]
    const result = validateInvoiceDraft(draft, 1)

    expect(result.payload).toBeNull()
    expect(result.errors['items.0.name']).toBeTruthy()
    expect(result.errors['items.0.quantity']).toBeTruthy()
    expect(result.errors['items.0.unitPrice']).toBeTruthy()
    expect(result.errors['items.0.amount']).toBeTruthy()
    expect(firstErrorElementId(result.errors)).toBe('review-item-0-name')
  })
})
