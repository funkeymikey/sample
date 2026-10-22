import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import App from '@/App.vue'
import { routes } from '@/router'
import { jsonResponse } from '@/testing'

let router: Router

/** Mount the app with its own router, so navigating in one test can't affect another. */
async function mountApp() {
  router = createRouter({ history: createMemoryHistory(), routes })
  const wrapper = mount(App, { global: { plugins: [router, [PrimeVue, { theme: 'none' }], ToastService] } })
  await flushPromises()
  return wrapper
}

async function apiStatusShownFor(fetchResult: Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(fetchResult))

  const wrapper = await mountApp()

  return wrapper.get('[data-test="api-status"]').text()
}

describe('App layout', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('links the Ledger brand to the accounts list', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'ok' })))

    const wrapper = await mountApp()

    expect(wrapper.get('[data-test="home-link"]').attributes('href')).toBe('/accounts')
  })
})

describe('App navigation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('links to both sections, highlighting the current one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ count: 0, next: null, previous: null, results: [] })),
    )
    const wrapper = await mountApp()

    await router.push('/imports')
    await flushPromises()

    expect(wrapper.get('[data-test="nav-accounts"]').attributes('href')).toBe('/accounts')
    expect(wrapper.get('[data-test="nav-imports"]').attributes('href')).toBe('/imports')
    expect(wrapper.get('[data-test="nav-imports"]').classes()).toContain('active')
    expect(wrapper.get('[data-test="nav-accounts"]').classes()).not.toContain('active')
  })
})

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
