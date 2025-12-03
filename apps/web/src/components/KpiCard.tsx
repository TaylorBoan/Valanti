import clsx from 'clsx'
import './KpiCard.css'

type Trend = 'up' | 'down' | 'neutral'

type Props = {
  title: string
  value: string
  subtitle?: string
  trend?: {
    label: string
    direction: Trend
  }
}

export function KpiCard({ title, value, subtitle, trend }: Props) {
  return (
    <article className="kpi-card">
      <div className="kpi-card__top">
        <p className="kpi-card__title">{title}</p>
        {trend && (
          <span className={clsx('kpi-card__trend', `kpi-card__trend--${trend.direction}`)}>
            {trend.label}
          </span>
        )}
      </div>
      <p className="kpi-card__value">{value}</p>
      {subtitle && <p className="kpi-card__subtitle">{subtitle}</p>}
    </article>
  )
}
