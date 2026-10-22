import { describe, expect, it } from 'vitest'

import { compactQuery, queryChoice, queryDate, queryPage, queryValue } from '@/routeQuery'

describe('reading the query string', () => {
  it('takes the first value of a repeated parameter', () => {
    expect(queryValue({ search: ['ada', 'grace'] }, 'search')).toBe('ada')
    expect(queryValue({}, 'search')).toBeUndefined()
  })

  it('accepts only the allowed choices', () => {
    expect(queryChoice({ status: 'OPEN' }, 'status', ['OPEN', 'CLOSED'])).toBe('OPEN')
    expect(queryChoice({ status: 'open' }, 'status', ['OPEN', 'CLOSED'])).toBeNull()
  })

  it.each([
    ['3', 3],
    [undefined, 1],
    ['0', 1],
    ['-2', 1],
    ['2.5', 1],
    ['two', 1],
  ])('reads page %s as %s', (page, expected) => {
    expect(queryPage(page === undefined ? {} : { page })).toBe(expected)
  })

  it.each([
    ['2026-09-01', new Date(2026, 8, 1)],
    ['2026-02-30', null], // would roll over to March 2
    ['2026-9-1', null],
    ['yesterday', null],
  ])('reads date %s', (value, expected) => {
    expect(queryDate({ from: value }, 'from')).toEqual(expected)
  })
})

describe('compactQuery', () => {
  it('leaves out empty values and turns the rest into strings', () => {
    expect(compactQuery({ search: '', status: null, ordering: undefined, page: 2, direction: 'DEBIT' })).toEqual({
      page: '2',
      direction: 'DEBIT',
    })
  })
})
