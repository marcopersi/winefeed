import axios from "axios";

export function searchWines(query, n = 20) {
  return axios.get("/search", { params: { q: query, n } });
}

export function fetchPrices(wineId) {
  return axios.get(`/wines/${wineId}/prices`);
}

export function fetchTopWines(n = 10) {
  return axios.get("/wines/top", { params: { n } });
}
