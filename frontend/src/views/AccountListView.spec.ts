import { flushPromises } from '@vue/test-utils'
import DataTable from 'primevue/datatable'
import SelectButton from 'primevue/selectbutton'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { accountData, errorResponse, jsonResponse, lastQuery, mountRoute, page, stubApi } from '@/testing'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function stubAccounts(accounts = [accountData()]) {
  return stubApi({ 'GET /api/accounts/': () => jsonResponse(page(accounts)) })
}

describe('AccountListView', () => {
  it('lists accounts with their balances', async () => {
    stubAccounts([
      accountData({ id: 'a1', account_number: 'ACCT1', holder_name: 'Ada Lovelace', balance: '1234.56' }),
      accountData({
        id: 'a2',
        account_number: 'ACCT2',
        holder_name: 'Grace Hopper',
        balance: '-75.00',
        status: 'CLOSED',
      }),
    ])

    const { wrapper } = await mountRoute('/accounts')

    const rows = wrapper.findAll('[data-test="account-row"]')
    expect(rows.map((row) => row.get('[data-test="account-number"]').text())).toEqual(['ACCT1', 'ACCT2'])
    const balances = wrapper.findAll('[data-test="money"]')
    expect(balances.map((balance) => balance.text())).toEqual(['$1,234.56', '-$75.00'])
    expect(balances.map((balance) => balance.attributes('data-sign'))).toEqual(['positive', 'negative'])
    expect(wrapper.findAll('[data-test="account-status"]').map((status) => status.text())).toEqual(['Open', 'Closed'])
  })

  it('shows a message when there are no accounts', async () => {
    stubAccounts([])

    const { wrapper } = await mountRoute('/accounts')

    expect(wrapper.find('[data-test="empty"]').exists()).toBe(true)
  })

  it('searches after the user stops typing', async () => {
    vi.useFakeTimers()
    const fetchMock = stubAccounts()
    const { wrapper } = await mountRoute('/accounts')

    await wrapper.get('[data-test="account-search"]').setValue('lovelace')
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(lastQuery(fetchMock, '/api/accounts/')).toEqual({
      search: 'lovelace',
      ordering: 'account_number',
      page: '1',
    })
  })

  it('filters by status, sorts and pages through the API', async () => {
    const fetchMock = stubAccounts()
    const { wrapper } = await mountRoute('/accounts')

    wrapper.findComponent(SelectButton).vm.$emit('update:modelValue', 'CLOSED')
    await flushPromises()
    expect(lastQuery(fetchMock, '/api/accounts/')).toMatchObject({ status: 'CLOSED', page: '1' })

    wrapper.findComponent(DataTable).vm.$emit('sort', { sortField: 'balance', sortOrder: -1 })
    await flushPromises()
    expect(lastQuery(fetchMock, '/api/accounts/')).toMatchObject({ ordering: '-balance' })

    wrapper.findComponent(DataTable).vm.$emit('page', { page: 1, rows: 25 })
    await flushPromises()
    expect(lastQuery(fetchMock, '/api/accounts/')).toMatchObject({ status: 'CLOSED', ordering: '-balance', page: '2' })
  })

  it('links each account by its account number, so keyboards can open it too', async () => {
    stubAccounts([accountData({ id: 'a1', account_number: 'ACCT1' })])

    const { wrapper } = await mountRoute('/accounts')

    const link = wrapper.get('[data-test="account-number"]')
    expect(link.element.tagName).toBe('A')
    expect(link.attributes('href')).toBe('/accounts/a1')
  })

  it('opens an account when its row is clicked', async () => {
    const account = accountData()
    stubAccounts([account])
    const { wrapper, router } = await mountRoute('/accounts')

    wrapper.findComponent(DataTable).vm.$emit('row-click', { data: account })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe(`/accounts/${account.id}`)
  })

  it('links to the new account form', async () => {
    stubAccounts()

    const { wrapper } = await mountRoute('/accounts')

    expect(wrapper.get('[data-test="open-account"]').attributes('href')).toBe('/accounts/new')
  })
})

describe('AccountListView: state in the URL', () => {
  it('restores search, filter, sort and page from the URL', async () => {
    const fetchMock = stubApi({ 'GET /api/accounts/': () => jsonResponse(page([accountData()], 60)) })

    const { wrapper } = await mountRoute('/accounts?search=ada&status=CLOSED&ordering=-balance&page=2')

    expect(lastQuery(fetchMock, '/api/accounts/')).toEqual({
      search: 'ada',
      status: 'CLOSED',
      ordering: '-balance',
      page: '2',
    })
    expect((wrapper.get('[data-test="account-search"]').element as HTMLInputElement).value).toBe('ada')
    expect(wrapper.findComponent(SelectButton).props('modelValue')).toBe('CLOSED')
  })

  it('puts changes in the URL, leaving out defaults', async () => {
    vi.useFakeTimers()
    stubAccounts()
    const { wrapper, router } = await mountRoute('/accounts')

    wrapper.findComponent(SelectButton).vm.$emit('update:modelValue', 'CLOSED')
    await flushPromises()
    wrapper.findComponent(DataTable).vm.$emit('sort', { sortField: 'balance', sortOrder: -1 })
    await flushPromises()
    wrapper.findComponent(DataTable).vm.$emit('page', { page: 1, rows: 25 })
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ status: 'CLOSED', ordering: '-balance', page: '2' })

    await wrapper.get('[data-test="account-search"]').setValue('ada')
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ search: 'ada', status: 'CLOSED', ordering: '-balance' })
  })

  it('goes back to page 1 when the page in the URL no longer exists', async () => {
    stubApi({
      'GET /api/accounts/': (url) =>
        url.searchParams.get('page') === '5'
          ? errorResponse(404, 'NOT_FOUND', 'Invalid page.')
          : jsonResponse(page([accountData()])),
    })

    const { wrapper, router } = await mountRoute('/accounts?status=OPEN&page=5')

    expect(router.currentRoute.value.query).toEqual({ status: 'OPEN' })
    expect(wrapper.findAll('[data-test="account-row"]')).toHaveLength(1)
    expect(wrapper.find('[data-test="load-error"]').exists()).toBe(false)
  })

  it('ignores invalid values in the URL', async () => {
    const fetchMock = stubAccounts()

    await mountRoute('/accounts?status=BOGUS&ordering=password&page=-3')

    expect(lastQuery(fetchMock, '/api/accounts/')).toEqual({ ordering: 'account_number', page: '1' })
  })

  it('follows the URL when it changes, e.g. clicking "Accounts" while filtered', async () => {
    const fetchMock = stubAccounts()
    const { router } = await mountRoute('/accounts?status=CLOSED')

    await router.push('/accounts')
    await flushPromises()

    expect(lastQuery(fetchMock, '/api/accounts/')).toEqual({ ordering: 'account_number', page: '1' })
  })
})
