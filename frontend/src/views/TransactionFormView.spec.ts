import { flushPromises } from '@vue/test-utils'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import SelectButton from 'primevue/selectbutton'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ACCOUNT_ID,
  accountData,
  errorResponse,
  jsonResponse,
  mountRoute,
  requestBody,
  stubApi,
  transactionData,
} from '@/testing'

const ACCOUNT_URL = `/api/accounts/${ACCOUNT_ID}/`
const TRANSACTIONS_URL = `/api/accounts/${ACCOUNT_ID}/transactions/`
const FORM_PATH = `/accounts/${ACCOUNT_ID}/transactions/new`

afterEach(() => {
  vi.unstubAllGlobals()
})

async function fillAndSubmit(wrapper: Awaited<ReturnType<typeof mountRoute>>['wrapper']) {
  wrapper.findComponent(SelectButton).vm.$emit('update:modelValue', 'DEBIT')
  wrapper.findComponent(InputNumber).vm.$emit('update:modelValue', 125.5)
  wrapper.findComponent(DatePicker).vm.$emit('update:modelValue', new Date(2026, 8, 1))
  await wrapper.get('[data-test="reference-id-input"]').setValue('REF-1')
  await wrapper.get('[data-test="description-input"]').setValue('Rent')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('TransactionFormView', () => {
  it('posts the transaction with the amount as an exact string, then shows the account', async () => {
    const fetchMock = stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`POST ${TRANSACTIONS_URL}`]: () => jsonResponse(transactionData(), 201),
    })
    const { wrapper, router } = await mountRoute(FORM_PATH)

    await fillAndSubmit(wrapper)

    expect(requestBody(fetchMock, `POST ${TRANSACTIONS_URL}`)).toEqual({
      direction: 'DEBIT',
      amount: '125.50',
      transaction_date: '2026-09-01',
      reference_id: 'REF-1',
      description: 'Rent',
    })
    expect(router.currentRoute.value.fullPath).toBe(`/accounts/${ACCOUNT_ID}`)
  })

  it('leaves the reference out when it is blank, so the API generates one', async () => {
    const fetchMock = stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`POST ${TRANSACTIONS_URL}`]: () => jsonResponse(transactionData(), 201),
    })
    const { wrapper } = await mountRoute(FORM_PATH)

    wrapper.findComponent(InputNumber).vm.$emit('update:modelValue', 10)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(requestBody(fetchMock, `POST ${TRANSACTIONS_URL}`)).not.toHaveProperty('reference_id')
  })

  it('shows field errors from the API', async () => {
    stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`POST ${TRANSACTIONS_URL}`]: () =>
        errorResponse(400, 'VALIDATION_ERROR', 'Invalid request data.', {
          amount: ['Ensure this value is greater than or equal to 0.01.'],
        }),
    })
    const { wrapper } = await mountRoute(FORM_PATH)

    await fillAndSubmit(wrapper)

    expect(wrapper.get('[data-test="error-amount"]').text()).toBe('Ensure this value is greater than or equal to 0.01.')
  })

  it('shows rule violations such as a duplicate reference', async () => {
    stubApi({
      [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData()),
      [`POST ${TRANSACTIONS_URL}`]: () =>
        errorResponse(409, 'CONFLICT', "A transaction with reference_id 'REF-1' already exists for this account."),
    })
    const { wrapper, router } = await mountRoute(FORM_PATH)

    await fillAndSubmit(wrapper)

    expect(wrapper.get('[data-test="form-error"]').text()).toContain("reference_id 'REF-1' already exists")
    expect(router.currentRoute.value.fullPath).toBe(FORM_PATH)
  })

  it("doesn't offer the form for a closed account", async () => {
    stubApi({ [`GET ${ACCOUNT_URL}`]: () => jsonResponse(accountData({ status: 'CLOSED' })) })

    const { wrapper } = await mountRoute(FORM_PATH)

    expect(wrapper.find('[data-test="closed-notice"]').exists()).toBe(true)
    expect(wrapper.find('form').exists()).toBe(false)
  })
})

describe('TransactionFormView: loading problems', () => {
  it('shows why the account could not be loaded', async () => {
    stubApi({ [`GET ${ACCOUNT_URL}`]: () => errorResponse(500, 'INTERNAL_ERROR', 'An error occurred.') })

    const { wrapper } = await mountRoute(FORM_PATH)

    expect(wrapper.get('[data-test="load-error"]').text()).toBe('An error occurred.')
    expect(wrapper.find('form').exists()).toBe(false)
  })
})
