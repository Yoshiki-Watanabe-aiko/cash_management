const currencyFormatter = new Intl.NumberFormat('ja-JP', {
  style: 'currency',
  currency: 'JPY',
  maximumFractionDigits: 0,
})

const percentFormatter = new Intl.NumberFormat('ja-JP', {
  style: 'percent',
  maximumFractionDigits: 1,
})

export function formatCurrency(amount: number | string): string {
  return currencyFormatter.format(Number(amount))
}

export function formatPercent(ratio: number | string): string {
  return percentFormatter.format(Number(ratio))
}

export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${year}/${month}/${day}`
}
