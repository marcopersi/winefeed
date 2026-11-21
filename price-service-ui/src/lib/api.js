import axios from "axios";

// Senior-review finding: no request had a timeout, so a hung backend (e.g.
// the external drive holding the DB asleep) left the UI stuck forever with
// no feedback. axios.get (not an axios.create() instance) stays the call
// site so existing tests that mock axios.get directly keep working.
const TIMEOUT_MS = 8000;

export function searchWines(query, n = 20) {
  return axios.get("/search", { params: { q: query, n }, timeout: TIMEOUT_MS });
}

export function fetchPrices(wineId, vintage) {
  return axios.get(`/wines/${wineId}/prices`, {
    params: vintage == null ? {} : { vintage },
    timeout: TIMEOUT_MS,
  });
}

export function fetchVintages(wineId) {
  return axios.get(`/wines/${wineId}/vintages`, { timeout: TIMEOUT_MS });
}

export function fetchForecast(wineId, vintage) {
  return axios.get(`/wines/${wineId}/forecast`, {
    params: vintage == null ? {} : { vintage },
    timeout: TIMEOUT_MS,
  });
}

export function fetchTopWines(n = 10) {
  return axios.get("/wines/top", { params: { n }, timeout: TIMEOUT_MS });
}
