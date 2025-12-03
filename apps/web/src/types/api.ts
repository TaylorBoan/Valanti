export type ModelDefinition = {
  key: string;
  make: string;
  label: string;
  firstSeenDate?: string | null;
  lastSeenDate?: string | null;
  hasPriceData?: boolean;
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
