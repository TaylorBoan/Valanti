import dayjs from 'dayjs';
import { memoize } from '../cache.js';
import { config } from '../config.js';
import { modelDefinitions, getModelByKey } from '../constants/models.js';
import { supabase } from '../supabase.js';
import {
  ListingRecord,
  ModelDefinition,
  ModelMetadata,
  PriceHistoryResponse,
  PricePoint,
  SummaryMetrics
} from '../types/index.js';
import { parseToIso } from '../utils/dates.js';
import { average, median, parseCurrency } from '../utils/pricing.js';

const PRICE_HISTORY_LIMIT = 2000;
const METRICS_SAMPLE_LIMIT = 10000;

export const listModels = async (): Promise<ModelMetadata[]> =>
  Promise.all(
    modelDefinitions.map(async (definition) => ({
      ...definition,
      hasPriceData: await modelHasPricingData(definition)
    }))
  );

export const getPriceHistoryForModel = (key: string): Promise<PriceHistoryResponse> =>
  memoize(`price-history:${key}`, async () => {
    const definition = getModelByKey(key);

    if (!definition) {
      throw new Error(`Unknown model key: ${key}`);
    }

    const listings = await fetchListings(definition);
    const points = extractPricePoints(listings);
    const prices = points.map((point) => point.price);

    return {
      model: definition,
      stats: {
        minPrice: prices.length ? Math.min(...prices) : null,
        maxPrice: prices.length ? Math.max(...prices) : null,
        medianPrice: median(prices),
        latestPrice: points.length ? points[points.length - 1].price : null,
        lastUpdated: points.length ? points[points.length - 1].date : null,
        totalPoints: points.length
      },
      points
    };
  });

export const getSummaryMetrics = (modelKey?: string): Promise<SummaryMetrics> => {
  const cacheKey = modelKey ? `summary-metrics:${modelKey}` : 'summary-metrics';

  return memoize(cacheKey, async () => {
    const now = dayjs();
    const currentWindowStart = now.subtract(30, 'day');
    const previousWindowStart = now.subtract(60, 'day');
    const definition = modelKey ? getModelByKey(modelKey) : undefined;

    if (modelKey && !definition) {
      throw new Error(`Unknown model key: ${modelKey}`);
    }

    const [totalResult, uniqueVins, currentWindow, previousWindow] = await Promise.all([
      supabase.from(config.listingsTable).select('id', { head: true, count: 'exact' }),
      countDistinct('vin'),
      (() => {
        let query = supabase
          .from(config.listingsTable)
          .select('price,date')
          .gte('date', currentWindowStart.toISOString())
          .lte('date', now.toISOString())
          .limit(METRICS_SAMPLE_LIMIT);

        definition?.filters?.forEach((filter) => {
          query =
            filter.operator === 'eq'
              ? query.eq(filter.column, filter.value)
              : query.ilike(filter.column, filter.value);
        });

        return query;
      })(),
      (() => {
        let query = supabase
          .from(config.listingsTable)
          .select('price,date')
          .gte('date', previousWindowStart.toISOString())
          .lt('date', currentWindowStart.toISOString())
          .limit(METRICS_SAMPLE_LIMIT);

        definition?.filters?.forEach((filter) => {
          query =
            filter.operator === 'eq'
              ? query.eq(filter.column, filter.value)
              : query.ilike(filter.column, filter.value);
        });

        return query;
      })()
    ]);

    if (totalResult.error) {
      throw totalResult.error;
    }
    if (currentWindow.error) {
      throw currentWindow.error;
    }
    if (previousWindow.error) {
      throw previousWindow.error;
    }

    const currentPrices = sanitizePriceArray(currentWindow.data);
    const previousPrices = sanitizePriceArray(previousWindow.data);
    const averageCurrent = average(currentPrices);
    const averagePrevious = average(previousPrices);

    return {
      totalListings: totalResult.count ?? null,
      uniqueVins,
      averageAskingPrice: averageCurrent,
      priceTrend: {
        current: averageCurrent,
        previous: averagePrevious,
        delta:
          averageCurrent !== null && averagePrevious !== null ? averageCurrent - averagePrevious : null
      },
      updatedAt: now.toISOString()
    };
  }, 120);
};

