import { flushPromises } from '@vue/test-utils'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import SelectButton from 'primevue/selectbutton'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ACCOUNT_ID,
  accountData,
  errorResponse,
  jsonResponse,
  lastQuery,
  mountRoute,
  page,
  requestBody,
  stubApi,
  transactionData,
} from '@/testing'

const ACCOUNT_URL = `/api/accounts/${ACCOUNT_ID}/`
const TRANSACTIONS_URL = `/api/accounts/${ACCOUNT_ID}/transactions/`

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubAccount(account = accountData(), transactions = [transactionData()]) {
  return stubApi({
    [`GET ${ACCOUNT_URL}`]: () => jsonResponse(account),
    [`GET ${TRANSACTIONS_URL}`]: () => jsonResponse(page(transactions)),
    [`PATCH ${ACCOUNT_URL}`]: () => jsonResponse({ ...account, status: 'CLOSED' }),
  })
}

describe('AccountDetailView', () => {
  it('shows the account and its balance', async () => {
    stubAccount(accountData({ holder_name: 'Ada Lovelace', account_number: 'ACCT1', balance: '-12.50' }))

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    expect(wrapper.get('[data-test="holder-name"]').text()).toBe('Ada Lovelace')
    expect(wrapper.get('[data-test="account-number"]').text()).toBe('ACCT1')
    const balance = wrapper.get('[data-test="balance"] [data-test="money"]')
    expect(balance.text()).toBe('-$12.50')
    expect(balance.attributes('data-sign')).toBe('negative')
  })

  it('lists transactions with credits as money in and debits as money out', async () => {
    stubAccount(accountData(), [
      transactionData({ id: 't1', direction: 'CREDIT', amount: '100.00' }),
      transactionData({ id: 't2', direction: 'DEBIT', amount: '40.25' }),
    ])

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    const amounts = wrapper.findAll('[data-test="transaction-amount"] [data-test="money"]')
    expect(amounts.map((amount) => amount.text())).toEqual(['+$100.00', '-$40.25'])
  })

  it('links each transaction by its reference, so keyboards can open it too', async () => {
    stubAccount(accountData(), [transactionData({ id: 't1', reference_id: 'REF-7' })])

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    const link = wrapper.get('[data-test="transaction-link"]')
    expect(link.text()).toBe('REF-7')
    expect(link.attributes('href')).toBe('/transactions/t1')
  })

  it('filters transactions by direction and date range', async () => {
    const fetchMock = stubAccount()
    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    wrapper.findComponent(SelectButton).vm.$emit('update:modelValue', 'DEBIT')
    const [fromPicker, toPicker] = wrapper.findAllComponents(DatePicker)
    fromPicker!.vm.$emit('update:modelValue', new Date(2026, 8, 1))
    toPicker!.vm.$emit('update:modelValue', new Date(2026, 8, 30))
    await flushPromises()

    expect(lastQuery(fetchMock, TRANSACTIONS_URL)).toEqual({
      direction: 'DEBIT',
      transaction_date_after: '2026-09-01',
      transaction_date_before: '2026-09-30',
      page: '1',
    })
  })

  it('pages through transactions and opens one when clicked', async () => {
    const transaction = transactionData()
    const fetchMock = stubAccount(accountData(), [transaction])
    const { wrapper, router } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    wrapper.findComponent(DataTable).vm.$emit('page', { page: 2, rows: 25 })
    await flushPromises()
    expect(lastQuery(fetchMock, TRANSACTIONS_URL)).toEqual({ page: '3' })

    wrapper.findComponent(DataTable).vm.$emit('row-click', { data: transaction })
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe(`/transactions/${transaction.id}`)
  })

  it('closes the account after confirmation', async () => {
    const fetchMock = stubAccount()
    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    await wrapper.get('[data-test="close-account"]').trigger('click')
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH')).toBe(false) // not until confirmed
    await wrapper.get('[data-test="confirm-close"]').trigger('click')
    await flushPromises()

    expect(requestBody(fetchMock, `PATCH ${ACCOUNT_URL}`)).toEqual({ status: 'CLOSED' })
    expect(wrapper.get('[data-test="account-status"]').text()).toBe('Closed')
    expect(wrapper.find('[data-test="closed-notice"]').exists()).toBe(true)
  })

  it('keeps the account open and explains why when closing fails', async () => {
    stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`GET ${TRANSACTIONS_URL}`]: () => jsonResponse(page([])),
      [`PATCH ${ACCOUNT_URL}`]: () => errorResponse(500, 'INTERNAL_ERROR', 'An error occurred.'),
    })
    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    await wrapper.get('[data-test="close-account"]').trigger('click')
    await wrapper.get('[data-test="confirm-close"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="toast"]').text()).toContain("Couldn't close the account")
    expect(wrapper.get('[data-test="toast"]').text()).toContain('An error occurred.')
    expect(wrapper.get('[data-test="account-status"]').text()).toBe('Open')
  })

  it('offers posting and editing only while the account is open', async () => {
    stubAccount(accountData({ status: 'OPEN' }))
    const { wrapper: openWrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)
    vi.unstubAllGlobals()
    stubAccount(accountData({ status: 'CLOSED' }))
    const { wrapper: closedWrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    expect(openWrapper.get('[data-test="post-transaction"]').attributes('href')).toBe(
      `/accounts/${ACCOUNT_ID}/transactions/new`,
    )
    expect(openWrapper.get('[data-test="edit-account"]').attributes('href')).toBe(`/accounts/${ACCOUNT_ID}/edit`)
    for (const action of ['post-transaction', 'edit-account', 'close-account']) {
      expect(closedWrapper.find(`[data-test="${action}"]`).exists()).toBe(false)
    }
    expect(closedWrapper.find('[data-test="closed-notice"]').exists()).toBe(true)
  })

  it('says so when the account does not exist', async () => {
    stubApi({
      [`GET ${ACCOUNT_URL}`]: () => errorResponse(404, 'NOT_FOUND', 'No Account matches the given query.'),
      [`GET ${TRANSACTIONS_URL}`]: () => errorResponse(404, 'NOT_FOUND', 'No Account matches the given query.'),
    })

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    expect(wrapper.find('[data-test="not-found"]').exists()).toBe(true)
  })
})

