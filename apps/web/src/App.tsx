import { useEffect, useMemo, useState } from 'react'
import { KpiCard } from './components/KpiCard'
import { ModelSelector } from './components/ModelSelector'
import { PriceHistoryChart } from './components/PriceHistoryChart'
import { api } from './lib/api'
import { formatCurrency, formatDate, formatDelta, formatNumber } from './lib/format'
import type { ModelDefinition, PriceHistoryResponse, SummaryMetrics } from './types/api'
import './App.css'

type LoadingState = {
  models: boolean
  metrics: boolean
  history: boolean
}

const initialLoading: LoadingState = {
  models: true,
  metrics: true,
  history: false
}

function App() {
  const [models, setModels] = useState<ModelDefinition[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [priceHistory, setPriceHistory] = useState<PriceHistoryResponse | null>(null)
  const [metrics, setMetrics] = useState<SummaryMetrics | null>(null)
  const [loading, setLoading] = useState<LoadingState>(initialLoading)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadModels = async () => {
      setLoading((state) => ({ ...state, models: true }))
      setError(null)
      try {
        const result = await api.getModels()
        setModels(result)
        if (result.length) {
          setSelectedModel((current) => {
            const stillValid = result.some(
              (model) => model.key === current && model.hasPriceData !== false
            )
            if (current && stillValid) {
              return current
            }
            const fallback = result.find((model) => model.hasPriceData !== false)
            return fallback?.key ?? ''
          })
        } else {
          setSelectedModel('')
        }
      } catch (err) {
        console.error(err)
        setError('Unable to load available models from the API.')
      } finally {
        setLoading((state) => ({ ...state, models: false }))
      }
    }

    const loadMetrics = async () => {
      setLoading((state) => ({ ...state, metrics: true }))
      setError(null)
      try {
        const summary = await api.getSummaryMetrics()
        setMetrics(summary)
      } catch (err) {
        console.error(err)
        setError('Unable to load KPI metrics from the API.')
      } finally {
        setLoading((state) => ({ ...state, metrics: false }))
      }
    }

    loadModels()
    loadMetrics()
  }, [])

  useEffect(() => {
    if (!selectedModel) {
      return
    }

    const loadHistory = async () => {
      setLoading((state) => ({ ...state, history: true }))
      setError(null)
      try {
        const history = await api.getPriceHistory(selectedModel)
        setPriceHistory(history)
      } catch (err) {
        console.error(err)
        setError('Unable to load price history for this model.')
      } finally {
        setLoading((state) => ({ ...state, history: false }))
      }
    }

    loadHistory()
  }, [selectedModel])

  const activeModel = useMemo(() => models.find((model) => model.key === selectedModel), [models, selectedModel])
  const priceDelta = formatDelta(metrics?.priceTrend.delta)

  return (
    <div className="dashboard">
      <header className="hero">
        <span className="hero__badge">Private preview</span>
        <h1>Valanti</h1>
        <p>
          250k+ scraped listings from AutoTempest unified in a single source of truth. Track live asking
          prices across the rarest models and spot directionally where the market is headed.
        </p>
        {metrics && <p className="hero__meta">Data refreshed {formatDate(metrics.updatedAt)}</p>}
      </header>

      {error && <div className="banner banner--error">{error}</div>}

      <section className="kpi-grid">
        <KpiCard title="Total listings" value={formatNumber(metrics?.totalListings)} />
        <KpiCard title="Unique VINs" value={formatNumber(metrics?.uniqueVins)} />
        <KpiCard
          title="Avg asking price (30d)"
          value={formatCurrency(metrics?.priceTrend.current)}
          subtitle="Window: last 30 days"
        />
        <KpiCard
          title="Delta vs prior 30d"
          value={formatCurrency(metrics?.priceTrend.previous)}
          subtitle="Prior 30-day window"
          trend={{ label: priceDelta.label, direction: priceDelta.trend }}
        />
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="panel__eyebrow">Historical pricing</p>
            <h2>{activeModel ? `${activeModel.make} ${activeModel.label}` : 'Select a model'}</h2>
            <p className="panel__subtitle">
              {priceHistory?.stats.totalPoints ? (
                <>
                  {priceHistory.stats.totalPoints} observations collected · Last updated{' '}
                  {formatDate(priceHistory.stats.lastUpdated)}
                </>
              ) : (
                'We aggregate raw listing data directly from Supabase in real time.'
              )}
            </p>
          </div>
          <ModelSelector
            models={models}
            value={selectedModel}
            onChange={setSelectedModel}
            disabled={loading.models}
          />
        </div>
        <PriceHistoryChart points={priceHistory?.points ?? []} loading={loading.history} />
      </section>
    </div>
  )
}

export default App
