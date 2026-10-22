import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import App from '@/App.vue'
import router from '@/router'

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

async function apiStatusShownFor(fetchResult: Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(fetchResult))

  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()

  return wrapper.get('[data-test="api-status"]').text()
}

describe('App API status', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows ok when the API and database are up', async () => {
    expect(await apiStatusShownFor(Promise.resolve(jsonResponse({ status: 'ok' }, 200)))).toBe('ok')
  })

  it('shows error when the API answers with an error response (e.g. database down)', async () => {
    const errorBody = { error: { type: 'INTERNAL_ERROR', message: 'An error occurred while handling your request.' } }

    expect(await apiStatusShownFor(Promise.resolve(jsonResponse(errorBody, 500)))).toBe('error')
  })

  it('shows unreachable when the request never gets a response', async () => {
    expect(await apiStatusShownFor(Promise.reject(new TypeError('Failed to fetch')))).toBe('unreachable')
  })

  it('shows unreachable when something other than the API answers', async () => {
    // e.g. the Vite dev proxy when Django isn't running
    expect(await apiStatusShownFor(Promise.resolve(new Response('', { status: 500 })))).toBe('unreachable')
  })
})
