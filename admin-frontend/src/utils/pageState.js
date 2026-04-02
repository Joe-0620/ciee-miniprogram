const STORAGE_PREFIX = 'dashboard-page-state:';
import { getDashboardToken } from './auth';

function isPlainObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

export function loadPageState(key, defaults) {
  if (typeof window === 'undefined') {
    return defaults;
  }
  try {
    const raw = window.localStorage.getItem(buildStorageKey(key));
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return {
      ...defaults,
      ...parsed,
      filters: isPlainObject(defaults.filters) || isPlainObject(parsed.filters)
        ? { ...(defaults.filters || {}), ...(parsed.filters || {}) }
        : parsed.filters ?? defaults.filters,
      sorter: isPlainObject(defaults.sorter) || isPlainObject(parsed.sorter)
        ? { ...(defaults.sorter || {}), ...(parsed.sorter || {}) }
        : parsed.sorter ?? defaults.sorter,
      pagination: isPlainObject(defaults.pagination) || isPlainObject(parsed.pagination)
        ? { ...(defaults.pagination || {}), ...(parsed.pagination || {}) }
        : parsed.pagination ?? defaults.pagination,
    };
  } catch {
    return defaults;
  }
}

export function savePageState(key, state) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(buildStorageKey(key), JSON.stringify(state));
  } catch {}
}

function buildStorageKey(key) {
  const token = getDashboardToken();
  const tokenScope = token ? token.slice(-16) : 'anonymous';
  return `${STORAGE_PREFIX}${tokenScope}:${key}`;
}
