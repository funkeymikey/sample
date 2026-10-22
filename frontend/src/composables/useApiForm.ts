import { ref } from 'vue'

import { describeError } from '@/api/client'

/**
 * The saving state and errors for a form that saves through the API.
 *
 * `submit(save)` runs `save`, tracking `saving`. If the API rejects it, field errors go to `fieldErrors` (shown
 * next to their fields) and anything else, like a rule violation or an unreachable server, goes to `formError`
 * (shown above the form).
 */
export function useApiForm() {
  const saving = ref(false)
  const fieldErrors = ref<Record<string, string[]>>({})
  const formError = ref<string | null>(null)

  async function submit(save: () => Promise<void>) {
    saving.value = true
    fieldErrors.value = {}
    formError.value = null
    try {
      await save()
    } catch (error) {
      const { message, fields } = describeError(error)
      fieldErrors.value = fields
      formError.value = Object.keys(fields).length ? null : message
    } finally {
      saving.value = false
    }
  }

  return { saving, fieldErrors, formError, submit }
}
