import { type Ref, ref, watch } from 'vue'

import { ApiError, describeError } from '@/api/client'

/**
 * Load one page of a list from the API, and reload whenever `params` changes (a filter, the sort, the page).
 *
 * Only the latest request's results are shown: if an older, slower request answers last, it's ignored. If the
 * requested page no longer exists (the API answers 404 for a page past the end), `onPageGone` is called, so the
 * page can send the user back to page 1 instead of showing an error.
 */
export function usePagedList<Params extends { page: number }, Item>(
  params: () => Params,
  fetchPage: (params: Params) => Promise<{ count: number; results: Item[] }>,
  options: { onPageGone?: () => void } = {},
) {
  const items = ref([]) as Ref<Item[]>
  const total = ref(0)
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  let latestRequest = 0

  watch(
    params,
    async (currentParams) => {
      const request = ++latestRequest
      loading.value = true
      loadError.value = null
      try {
        const listPage = await fetchPage(currentParams)
        if (request === latestRequest) {
          items.value = listPage.results
          total.value = listPage.count
        }
      } catch (error) {
        if (request !== latestRequest) {
          return
        }
        if (error instanceof ApiError && error.status === 404 && currentParams.page > 1) {
          options.onPageGone?.()
          return
        }
        items.value = []
        total.value = 0
        loadError.value = describeError(error).message
      } finally {
        if (request === latestRequest) {
          loading.value = false
        }
      }
    },
    { immediate: true },
  )

  return { items, total, loading, loadError }
}
