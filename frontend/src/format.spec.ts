import { describe, expect, it } from 'vitest'

import { formatDate, formatMoney, initials, toIsoDate, toMoneyString } from '@/format'

describe('formatMoney', () => {
  it.each([
    ['0.00', '$0.00'],
    ['1234.56', '$1,234.56'],
    ['-75.00', '-$75.00'],
    ['19999999999.97', '$19,999,999,999.97'],
  ])('formats %s as %s', (amount, expected) => {
    expect(formatMoney(amount)).toBe(expected)
  })

  it('can show the sign of positive amounts too, for money moving in and out', () => {
    expect(formatMoney('100.00', { showSign: true })).toBe('+$100.00')
    expect(formatMoney('-40.25', { showSign: true })).toBe('-$40.25')
  })

  it('keeps every cent of large amounts (no floating-point rounding)', () => {
    expect(formatMoney('9007199254740993.01')).toBe('$9,007,199,254,740,993.01')
  })
})

describe('toMoneyString', () => {
  it.each([
    [125.5, '125.50'],
    [0.1 + 0.2, '0.30'],
    [9999999999.99, '9999999999.99'],
  ])('turns %s into %s', (amount, expected) => {
    expect(toMoneyString(amount)).toBe(expected)
  })
})

describe('dates', () => {
  it('formats an API date without shifting it across time zones', () => {
    expect(formatDate('2026-09-01')).toBe('Sep 1, 2026')
  })

  it('turns a picked date into the API format using the local calendar day', () => {
    expect(toIsoDate(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05')
  })
})

describe('initials', () => {
  it.each([
    ['Ada Lovelace', 'AL'],
    ['oprah', 'O'],
    ['John Ronald Reuel Tolkien', 'JT'],
    ['  bob   hope ', 'BH'],
    ['', '?'],
  ])('turns %j into %s', (name, expected) => {
    expect(initials(name)).toBe(expected)
  })
})
