import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { ApiError } from '@/api/client'
import { usePagedList } from '@/composables/usePagedList'
import { deferred, page, withSetup } from '@/testing'

describe('usePagedList', () => {
  it('loads the page for the current filters', async () => {
    const filter = ref('open')
    const fetchPage = vi.fn(async () => page(['a', 'b'], 30))

    const { items, total, loading } = withSetup(() =>
      usePagedList(() => ({ filter: filter.value, page: 1 }), fetchPage),
    )
    await flushPromises()

    expect(fetchPage).toHaveBeenCalledWith({ filter: 'open', page: 1 })
    expect(items.value).toEqual(['a', 'b'])
    expect(total.value).toBe(30)
    expect(loading.value).toBe(false)
  })

  it('shows only the latest request, even when an older one answers last', async () => {
    const filter = ref('first')
    const slowFirstResponse = deferred<ReturnType<typeof page<string>>>()
    const { items } = withSetup(() =>
      usePagedList(
        () => ({ filter: filter.value, page: 1 }),
        async ({ filter: value }) => (value === 'first' ? slowFirstResponse.promise : page(['second'])),
      ),
    )

    filter.value = 'second'
    await flushPromises()
    slowFirstResponse.resolve(page(['first']))
    await flushPromises()

    expect(items.value).toEqual(['second'])
  })

  it('calls onPageGone when a page past the end is requested', async () => {
    const onPageGone = vi.fn()
    const notFound = new ApiError(404, { error: { type: 'NOT_FOUND', message: 'Invalid page.' } })

    const { loadError } = withSetup(() =>
      usePagedList(
        () => ({ page: 5 }),
        async () => Promise.reject(notFound),
        { onPageGone },
      ),
    )
    await flushPromises()

    expect(onPageGone).toHaveBeenCalledOnce()
    expect(loadError.value).toBeNull()
  })

  it('reports other failures as a load error', async () => {
    const { loadError, items } = withSetup(() =>
      usePagedList(
        () => ({ page: 1 }),
        async () => Promise.reject(new TypeError('Failed to fetch')),
      ),
    )
    await flushPromises()

    expect(loadError.value).toBe("Couldn't reach the server. Check your connection and try again.")
    expect(items.value).toEqual([])
  })
})
