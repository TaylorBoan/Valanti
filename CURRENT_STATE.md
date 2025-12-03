# Corsa – Current State (December 2025)

## High-Level Overview
- **Purpose:** Scrape and analyze ~250k luxury/exotic listings from AutoTempest, surface curated models, KPI summaries, and price history visualizations.
- **Stacks:** Turborepo monorepo with `apps/api` (Express + Supabase) and `apps/web` (Vite + React). Shared env via root `.env`.
- **Data source:** Supabase PostgREST pointing at schema `raw` and table `auto_tempest_scrape`. Service-role key is used server side.

## API (`apps/api`)
- **Server:** `tsx watch src/server.ts`, exposed at `http://localhost:4000`. CORS origin defaults to `*` but can be locked via `ALLOWED_ORIGIN`.
- **Config loading:** Resolves `.env`, `.env.local`, and `apps/api/.env` at project root. Validates with Zod (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, optional `SUPABASE_SCHEMA` ∈ {public, graphql_public, raw}).
- **Supabase client:** Uses service role with non-persistent auth. Custom headers add `Accept-Profile` so PostgREST queries the selected schema.
- **Caching:** Simple in-memory `node-cache` memoization for price history per model (no TTL set, default 5 min), summary metrics (TTL 120 s), and “model has data” probes (TTL 900 s).
- **Endpoints:**
  - `GET /health` (implicit Express default) – readiness (see server setup if expanded).
  - `GET /api/models` – returns curated list (`apps/api/src/constants/models.ts`) enriched with `hasPriceData` flag determined via HEAD count query against Supabase.
  - `GET /api/models/:key/price-history` – pulls up to 2,000 ordered rows per model, merges direct and historical price entries, returns stats (min/max/median/latest total points).
  - `GET /api/metrics/summary` – computes:
    - `totalListings` (HEAD count of entire table).
    - `uniqueVins` via manual `fetch` HEAD request with `distinct=on`.
    - `averageAskingPrice` and 30-day vs prior 30-day windows, limited to 10,000 rows each.

## Frontend (`apps/web`)
- **Build/runtime:** Vite dev server on `http://localhost:5173`. API base defaults to `http://localhost:4000/api` unless `VITE_API_BASE_URL` overrides.
- **Layout:** Single-page dashboard with hero blurb, KPI grid, model selector, and price history chart (line chart component specifics elsewhere).
- **Model selector UX:**
  - Displays all curated models.
  - Models lacking price data are disabled but still visible with tooltip “Pricing data unavailable”.
  - Component auto-selects previously chosen model if still valid, otherwise first selectable model; dropdown overall disabled when no selectable entries.
  - Styling updated for dark background readability.
- **KPI cards:** Show total listings, unique VINs, average asking price for last 30 days, and “Delta vs prior 30d” (difference between current and previous averages). Metrics represent *all* listings, not model-specific aggregates.
- **Price history section:** Header reflects active model, subtitle conveys total observations or default copy. Chart consumes aggregated `PricePoint[]`; loading/error states handled via banners and state flags.

## Data Requirements & Environment
- Required env vars (per `.env` template / API README):
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SCHEMA` (e.g., `raw`).
  - `LISTINGS_TABLE` (currently `auto_tempest_scrape`).
  - Optional: `PORT`, `ALLOWED_ORIGIN`.
- Supabase configuration (already applied):
  - `authenticator` role `pgrst.db_schemas = 'public,graphql_public,raw'`.
  - `raw` schema grants: `usage` + `select` for `service_role` (and optionally `anon`/`authenticated`), plus default privileges for future tables.
  - Schema cache reload via `NOTIFY pgrst, 'reload schema';`.

## Current Limitations / TODO Notes
- Model metadata list is static; no persistence of `firstSeenDate`, `lastSeenDate`, or `totalListings` despite type support.
- Summary metrics sample size is capped at 10k rows; large datasets may yield approximate averages.
- No pagination or filtering on price history beyond static filters defined per model.
- API caching is in-memory only; restarts flush memoized data.
- No automated Supabase migration scripts for role grants/search-path; instructions are manual.

## Running Locally
1. `pnpm install`.
2. Populate root `.env` with Supabase credentials/schema/table.
3. In project root: `pnpm dev` (runs `apps/api` on 4000 and `apps/web` on 5173 concurrently).
4. Visit `http://localhost:5173` for the dashboard.

This document reflects the behavior after enabling schema-level access to `raw.auto_tempest_scrape` and introducing model availability gating in December 2025.

