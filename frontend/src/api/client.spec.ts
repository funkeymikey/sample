import { afterEach, describe, expect, it } from 'vitest'
import { vi } from 'vitest'

import {
  ApiError,
  createAccount,
  describeError,
  getAccount,
  listAccounts,
  listAccountTransactions,
  postTransaction,
  updateAccount,
} from '@/api/client'
import { errorResponse, jsonResponse, lastQuery, requestBody, stubApi } from '@/testing'

const ACCOUNT_ID = '11111111-1111-1111-1111-111111111111'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client', () => {
  it('sends list filters as query parameters, leaving out empty ones', async () => {
    const fetchMock = stubApi({ 'GET /api/accounts/': () => jsonResponse({ count: 0, results: [] }) })

    await listAccounts({ search: 'ada', status: undefined, ordering: '-balance', page: 2 })

    expect(lastQuery(fetchMock, '/api/accounts/')).toEqual({ search: 'ada', ordering: '-balance', page: '2' })
  })

  it('sends JSON bodies with the right method and path', async () => {
    const fetchMock = stubApi({
      'POST /api/accounts/': () => jsonResponse({ id: ACCOUNT_ID }, 201),
      [`PATCH /api/accounts/${ACCOUNT_ID}/`]: () => jsonResponse({ id: ACCOUNT_ID }),
      [`POST /api/accounts/${ACCOUNT_ID}/transactions/`]: () => jsonResponse({ id: 'txn' }, 201),
    })
    const transaction = {
      direction: 'CREDIT',
      amount: '125.50',
      transaction_date: '2026-09-01',
      reference_id: 'REF-1',
    } as const

    await createAccount({ account_number: 'ACCT1', holder_name: 'Ada Lovelace' })
    await updateAccount(ACCOUNT_ID, { status: 'CLOSED' })
    await postTransaction(ACCOUNT_ID, transaction)

    expect(requestBody(fetchMock, 'POST /api/accounts/')).toEqual({
      account_number: 'ACCT1',
      holder_name: 'Ada Lovelace',
    })
    expect(requestBody(fetchMock, `PATCH /api/accounts/${ACCOUNT_ID}/`)).toEqual({ status: 'CLOSED' })
    expect(requestBody(fetchMock, `POST /api/accounts/${ACCOUNT_ID}/transactions/`)).toEqual(transaction)
  })

  it('returns the parsed response', async () => {
    stubApi({
      [`GET /api/accounts/${ACCOUNT_ID}/`]: () => jsonResponse({ id: ACCOUNT_ID, balance: '12.34' }),
      [`GET /api/accounts/${ACCOUNT_ID}/transactions/`]: () => jsonResponse({ count: 1, results: [{ id: 'txn' }] }),
    })

    expect((await getAccount(ACCOUNT_ID)).balance).toBe('12.34')
    expect((await listAccountTransactions(ACCOUNT_ID, {})).count).toBe(1)
  })

  it('throws ApiError with the API error on a non-2xx response', async () => {
    stubApi({ [`GET /api/accounts/${ACCOUNT_ID}/`]: () => errorResponse(404, 'NOT_FOUND', 'Not found.') })

    const error = await getAccount(ACCOUNT_ID).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).errorResponse?.error.message).toBe('Not found.')
  })
})

describe('describeError', () => {
  it('uses the API message and field errors', () => {
    const error = new ApiError(400, {
      error: { type: 'VALIDATION_ERROR', message: 'Invalid request data.', fields: { amount: ['Too small.'] } },
    })

    expect(describeError(error)).toEqual({ message: 'Invalid request data.', fields: { amount: ['Too small.'] } })
  })

  it('falls back to a generic message when the API never answered', () => {
    expect(describeError(new TypeError('Failed to fetch'))).toEqual({
      message: "Couldn't reach the server. Check your connection and try again.",
      fields: {},
    })
    expect(describeError(new ApiError(502, null)).message).toBe(
      "Couldn't reach the server. Check your connection and try again.",
    )
  })
})
