import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ACCOUNT_ID,
  errorResponse,
  jsonResponse,
  mountRoute,
  stubApi,
  TRANSACTION_ID,
  transactionData,
} from '@/testing'

const TRANSACTION_URL = `/api/transactions/${TRANSACTION_ID}/`

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('TransactionDetailView', () => {
  it('shows the transaction and links back to its account', async () => {
    stubApi({
      [`GET ${TRANSACTION_URL}`]: () =>
        jsonResponse(transactionData({ direction: 'DEBIT', amount: '40.25', reference_id: 'REF-9' })),
    })

    const { wrapper } = await mountRoute(`/transactions/${TRANSACTION_ID}`)

    expect(wrapper.get('[data-test="reference-id"]').text()).toBe('REF-9')
    expect(wrapper.get('[data-test="transaction-amount"] [data-test="money"]').text()).toBe('-$40.25')
    expect(wrapper.get('[data-test="transaction-date"]').text()).toBe('Sep 1, 2026')
    expect(wrapper.get('[data-test="account-link"]').attributes('href')).toBe(`/accounts/${ACCOUNT_ID}`)
  })

  it('says so when the transaction does not exist', async () => {
    stubApi({ [`GET ${TRANSACTION_URL}`]: () => errorResponse(404, 'NOT_FOUND', 'Not found.') })

    const { wrapper } = await mountRoute(`/transactions/${TRANSACTION_ID}`)

    expect(wrapper.find('[data-test="not-found"]').exists()).toBe(true)
  })
})
