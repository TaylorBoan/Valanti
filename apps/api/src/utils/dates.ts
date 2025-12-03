import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat.js';
import utc from 'dayjs/plugin/utc.js';

dayjs.extend(utc);
dayjs.extend(customParseFormat);

export const toDate = (value?: string | null) => (value ? dayjs(value) : null);

export const parseToIso = (value?: string | number | null) => {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === 'number') {
    return dayjs(value * 1000).utc().toISOString();
  }

  const direct = dayjs(value);
  if (direct.isValid()) {
    return direct.toISOString();
  }

  const formats = ['YYYY-MM-DD HH:mm:ss', 'MMM D YYYY', 'MMM D YYYY HH:mm', 'MM/DD/YYYY', 'YYYY-MM-DD'];
  for (const format of formats) {
    const parsed = dayjs(value, format, true);
    if (parsed.isValid()) {
      return parsed.toISOString();
    }
  }

  return null;
};

export const maxDate = (dates: (string | null | undefined)[]) => {
  const parsed = dates
    .map((value) => (value ? dayjs(value) : null))
    .filter((d): d is dayjs.Dayjs => Boolean(d));

  if (!parsed.length) {
    return null;
  }

  return parsed.sort((a, b) => a.valueOf() - b.valueOf())[parsed.length - 1];
};

export const isoString = (value: dayjs.Dayjs | null) => (value ? value.toISOString() : null);