async function fetchListings(definition: ModelDefinition): Promise<ListingRecord[]> {
  let query = supabase
    .from(config.listingsTable)
    .select(
      'id,make,model,backendModel,trim,vin,price,priceHistory,listingHistory,mileage,date,ctime,img,location,sitecode,sourceName,title'
    )
    .order('date', { ascending: true, nullsFirst: false })
    .limit(PRICE_HISTORY_LIMIT);

  definition.filters?.forEach((filter) => {
    if (filter.operator === 'eq') {
      query = query.eq(filter.column, filter.value);
      return;
    }

    query = query.ilike(filter.column, filter.value);
  });

  const { data, error } = await query;

  if (error) {
    throw error;
  }

  return data ?? [];
}

async function modelHasPricingData(definition: ModelDefinition): Promise<boolean> {
  return memoize<boolean>(
    `model-has-pricing:${definition.key}`,
    async () => {
      let query = supabase
        .from(config.listingsTable)
        .select('id', { head: true, count: 'exact' });

      definition.filters?.forEach((filter) => {
        if (filter.operator === 'eq') {
          query = query.eq(filter.column, filter.value);
          return;
        }

        query = query.ilike(filter.column, filter.value);
      });

      const { count, error } = await query;

      if (error) {
        throw error;
      }

      return (count ?? 0) > 0;
    },
    900
  );
}

function extractPricePoints(listings: ListingRecord[]): PricePoint[] {
  const points = new Map<string, PricePoint>();

  listings.forEach((listing) => {
    const priceFromListing = parseCurrency(listing.price ?? null);
    const baseDate = parseToIso(listing.date ?? listing.ctime ?? null);

    if (priceFromListing !== null && baseDate) {
      const key = `${baseDate}-${priceFromListing}-${listing.vin ?? listing.id ?? ''}`;
      points.set(key, {
        date: baseDate,
        price: priceFromListing,
        mileage: parseMileage(listing.mileage),
        listingId: listing.id ?? null,
        vin: listing.vin ?? null,
        source: listing.sourceName ?? listing.sitecode ?? null
      });
    }

    const histories = [...parseHistory(listing.priceHistory), ...parseHistory(listing.listingHistory)];

    histories.forEach((entry) => {
      const price = parseCurrency(entry.price ?? null);
      const date = parseToIso(entry.date ?? null);

      if (price === null || !date) {
        return;
      }

      const key = `${date}-${price}-${listing.vin ?? listing.id ?? ''}`;
      if (!points.has(key)) {
        points.set(key, {
          date,
          price,
          mileage: parseMileage(entry.mileage ?? null) ?? parseMileage(listing.mileage),
          listingId: listing.id ?? null,
          vin: listing.vin ?? null,
          source: listing.sourceName ?? listing.sitecode ?? null
        });
      }
    });
  });

  return Array.from(points.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function parseHistory(value: ListingRecord['priceHistory'] | ListingRecord['listingHistory']) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  return [];
}

function parseMileage(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === 'number') {
    return value;
  }

  const numeric = Number.parseInt(value.replace(/[^0-9]/g, ''), 10);
  return Number.isFinite(numeric) ? numeric : null;
}

function sanitizePriceArray(
  rows: { price?: string | number | null; date?: string | null }[] | null
): number[] {
  if (!rows?.length) {
    return [];
  }

  return rows
    .map((row) => parseCurrency(row.price ?? null))
    .filter((value): value is number => value !== null);
}

async function countDistinct(column: string): Promise<number | null> {
  const url = new URL(`${config.supabaseUrl}/rest/v1/${config.listingsTable}`);
  url.searchParams.set('select', column);
  url.searchParams.set('distinct', 'on');

  const response = await fetch(url.toString(), {
    method: 'HEAD',
    headers: {
      apikey: config.supabaseKey,
      Authorization: `Bearer ${config.supabaseKey}`,
      Prefer: 'count=exact',
      'Accept-Profile': config.supabaseSchema
    }
  });

  if (!response.ok) {
    return null;
  }

  const contentRange = response.headers.get('content-range');
  if (!contentRange) {
    return null;
  }

  const [, total] = contentRange.split('/');
  return total ? Number(total) : null;
}
