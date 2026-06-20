import type {
  AppSettings,
  ArtistMoodFingerprintsResponse,
  AuthUser,
  CityOption,
  DateTimeMonthDetailResponse,
  DateTimeOverviewResponse,
  OverviewResponse,
  Period,
  TopTracksResponse,
  WeatherCorrelationResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      ...init.headers,
    },
  });
}

export function lastfmLoginUrl(mode: "login" | "set_password" = "login"): string {
  const params = new URLSearchParams({ mode });
  return apiUrl(`/api/auth/lastfm/login?${params}`);
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const response = await apiFetch("/api/auth/me");
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error("Unable to load your session.");
  }
  return response.json();
}

export async function logout(): Promise<void> {
  const response = await apiFetch("/api/auth/logout", { method: "POST" });
  if (!response.ok) {
    throw new Error("Unable to sign out.");
  }
}

export async function loginWithPassword(
  lastfmUsername: string,
  password: string,
): Promise<AuthUser> {
  const response = await apiFetch("/api/auth/password/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      lastfm_username: lastfmUsername,
      password,
    }),
  });
  if (!response.ok) {
    const message =
      response.status === 401
        ? "Invalid username or password."
        : "Unable to sign in.";
    throw new Error(message);
  }
  return response.json();
}

export async function setAppPassword(password: string): Promise<AuthUser> {
  const response = await apiFetch("/api/auth/password/set", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Password must be at least 8 characters."
        : "Unable to save password.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchOverview(period: Period): Promise<OverviewResponse> {
  const response = await apiFetch(`/api/stats/overview?period=${period}`);
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
  const response = await apiFetch("/api/settings");
  if (!response.ok) {
    throw new Error("Unable to load settings.");
  }
  return response.json();
}

export async function searchCities(query: string): Promise<CityOption[]> {
  const params = new URLSearchParams({ query });
  const response = await apiFetch(`/api/cities?${params}`);
  if (!response.ok) {
    throw new Error("Unable to search cities.");
  }
  return response.json();
}

export async function updateAppSettings(settings: AppSettings): Promise<AppSettings> {
  const response = await apiFetch("/api/settings", {
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
  const response = await apiFetch(`/api/top-tracks?${params}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid top tracks filter selected."
        : "Unable to load top tracks.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchArtistMoodFingerprints(
  period: Period,
  limit = 10,
): Promise<ArtistMoodFingerprintsResponse> {
  const params = new URLSearchParams({
    period,
    limit: String(limit),
  });
  const response = await apiFetch(`/api/moods/artist-fingerprints?${params}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid artist mood filter selected."
        : "Unable to load artist mood fingerprints.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchWeatherCorrelation(
  period: Period,
): Promise<WeatherCorrelationResponse> {
  const response = await apiFetch(`/api/weather-correlation?period=${period}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid weather period selected."
        : "Unable to load weather correlation.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchDateTimeOverview(
  period: Period,
): Promise<DateTimeOverviewResponse> {
  const response = await fetch(`${API_BASE_URL}/api/datetime/overview?period=${period}`);
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid datetime period selected."
        : "Unable to load datetime insights.";
    throw new Error(message);
  }
  return response.json();
}

export async function fetchDateTimeMonthDetail(
  yearMonth: string,
  period: Period = "all",
): Promise<DateTimeMonthDetailResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/datetime/months/${yearMonth}?period=${period}`,
  );
  if (!response.ok) {
    const message =
      response.status === 400
        ? "Invalid month selected."
        : "Unable to load month details.";
    throw new Error(message);
  }
  return response.json();
}
