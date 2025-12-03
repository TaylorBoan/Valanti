import type { ModelDefinition, PriceHistoryResponse, SummaryMetrics } from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:4000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...init
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request to ${path} failed`)
  }

  return (await response.json()) as T
}

export const api = {
  async getModels(): Promise<ModelDefinition[]> {
    const result = await request<{ data: ModelDefinition[] }>('/models')
    return result.data
  },
  getSummaryMetrics(modelKey?: string): Promise<SummaryMetrics> {
    const params = modelKey ? `?modelKey=${encodeURIComponent(modelKey)}` : ''
    return request(`/metrics/summary${params}`)
  },
  getPriceHistory(modelKey: string): Promise<PriceHistoryResponse> {
    return request(`/models/${modelKey}/price-history`)
  }
}
