import type { TransactionDirection } from '@/api/client'

const MONEY_FORMAT = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const SIGNED_MONEY_FORMAT = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  signDisplay: 'exceptZero',
})
const DATE_FORMAT = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
const DATE_TIME_FORMAT = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' })

/**
 * Format an API amount (a decimal string like "-1234.50") as US dollars. With `showSign`, positive amounts get
 * a "+" too, for money moving in and out. The string is formatted as-is, never converted to a floating-point
 * number, so no cent is ever lost.
 */
export function formatMoney(amount: string, { showSign = false } = {}): string {
  return (showSign ? SIGNED_MONEY_FORMAT : MONEY_FORMAT).format(amount as Intl.StringNumericLiteral)
}

/** A transaction's effect on the balance: credits as they are, debits negated. */
export function signedAmount(direction: TransactionDirection, amount: string): string {
  return direction === 'DEBIT' ? `-${amount}` : amount
}

/** Turn an amount typed into a number input into the 2-decimal string the API expects. */
export function toMoneyString(amount: number): string {
  return amount.toFixed(2)
}

/** Format an API date ("2026-09-01") for display, without shifting it into another day by time zone. */
export function formatDate(isoDate: string): string {
  return DATE_FORMAT.format(fromIsoDate(isoDate))
}

/** Turn an API date ("2026-09-01") into a local Date at midnight on that calendar day. */
export function fromIsoDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year!, month! - 1, day!)
}

/** Format an API timestamp for display, in the viewer's time zone. */
export function formatDateTime(isoDateTime: string): string {
  return DATE_TIME_FORMAT.format(new Date(isoDateTime))
}

/** Turn a picked date into the API's date format, using the calendar day the user picked. */
export function toIsoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** Up to two initials for an avatar: the first and last words of a name ("Ada Lovelace" → "AL"). */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  if (!words.length) {
    return '?'
  }
  const first = words[0]!
  const last = words.length > 1 ? words[words.length - 1]! : ''
  return `${first[0]}${last[0] ?? ''}`.toUpperCase()
}
