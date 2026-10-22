import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { ApiError } from '@/api/client'
import { useRecord } from '@/composables/useRecord'
import { deferred, withSetup } from '@/testing'

const notFoundError = new ApiError(404, { error: { type: 'NOT_FOUND', message: 'Not found.' } })

describe('useRecord', () => {
  it('loads the record', async () => {
    const { record, notFound, loadError } = withSetup(() => useRecord(ref('a'), async (id) => ({ id })))
    await flushPromises()

    expect(record.value).toEqual({ id: 'a' })
    expect(notFound.value).toBe(false)
    expect(loadError.value).toBeNull()
  })

  it('reports a 404 as not found, and anything else as a load error', async () => {
    const missing = withSetup(() => useRecord(ref('a'), async () => Promise.reject(notFoundError)))
    const broken = withSetup(() => useRecord(ref('a'), async () => Promise.reject(new TypeError('Failed to fetch'))))
    await flushPromises()

    expect([missing.notFound.value, missing.loadError.value]).toEqual([true, null])
    expect(broken.notFound.value).toBe(false)
    expect(broken.loadError.value).toBe("Couldn't reach the server. Check your connection and try again.")
  })

  it('reloads when the id changes, ignoring a slower response for the old id', async () => {
    const id = ref('old')
    const slowOldResponse = deferred<{ id: string }>()
    const { record } = withSetup(() =>
      useRecord(id, async (recordId) => (recordId === 'old' ? slowOldResponse.promise : { id: recordId })),
    )

    id.value = 'new'
    await flushPromises()
    slowOldResponse.resolve({ id: 'old' })
    await flushPromises()

    expect(record.value).toEqual({ id: 'new' })
  })

  it('does nothing without an id (e.g. a form opening a new record)', async () => {
    const { record, loading } = withSetup(() => useRecord(ref(undefined), async (id: string) => ({ id })))
    await flushPromises()

    expect(record.value).toBeNull()
    expect(loading.value).toBe(false)
  })
})
