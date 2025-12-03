# Corsa API

Supabase-backed REST API that exposes curated model metadata, KPI metrics, and historical price data for the listings dashboard.

## Getting Started

```bash
pnpm install
pnpm --filter api dev
```

Create a `.env` file (or use the root `.env`) with the following keys:

```
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_SCHEMA=public
LISTINGS_TABLE=listings
PORT=4000
ALLOWED_ORIGIN=http://localhost:5173
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Simple readiness probe |
| GET | `/api/models` | Returns the curated make/model catalog used by the dashboard |
| GET | `/api/models/:modelKey/price-history` | Returns the normalized price timeline for a model |
| GET | `/api/metrics/summary` | Returns KPI data (total listings, unique VINs, price delta) |

### `/api/models`

```json
{
  "data": [
    {
      "key": "lamborghini-aventador",
      "make": "Lamborghini",
      "label": "Aventador"
    }
  ]
}
```

### `/api/models/:key/price-history`

```json
{
  "model": {
    "key": "lamborghini-aventador",
    "make": "Lamborghini",
    "label": "Aventador"
  },
  "stats": {
    "minPrice": 429000,
    "maxPrice": 489999,
    "medianPrice": 459000,
    "latestPrice": 459000,
    "lastUpdated": "2025-09-07T13:34:03.000Z",
    "totalPoints": 42
  },
  "points": [
    {
      "date": "2024-09-02T00:59:11.000Z",
      "price": 469985,
      "vin": "ZHWUV4ZD1KLA08099",
      "source": "PrivateAuto"
    }
  ]
}
```

### `/api/metrics/summary`

```json
{
  "totalListings": 251238,
  "uniqueVins": 13244,
  "averageAskingPrice": 451200,
  "priceTrend": {
    "current": 451200,
    "previous": 444800,
    "delta": 6400
  },
  "updatedAt": "2025-12-03T09:00:00.000Z"
}
```
