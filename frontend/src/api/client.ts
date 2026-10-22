import type { components, paths } from './schema'

type Schemas = components['schemas']

export type Health = Schemas['Health']
export type Account = Schemas['Account']
export type AccountRequest = Schemas['AccountRequest']
export type AccountUpdateRequest = Schemas['PatchedAccountUpdateRequest']
export type AccountStatus = Schemas['AccountStatusEnum']
export type AccountPage = Schemas['PaginatedAccountList']
export type AccountListParams = NonNullable<paths['/api/accounts/']['get']['parameters']['query']>
export type Transaction = Schemas['Transaction']
export type TransactionRequest = Schemas['TransactionRequest']
export type TransactionDirection = Schemas['TransactionDirectionEnum']
export type TransactionPage = Schemas['PaginatedTransactionList']
export type TransactionListParams = NonNullable<paths['/api/accounts/{id}/transactions/']['get']['parameters']['query']>

/** Rows per page in every paginated list. Must match `PAGE_SIZE` in the backend's REST_FRAMEWORK settings. */
export const API_PAGE_SIZE = 25

/** The body of every error the API returns. */
export type ErrorResponse = Schemas['ErrorResponse']
export type ErrorType = Schemas['ErrorTypeEnum']

/** Thrown when a request gets a non-2xx response. `body` is the parsed JSON, or null if there was none. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API request failed with status ${status}`)
  }

  /** The API's own error details, or null if the response didn't come from the API (e.g. a proxy error). */
  get errorResponse(): ErrorResponse | null {
    return isErrorResponse(this.body) ? this.body : null
  }
}

function isErrorResponse(body: unknown): body is ErrorResponse {
  return typeof body === 'object' && body !== null && 'error' in body && typeof body.error === 'object'
}

const UNREACHABLE_MESSAGE = "Couldn't reach the server. Check your connection and try again."

/**
 * What to show the user for a failed request: the API's message and per-field errors, or a generic
 * "couldn't reach the server" message when the API never answered.
 */
export function describeError(error: unknown): { message: string; fields: Record<string, string[]> } {
  if (error instanceof ApiError && error.errorResponse) {
    const { message, fields } = error.errorResponse.error
    return { message, fields: fields ?? {} }
  }
  return { message: UNREACHABLE_MESSAGE, fields: {} }
}

type QueryValue = string | number | null | undefined

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH',
  path: string,
  options: { query?: Record<string, QueryValue>; body?: unknown } = {},
): Promise<T> {
  const query = new URLSearchParams()
  for (const [name, value] of Object.entries(options.query ?? {})) {
    if (value !== null && value !== undefined && value !== '') {
      query.set(name, String(value))
    }
  }
  const queryString = query.size ? `?${query}` : ''
  const hasBody = options.body !== undefined
  const response = await fetch(`/api${path}${queryString}`, {
    method,
    headers: { Accept: 'application/json', ...(hasBody ? { 'Content-Type': 'application/json' } : {}) },
    body: hasBody ? JSON.stringify(options.body) : undefined,
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, body)
  }
  return body as T
}

/** Check the API's health. Throws `ApiError` if it isn't healthy (e.g. a 500 when its database is down). */
export function getHealth(): Promise<Health> {
  return request<Health>('GET', '/health/')
}

/** One page of accounts, with balances, matching the search, status filter and ordering. */
export function listAccounts(params: AccountListParams): Promise<AccountPage> {
  return request<AccountPage>('GET', '/accounts/', { query: params })
}

/** One account, with its balance. */
export function getAccount(accountId: string): Promise<Account> {
  return request<Account>('GET', `/accounts/${accountId}/`)
}

/** Open a new account. */
export function createAccount(account: AccountRequest): Promise<Account> {
  return request<Account>('POST', '/accounts/', { body: account })
}

/** Change an account's name, email or status (set status to CLOSED to close it). */
export function updateAccount(accountId: string, changes: AccountUpdateRequest): Promise<Account> {
  return request<Account>('PATCH', `/accounts/${accountId}/`, { body: changes })
}

/** One page of an account's transactions, newest first, matching the filters. */
export function listAccountTransactions(accountId: string, params: TransactionListParams): Promise<TransactionPage> {
  return request<TransactionPage>('GET', `/accounts/${accountId}/transactions/`, { query: params })
}

/** Post a transaction to an account. */
export function postTransaction(accountId: string, transaction: TransactionRequest): Promise<Transaction> {
  return request<Transaction>('POST', `/accounts/${accountId}/transactions/`, { body: transaction })
}

/** One transaction. */
export function getTransaction(transactionId: string): Promise<Transaction> {
  return request<Transaction>('GET', `/transactions/${transactionId}/`)
}
