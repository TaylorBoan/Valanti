export const parseCurrency = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }

  const normalized = value.replace(/[^0-9.\-]/g, '');
  if (!normalized.trim()) {
    return null;
  }

  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
};

export const average = (values: number[]): number | null => {
  if (!values.length) {
    return null;
  }

  const sum = values.reduce((total, current) => total + current, 0);
  return sum / values.length;
};

export const median = (values: number[]): number | null => {
  if (!values.length) {
    return null;
  }

  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    return (sorted[middle - 1] + sorted[middle]) / 2;
  }

  return sorted[middle];
};
