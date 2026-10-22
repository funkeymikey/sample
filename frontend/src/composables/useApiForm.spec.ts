import { describe, expect, it } from 'vitest'

import { ApiError } from '@/api/client'
import { useApiForm } from '@/composables/useApiForm'

function apiError(status: number, message: string, fields?: Record<string, string[]>) {
  return new ApiError(status, { error: { type: 'VALIDATION_ERROR', message, ...(fields ? { fields } : {}) } })
}

describe('useApiForm', () => {
  it('runs the save and tracks progress', async () => {
    const { submit, saving } = useApiForm()
    let savingDuringSave = false

    await submit(async () => {
      savingDuringSave = saving.value
    })

    expect(savingDuringSave).toBe(true)
    expect(saving.value).toBe(false)
  })

  it('puts field errors next to fields, and other errors above the form', async () => {
    const { submit, fieldErrors, formError } = useApiForm()

    await submit(async () => Promise.reject(apiError(400, 'Invalid request data.', { amount: ['Too small.'] })))
    expect(fieldErrors.value).toEqual({ amount: ['Too small.'] })
    expect(formError.value).toBeNull()

    await submit(async () => Promise.reject(apiError(409, 'Duplicate reference.')))
    expect(fieldErrors.value).toEqual({}) // cleared by the new attempt
    expect(formError.value).toBe('Duplicate reference.')
  })
})
