# Corsa Market Intelligence MVP

Lightweight monorepo housing the Supabase-backed API (`apps/api`) and the React dashboard (`apps/web`) that visualizes historical pricing for high-end exotic vehicles scraped from AutoTempest.

## Prerequisites

- Node.js 20+
- pnpm 10+
- Supabase project with the raw listings table (`clean_listings` schema) accessible via service-role key

## Getting Started

```bash
pnpm install
cp .env.example .env # add Supabase credentials & API base URL
pnpm dev:api        # starts the Express API on http://localhost:4000
pnpm dev:web        # starts the Vite dev server on http://localhost:5173
```

The dashboard expects `VITE_API_BASE_URL` to point at the Express server (defaults to `http://localhost:4000/api`).

## Architecture

- **apps/api** – Express + TypeScript server that queries Supabase, calculates KPI metrics, and returns normalized price history.
- **apps/web** – Vite + React front-end with a hero, KPI cards, model selector, and Recharts-powered timeline.
- **Shared tooling** – pnpm workspaces and root scripts (`pnpm dev`, `pnpm lint`, etc.).

## Key Endpoints

- `GET /api/models` – curated model catalog used by the selector.
- `GET /api/models/:modelKey/price-history` – listing-derived timeline for a model.
- `GET /api/metrics/summary` – KPI data (total listings, unique VINs, price delta, avg price).

## Deployment Notes

- API can be deployed to Render, Fly.io, Railway, or Supabase Functions. Provide Supabase service-role key securely.
- Frontend can live on Netlify/Vercel. Configure `VITE_API_BASE_URL` to point at the deployed API.
- Apply caching/CDN headers around `/api/*` as needed; responses are already cached in-memory for 2 minutes.
