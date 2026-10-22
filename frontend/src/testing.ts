import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import PrimeVue from 'primevue/config'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import { vi } from 'vitest'
import { createMemoryHistory, createRouter, type RouteComponent, type RouteRecordRaw, RouterView } from 'vue-router'

import type { Account, ImportBatch, ImportRowError, Transaction } from '@/api/client'
import { routes } from '@/router'

type Handler = (url: URL, init: RequestInit) => Response | Promise<Response>
type FetchMock = ReturnType<typeof vi.fn<(input: string, init?: RequestInit) => Promise<Response>>>

/** A JSON response, the way the API sends one. */
export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** An API error in the standard `{"error": {...}}` shape. */
export function errorResponse(status: number, type: string, message: string, fields?: Record<string, string[]>) {
  return jsonResponse({ error: { type, message, ...(fields ? { fields } : {}) } }, status)
}

/**
 * Replace `fetch` with a fake API. `handlers` maps "METHOD /api/path/" to a function returning the response.
 * Unhandled requests fail the test loudly. Returns the mock, so tests can inspect the requests made.
 */
export function stubApi(handlers: Record<string, Handler>): FetchMock {
  const fetchMock = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input, 'http://localhost')
    const key = `${init.method ?? 'GET'} ${url.pathname}`
    const handler = handlers[key]
    if (!handler) {
      throw new Error(`Unexpected API request: ${key}`)
    }
    return handler(url, init)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** The parsed JSON body of the request the mock received for "METHOD /api/path/". */
export function requestBody(fetchMock: FetchMock, key: string): unknown {
  const call = fetchMock.mock.calls.find(
    ([input, init]) => `${init?.method ?? 'GET'} ${new URL(input, 'http://localhost').pathname}` === key,
  )
  if (!call) {
    throw new Error(`No request made: ${key}`)
  }
  return JSON.parse(String(call[1]?.body))
}

/** The query parameters of the most recent request to `path`. */
export function lastQuery(fetchMock: FetchMock, path: string): Record<string, string> {
  const urls = fetchMock.mock.calls
    .map(([input]) => new URL(input, 'http://localhost'))
    .filter((url) => url.pathname === path)
  const last = urls.at(-1)
  if (!last) {
    throw new Error(`No request made to ${path}`)
  }
  return Object.fromEntries(last.searchParams)
}

/**
 * The app's routes with every lazily loaded page loaded up front, so navigating in a test finishes
 * within a single `flushPromises()` instead of waiting on dynamic imports.
 */
async function eagerRoutes(): Promise<RouteRecordRaw[]> {
  return Promise.all(
    routes.map(async (route) => {
      if (typeof route.component !== 'function') {
        return route
      }
      const loaded = await (route.component as () => Promise<{ default: RouteComponent }>)()
      return { ...route, component: loaded.default } as RouteRecordRaw
    }),
  )
}

/**
 * Render the app's router at `path` (with a toast area), with PrimeVue installed, and wait for the page's
 * requests to settle.
 * Dialogs render in place (no teleport), so their buttons can be found like any other element.
 */
export async function mountRoute(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: await eagerRoutes() })
  await router.push(path)
  await router.isReady()
  // The page plus a toast area (as App renders), so tests can check toast messages via `[data-test="toast"]`.
  const page = defineComponent({
    render: () => [h(Toast, { pt: { message: { 'data-test': 'toast' } } }), h(RouterView)],
  })
  const wrapper = mount(page, {
    global: { plugins: [router, [PrimeVue, { theme: 'none' }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return { wrapper, router }
}

export const ACCOUNT_ID = '11111111-1111-1111-1111-111111111111'
export const TRANSACTION_ID = '22222222-2222-2222-2222-222222222222'

/** An account as the API returns it. */
export function accountData(overrides: Partial<Account> = {}): Account {
  return {
    id: ACCOUNT_ID,
    account_number: 'ACCT1',
    holder_name: 'Ada Lovelace',
    email: 'ada@example.com',
    status: 'OPEN',
    balance: '0.00',
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    ...overrides,
  }
}

/** A transaction as the API returns it. */
export function transactionData(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: TRANSACTION_ID,
    account: ACCOUNT_ID,
    direction: 'CREDIT',
    amount: '125.50',
    transaction_date: '2026-09-01',
    reference_id: 'REF-1',
    description: 'Paycheck',
    import_batch: null,
    created_at: '2026-09-01T12:00:00Z',
    ...overrides,
  }
}

/** A page of results, the way the API paginates lists. `count` is the total across all pages. */
export function page<T>(results: T[], count = results.length) {
  return { count, next: null, previous: null, results }
}

/** A promise you resolve later, for making a fake API response arrive out of order. */
export function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((settle) => {
    resolve = settle
  })
  return { promise, resolve }
}

/** Run a composable inside a real component (so watchers and lifecycle hooks work), and return what it returns. */
export function withSetup<T>(composable: () => T): T {
  let result!: T
  mount(
    defineComponent({
      setup() {
        result = composable()
        return () => null
      },
    }),
  )
  return result
}

export const IMPORT_ID = '33333333-3333-3333-3333-333333333333'

/** An import batch as the API returns it. */
export function importData(overrides: Partial<ImportBatch> = {}): ImportBatch {
  return {
    id: IMPORT_ID,
    original_filename: 'september.csv',
    status: 'COMPLETED',
    row_count: 3,
    error_count: 0,
    created_at: '2026-09-01T12:00:00Z',
    completed_at: '2026-09-01T12:00:01Z',
    ...overrides,
  }
}

/** One invalid row of a failed import, as the API returns it. */
export function rowErrorData(overrides: Partial<ImportRowError> = {}): ImportRowError {
  return {
    row_number: 2,
    raw_data: {
      account_number: '9999',
      direction: 'CREDIT',
      amount: '10.00',
      transaction_date: '2026-09-01',
      reference_id: 'REF-1',
      description: '',
    },
    errors: { account_number: ['No account with this number.'] },
    ...overrides,
  }
}
