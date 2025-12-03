import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'
import { formatCurrency, formatDate } from '../lib/format'
import type { PricePoint } from '../types/api'
import './PriceHistoryChart.css'

type Props = {
  points: PricePoint[]
  loading?: boolean
}

export function PriceHistoryChart({ points, loading }: Props) {
  if (loading) {
    return <div className="chart chart--loading">Loading price history…</div>
  }

  if (!points.length) {
    return <div className="chart chart--empty">No pricing data yet for this model.</div>
  }

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={points} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.3)" />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => formatDate(value)}
            stroke="var(--muted-light)"
            minTickGap={32}
          />
          <YAxis
            tickFormatter={(value) => formatCurrency(value as number)}
            stroke="var(--muted-light)"
            width={96}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#38bdf8"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

type TooltipProps = {
  active?: boolean
  payload?: Array<{ value: number; payload: PricePoint }>
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) {
    return null
  }

  const { payload: point } = payload[0]
  return (
    <div className="chart-tooltip">
      <p>{formatDate(point.date)}</p>
      <p className="chart-tooltip__price">{formatCurrency(point.price)}</p>
      {point.source && <p className="chart-tooltip__meta">Source: {point.source}</p>}
      {point.vin && <p className="chart-tooltip__meta">VIN: {point.vin}</p>}
    </div>
  )
}