describe('AccountDetailView: transaction filters in the URL', () => {
  it('restores the direction, dates and page from the URL', async () => {
    const fetchMock = stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`GET ${TRANSACTIONS_URL}`]: () => jsonResponse(page([transactionData()], 60)),
    })

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}?direction=DEBIT&from=2026-09-01&to=2026-09-30&page=2`)

    expect(lastQuery(fetchMock, TRANSACTIONS_URL)).toEqual({
      direction: 'DEBIT',
      transaction_date_after: '2026-09-01',
      transaction_date_before: '2026-09-30',
      page: '2',
    })
    expect(wrapper.findComponent(SelectButton).props('modelValue')).toBe('DEBIT')
    const [fromPicker] = wrapper.findAllComponents(DatePicker)
    expect(fromPicker!.props('modelValue')).toEqual(new Date(2026, 8, 1))
  })

  it('puts filter changes in the URL', async () => {
    stubAccount()
    const { wrapper, router } = await mountRoute(`/accounts/${ACCOUNT_ID}`)

    wrapper.findComponent(SelectButton).vm.$emit('update:modelValue', 'CREDIT')
    await flushPromises()
    const [fromPicker, toPicker] = wrapper.findAllComponents(DatePicker)
    fromPicker!.vm.$emit('update:modelValue', new Date(2026, 8, 1))
    await flushPromises()
    toPicker!.vm.$emit('update:modelValue', new Date(2026, 8, 30))
    await flushPromises()
    wrapper.findComponent(DataTable).vm.$emit('page', { page: 2, rows: 25 })
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({
      direction: 'CREDIT',
      from: '2026-09-01',
      to: '2026-09-30',
      page: '3',
    })

    fromPicker!.vm.$emit('update:modelValue', null) // cleared
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ direction: 'CREDIT', to: '2026-09-30' })
  })

  it('ignores invalid values in the URL', async () => {
    const fetchMock = stubAccount()

    await mountRoute(`/accounts/${ACCOUNT_ID}?direction=UP&from=2026-02-30&to=yesterday&page=0`)

    expect(lastQuery(fetchMock, TRANSACTIONS_URL)).toEqual({ page: '1' })
  })
})
