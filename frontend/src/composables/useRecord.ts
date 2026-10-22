import { type Ref, ref, type WatchSource, watch } from 'vue'

import { ApiError, describeError } from '@/api/client'

/**
 * Load one record by id, and reload it whenever the id changes.
 *
 * Returns the record (null until loaded), whether the API said it doesn't exist (`notFound`), and a message
 * for any other failure (`loadError`). If the id changes while a load is in flight, the older response is
 * ignored, so a slow answer can never replace the newer record. Without an id, nothing loads.
 */
export function useRecord<T>(id: WatchSource<string | undefined>, load: (id: string) => Promise<T>) {
  const record = ref(null) as Ref<T | null>
  const notFound = ref(false)
  const loadError = ref<string | null>(null)
  const loading = ref(false)
  let latestRequest = 0

  watch(
    id,
    async (recordId) => {
      const request = ++latestRequest
      record.value = null
      notFound.value = false
      loadError.value = null
      if (!recordId) {
        loading.value = false
        return
      }
      loading.value = true
      try {
        const loaded = await load(recordId)
        if (request === latestRequest) {
          record.value = loaded
        }
      } catch (error) {
        if (request !== latestRequest) {
          return
        }
        if (error instanceof ApiError && error.status === 404) {
          notFound.value = true
        } else {
          loadError.value = describeError(error).message
        }
      } finally {
        if (request === latestRequest) {
          loading.value = false
        }
      }
    },
    { immediate: true },
  )

  return { record, notFound, loadError, loading }
}
