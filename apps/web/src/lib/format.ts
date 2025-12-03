import dayjs from 'dayjs'

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0
})

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0
})

export const formatCurrency = (value?: number | null) => {
  if (value === null || value === undefined) {
    return '—'
  }

  return currencyFormatter.format(value)
}

export const formatNumber = (value?: number | null) => {
  if (value === null || value === undefined) {
    return '—'
  }

  return numberFormatter.format(value)
}

export const formatDate = (value?: string | null) => {
  if (!value) {
    return '—'
  }

  return dayjs(value).format('MMM D, YYYY')
}

export const formatDelta = (value?: number | null) => {
  if (value === null || value === undefined) {
    return { label: '—', trend: 'neutral' as const }
  }

  const prefix = value > 0 ? '+' : ''
  const label = `${prefix}${currencyFormatter.format(Math.abs(value))}`
  const trend = value === 0 ? ('neutral' as const) : value > 0 ? ('up' as const) : ('down' as const)

  return { label, trend }
}
