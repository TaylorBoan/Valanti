import type { ModelDefinition } from '../types/api'
import './ModelSelector.css'

type Props = {
  models: ModelDefinition[]
  value: string
  onChange: (key: string) => void
  disabled?: boolean
}

export function ModelSelector({ models, value, onChange, disabled }: Props) {
  const hasSelectableOption = models.some((model) => model.hasPriceData !== false)
  return (
    <label className="model-selector">
      <span className="model-selector__label">Model</span>
      <select
        className="model-selector__select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !models.length || !hasSelectableOption}
      >
        {models.map((model) => (
          <option
            key={model.key}
            value={model.key}
            disabled={model.hasPriceData === false}
            title={model.hasPriceData === false ? 'Pricing data unavailable' : undefined}
          >
            {model.make} · {model.label}
          </option>
        ))}
      </select>
    </label>
  )
}
