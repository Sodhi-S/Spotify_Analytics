import type { OverviewResponse, Period } from "./types";

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
