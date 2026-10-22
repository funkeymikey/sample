import { type LocationQuery, type LocationQueryRaw, useRouter } from 'vue-router'

import { fromIsoDate, toIsoDate } from '@/format'

/** A query parameter's value (the first one, if it's repeated), or undefined if it's missing. */
export function queryValue(query: LocationQuery, name: string): string | undefined {
  const value = query[name]
  return (Array.isArray(value) ? value[0] : value) ?? undefined
}

/** A query parameter that must be one of `choices`; anything else counts as not set. */
export function queryChoice<T extends string>(query: LocationQuery, name: string, choices: readonly T[]): T | null {
  const value = queryValue(query, name)
  return choices.find((choice) => choice === value) ?? null
}

/** The `page` query parameter as a page number, defaulting to 1 when missing or invalid. */
export function queryPage(query: LocationQuery): number {
  const page = Number(queryValue(query, 'page'))
  return Number.isInteger(page) && page > 0 ? page : 1
}

/** A query parameter holding a real calendar date ("2026-09-01"); anything else, like "2026-02-30", is null. */
export function queryDate(query: LocationQuery, name: string): Date | null {
  const value = queryValue(query, name)
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null
  }
  const date = fromIsoDate(value)
  return toIsoDate(date) === value ? date : null // rejects dates that roll over, like Feb 30 → Mar 2
}

/** Query parameters with empty values left out, so URLs only show what's actually set. */
export function compactQuery(values: Record<string, string | number | null | undefined>): LocationQueryRaw {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value !== null && value !== undefined && value !== '')
      .map(([name, value]) => [name, String(value)]),
  )
}

type QueryState = Record<string, string | number | null>

/**
 * Returns `updateQuery(changes)`, which merges `changes` into the page's state and puts the result in the URL
 * (replacing the history entry, so Back still leaves the page instead of undoing each filter change).
 *
 * `currentState` reads the state from the URL; `toQuery` turns a state into query parameters. Updates made
 * in quick succession build on each other: until the URL catches up, each one starts from the last one requested,
 * so no change is lost.
 */
export function useQueryUpdater<State extends QueryState>(
  currentState: () => State,
  toQuery: (state: State) => LocationQueryRaw,
): (changes: Partial<State>) => void {
  const router = useRouter()
  let pendingState: State | null = null
  return (changes) => {
    const nextState = { ...(pendingState ?? currentState()), ...changes }
    pendingState = nextState
    router.replace({ query: toQuery(nextState) }).finally(() => {
      if (pendingState === nextState) {
        pendingState = null
      }
    })
  }
}
