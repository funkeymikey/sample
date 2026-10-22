import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorResponse, IMPORT_ID, importData, jsonResponse, mountRoute, stubApi } from '@/testing'

afterEach(() => {
  vi.unstubAllGlobals()
})

type Wrapper = Awaited<ReturnType<typeof mountRoute>>['wrapper']

async function chooseFile(wrapper: Wrapper, name = 'september.csv') {
  const input = wrapper.get('[data-test="file-input"]')
  Object.defineProperty(input.element, 'files', { value: [new File(['a,b\n'], name, { type: 'text/csv' })] })
  await input.trigger('change')
}

describe('ImportUploadView', () => {
  it('offers sample files to download', async () => {
    const { wrapper } = await mountRoute('/imports/new')

    expect(wrapper.get('[data-test="sample-file"]').attributes('href')).toBe('/api/imports/sample.csv')
    expect(wrapper.get('[data-test="sample-file-invalid"]').attributes('href')).toBe(
      '/api/imports/sample.csv?invalid=true',
    )
  })

  it('uploads the chosen file and shows its results', async () => {
    const fetchMock = stubApi({ 'POST /api/imports/': () => jsonResponse(importData(), 201) })
    const { wrapper, router } = await mountRoute('/imports/new')

    expect(wrapper.get('[data-test="upload-button"]').attributes('disabled')).toBeDefined() // nothing chosen yet
    await chooseFile(wrapper)
    expect(wrapper.get('[data-test="chosen-file"]').text()).toContain('september.csv')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
    expect(router.currentRoute.value.fullPath).toBe(`/imports/${IMPORT_ID}`)
  })

  it('accepts a file dropped onto the drop zone', async () => {
    const fetchMock = stubApi({ 'POST /api/imports/': () => jsonResponse(importData(), 201) })
    const { wrapper } = await mountRoute('/imports/new')
    const dropped = new File(['a,b\n'], 'dropped.csv', { type: 'text/csv' })

    await wrapper.get('[data-test="drop-zone"]').trigger('drop', { dataTransfer: { files: [dropped] } })
    expect(wrapper.get('[data-test="chosen-file"]').text()).toContain('dropped.csv')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const [, init] = fetchMock.mock.calls.find(([, requestInit]) => requestInit?.method === 'POST')!
    expect((init!.body as FormData).get('file')).toBe(dropped)
  })

  it('shows why a file was rejected', async () => {
    stubApi({
      'POST /api/imports/': () =>
        errorResponse(400, 'VALIDATION_ERROR', 'The file is missing required columns: amount.'),
    })
    const { wrapper, router } = await mountRoute('/imports/new')

    await chooseFile(wrapper)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-test="form-error"]').text()).toContain('missing required columns: amount')
    expect(router.currentRoute.value.fullPath).toBe('/imports/new')
  })
})
