import { flushPromises } from '@vue/test-utils'
import DataTable from 'primevue/datatable'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { importData, jsonResponse, lastQuery, mountRoute, page, stubApi } from '@/testing'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ImportListView', () => {
  it('lists imports with their outcome, each linking to its results', async () => {
    stubApi({
      'GET /api/imports/': () =>
        jsonResponse(
          page([
            importData({ id: 'b2', original_filename: 'october.csv', status: 'FAILED', error_count: 4 }),
            importData({ id: 'b1', original_filename: 'september.csv', status: 'COMPLETED' }),
          ]),
        ),
    })

    const { wrapper } = await mountRoute('/imports')

    const links = wrapper.findAll('[data-test="import-link"]')
    expect(links.map((link) => link.text())).toEqual(['october.csv', 'september.csv'])
    expect(links.map((link) => link.attributes('href'))).toEqual(['/imports/b2', '/imports/b1'])
    expect(wrapper.findAll('[data-test="import-status"]').map((status) => status.text())).toEqual([
      'Failed',
      'Completed',
    ])
    expect(wrapper.get('[data-test="upload-link"]').attributes('href')).toBe('/imports/new')
  })

  it('opens an import when its row is clicked', async () => {
    const batch = importData({ id: 'b1' })
    stubApi({ 'GET /api/imports/': () => jsonResponse(page([batch])) })
    const { wrapper, router } = await mountRoute('/imports')

    wrapper.findComponent(DataTable).vm.$emit('row-click', { data: batch })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/imports/b1')
  })

  it('keeps the page in the URL', async () => {
    const fetchMock = stubApi({ 'GET /api/imports/': () => jsonResponse(page([importData()], 60)) })
    const { wrapper, router } = await mountRoute('/imports?page=2')

    expect(lastQuery(fetchMock, '/api/imports/')).toEqual({ page: '2' })
    wrapper.findComponent(DataTable).vm.$emit('page', { page: 2, rows: 25 })
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ page: '3' })
  })

  it('shows a message when there are no imports yet', async () => {
    stubApi({ 'GET /api/imports/': () => jsonResponse(page([])) })

    const { wrapper } = await mountRoute('/imports')

    expect(wrapper.find('[data-test="empty"]').exists()).toBe(true)
  })
})
