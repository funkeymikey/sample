import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorResponse, IMPORT_ID, importData, jsonResponse, mountRoute, page, rowErrorData, stubApi } from '@/testing'

const IMPORT_URL = `/api/imports/${IMPORT_ID}/`
const ERRORS_URL = `/api/imports/${IMPORT_ID}/errors/`

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ImportDetailView', () => {
  it('summarizes a completed import', async () => {
    stubApi({ [`GET ${IMPORT_URL}`]: () => jsonResponse(importData({ status: 'COMPLETED', row_count: 3 })) })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.get('[data-test="import-status"]').text()).toBe('Completed')
    expect(wrapper.get('[data-test="import-summary"]').text()).toContain('All 3 rows were posted.')
    expect(wrapper.find('[data-test="row-error"]').exists()).toBe(false)
  })

  it('offers the original file, exactly as uploaded, for auditing', async () => {
    stubApi({ [`GET ${IMPORT_URL}`]: () => jsonResponse(importData()) })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.get('[data-test="original-file"]').attributes('href')).toBe(`/api/imports/${IMPORT_ID}/file/`)
  })

  it('lists the problems with a failed import, with the rows to fix as a download', async () => {
    stubApi({
      [`GET ${IMPORT_URL}`]: () => jsonResponse(importData({ status: 'FAILED', row_count: 10, error_count: 2 })),
      [`GET ${ERRORS_URL}`]: () =>
        jsonResponse(
          page([
            rowErrorData({ row_number: 3 }),
            rowErrorData({
              row_number: 7,
              errors: { amount: ['Too small.'], transaction_date: ['Not a date.'] },
            }),
          ]),
        ),
    })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.get('[data-test="import-status"]').text()).toBe('Failed')
    expect(wrapper.get('[data-test="import-summary"]').text()).toContain('2 of 10 rows have problems')
    const rows = wrapper.findAll('[data-test="row-error"]')
    expect(rows.map((row) => row.get('[data-test="line"]').text())).toEqual(['3', '7'])
    expect(rows[1]!.get('[data-test="problems"]').text()).toContain('amount: Too small.')
    expect(rows[1]!.get('[data-test="problems"]').text()).toContain('transaction_date: Not a date.')
    expect(wrapper.get('[data-test="errors-csv"]').attributes('href')).toBe(`/api/imports/${IMPORT_ID}/errors.csv`)
  })

  it('says when an import is still processing', async () => {
    stubApi({ [`GET ${IMPORT_URL}`]: () => jsonResponse(importData({ status: 'PROCESSING', completed_at: null })) })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.get('[data-test="import-status"]').text()).toBe('Processing')
    expect(wrapper.find('[data-test="processing"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="import-summary"]').exists()).toBe(false)
  })

  it('explains when the row errors of a failed import cannot be loaded', async () => {
    stubApi({
      [`GET ${IMPORT_URL}`]: () => jsonResponse(importData({ status: 'FAILED', error_count: 2 })),
      [`GET ${ERRORS_URL}`]: () => errorResponse(500, 'INTERNAL_ERROR', 'An error occurred.'),
    })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.get('[data-test="row-errors-error"]').text()).toBe('An error occurred.')
  })

  it('says so when the import does not exist', async () => {
    stubApi({ [`GET ${IMPORT_URL}`]: () => errorResponse(404, 'NOT_FOUND', 'Not found.') })

    const { wrapper } = await mountRoute(`/imports/${IMPORT_ID}`)

    expect(wrapper.find('[data-test="not-found"]').exists()).toBe(true)
  })
})
