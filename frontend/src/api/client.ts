import type { components } from './schema'

export type Health = components['schemas']['Health']

/** The body of every error the API returns. */
export type ErrorResponse = components['schemas']['ErrorResponse']
export type ErrorType = components['schemas']['ErrorTypeEnum']

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

/** GET a JSON resource from the API, typed by the generated schema. Throws `ApiError` on a non-2xx response. */
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { headers: { Accept: 'application/json' } })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, body)
  }
  return body as T
}

/** Check the API's health. Throws `ApiError` if it isn't healthy (e.g. a 500 when its database is down). */
export function getHealth(): Promise<Health> {
  return getJson<Health>('/health/')
}
