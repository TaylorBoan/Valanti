export type ListingRecord = {
  id?: string;
  make?: string;
  model?: string;
  backendModel?: string | null;
  trim?: string | null;
  vin?: string | null;
  price?: string | number | null;
  priceHistory?: Array<PriceHistoryEntry> | string | null;
  listingHistory?: string | null;
  mileage?: string | number | null;
  date?: string | null;
  ctime?: number | null;
  img?: string | null;
  location?: string | null;
  sitecode?: string | null;
  sourceName?: string | null;
  title?: string | null;
};

export type PriceHistoryEntry = {
  date?: string;
  price?: string | number;
  mileage?: string | number;
  trend?: string;
};

export type FilterClause = {
  column: 'make' | 'model' | 'backendModel' | 'title';
  operator: 'eq' | 'ilike';
  value: string;
};

export type ModelDefinition = {
  key: string;
  make: string;
  label: string;
  aliases?: string[];
  filters?: FilterClause[];
  hasPriceData?: boolean;
};

export type ModelMetadata = ModelDefinition & {
  firstSeenDate?: string | null;
  lastSeenDate?: string | null;
  totalListings?: number;
};

export type PricePoint = {
  date: string;
  price: number;
  mileage?: number | null;
  vin?: string | null;
  listingId?: string | null;
  source?: string | null;
};

export type PriceHistoryResponse = {
  model: ModelDefinition;
  stats: {
    minPrice: number | null;
    maxPrice: number | null;
    medianPrice: number | null;
    latestPrice: number | null;
    lastUpdated: string | null;
    totalPoints: number;
  };
  points: PricePoint[];
};

export type SummaryMetrics = {
  totalListings: number | null;
  uniqueVins: number | null;
  averageAskingPrice: number | null;
  priceTrend: {
    current: number | null;
    previous: number | null;
    delta: number | null;
  };
  updatedAt: string;
};
