import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ACCOUNT_ID, accountData, errorResponse, jsonResponse, mountRoute, requestBody, stubApi } from '@/testing'

const ACCOUNT_URL = `/api/accounts/${ACCOUNT_ID}/`

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AccountFormView: opening an account', () => {
  it('creates the account and shows it', async () => {
    const fetchMock = stubApi({ 'POST /api/accounts/': () => jsonResponse(accountData(), 201) })
    const { wrapper, router } = await mountRoute('/accounts/new')

    await wrapper.get('[data-test="account-number-input"]').setValue('ACCT1')
    await wrapper.get('[data-test="holder-name-input"]').setValue('Ada Lovelace')
    await wrapper.get('[data-test="email-input"]').setValue('ada@example.com')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(requestBody(fetchMock, 'POST /api/accounts/')).toEqual({
      account_number: 'ACCT1',
      holder_name: 'Ada Lovelace',
      email: 'ada@example.com',
    })
    expect(router.currentRoute.value.fullPath).toBe(`/accounts/${ACCOUNT_ID}`)
  })

  it('leaves the account number out when it is blank, so the API generates one', async () => {
    const fetchMock = stubApi({ 'POST /api/accounts/': () => jsonResponse(accountData(), 201) })
    const { wrapper } = await mountRoute('/accounts/new')

    await wrapper.get('[data-test="holder-name-input"]').setValue('Ada Lovelace')
    await wrapper.get('[data-test="account-number-input"]').setValue('   ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(requestBody(fetchMock, 'POST /api/accounts/')).toEqual({ holder_name: 'Ada Lovelace', email: '' })
  })

  it('shows the API field errors next to the fields', async () => {
    stubApi({
      'POST /api/accounts/': () =>
        errorResponse(400, 'VALIDATION_ERROR', 'Invalid request data.', {
          account_number: ['account with this account number already exists.'],
          email: ['Enter a valid email address.'],
        }),
    })
    const { wrapper, router } = await mountRoute('/accounts/new')

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-test="error-account_number"]').text()).toBe(
      'account with this account number already exists.',
    )
    expect(wrapper.get('[data-test="error-email"]').text()).toBe('Enter a valid email address.')
    expect(router.currentRoute.value.fullPath).toBe('/accounts/new')
  })
})

describe('AccountFormView: editing an account', () => {
  it('loads the account and saves only the editable fields', async () => {
    const fetchMock = stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData({ holder_name: 'Ada Lovelace' })),
      [`PATCH ${ACCOUNT_URL}`]: () => jsonResponse(accountData({ holder_name: 'Ada King' })),
    })
    const { wrapper, router } = await mountRoute(`/accounts/${ACCOUNT_ID}/edit`)

    const accountNumberInput = wrapper.get('[data-test="account-number-input"]')
    expect((accountNumberInput.element as HTMLInputElement).value).toBe('ACCT1')
    expect(accountNumberInput.attributes('disabled')).toBeDefined() // can't change after create
    await wrapper.get('[data-test="holder-name-input"]').setValue('Ada King')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(requestBody(fetchMock, `PATCH ${ACCOUNT_URL}`)).toEqual({
      holder_name: 'Ada King',
      email: 'ada@example.com',
    })
    expect(router.currentRoute.value.fullPath).toBe(`/accounts/${ACCOUNT_ID}`)
  })

  it("doesn't offer to edit a closed account", async () => {
    stubApi({ [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData({ status: 'CLOSED' })) })

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}/edit`)

    expect(wrapper.find('[data-test="closed-notice"]').exists()).toBe(true)
    expect(wrapper.find('form').exists()).toBe(false)
  })
})

describe('AccountFormView: loading problems', () => {
  it('shows why the account could not be loaded', async () => {
    stubApi({ [`GET ${ACCOUNT_URL}`]: () => errorResponse(500, 'INTERNAL_ERROR', 'An error occurred.') })

    const { wrapper } = await mountRoute(`/accounts/${ACCOUNT_ID}/edit`)

    expect(wrapper.get('[data-test="load-error"]').text()).toBe('An error occurred.')
    expect(wrapper.find('form').exists()).toBe(false)
  })
})
