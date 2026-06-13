import type {
  AppSettings,
  CityOption,
  OverviewResponse,
  Period,
  TopTracksResponse,
  WeatherCorrelationResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchOverview(period: Period): Promise<OverviewResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/overview?period=${period}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid period selected."
        : "Unable to load overview data.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchAppSettings(): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`);
  if (!response.ok) {
    throw new Error("Unable to load settings.");
  }
  return response.json();
}

export async function searchCities(query: string): Promise<CityOption[]> {
  const params = new URLSearchParams({ query });
  const response = await fetch(`${API_BASE_URL}/api/cities?${params}`);
  if (!response.ok) {
    throw new Error("Unable to search cities.");
  }
  return response.json();
}

export async function updateAppSettings(settings: AppSettings): Promise<AppSettings> {
  const response = await fetch(`${API_BASE_URL}/api/settings`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    const message =
      response.status === 400 ? "Invalid settings value." : "Unable to save settings.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchTopTracks(
  period: Period,
  limit: number,
): Promise<TopTracksResponse> {
  const params = new URLSearchParams({
    period,
    limit: String(limit),
  });
  const response = await fetch(`${API_BASE_URL}/api/top-tracks?${params}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid top tracks filter selected."
        : "Unable to load top tracks.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchWeatherCorrelation(
  period: Period,
): Promise<WeatherCorrelationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/weather-correlation?period=${period}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid weather period selected."
        : "Unable to load weather correlation.";
    throw new Error(message);
  }
  return response.json();
}
