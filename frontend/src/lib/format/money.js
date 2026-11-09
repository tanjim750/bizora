/**
 * Formats a monetary amount with an ISO currency code and 2 decimal places.
 * Example: money(2500, 'BDT') -> "BDT 2,500.00"
 */
export function money(amount, currency = 'BDT') {
  if (amount === 'UNAVAILABLE') return 'UNAVAILABLE'
  if (amount === null || amount === undefined || amount === '') return '—'

  const num = typeof amount === 'number' ? amount : parseFloat(String(amount))
  if (Number.isNaN(num)) return '—'

  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })

  return `${currency} ${formatted}`
}

export default money
