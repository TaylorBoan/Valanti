import NodeCache from 'node-cache';

export const cache = new NodeCache({ stdTTL: 300, checkperiod: 60 });

export function memoize<T>(key: string, factory: () => Promise<T>, ttlSeconds = 300) {
  const cached = cache.get<T>(key);
  if (cached) {
    return Promise.resolve(cached);
  }

  return factory().then((result) => {
    cache.set(key, result, ttlSeconds);
    return result;
  });
}
