export type Period = "7d" | "30d" | "6m" | "all";

export interface OverviewResponse {
  period: Period;
  total_listens: number;
  unique_tracks: number;
  unique_artists: number;
  top_tracks: {
    track_id: string;
    name: string;
    artist_name: string;
    play_count: number;
  }[];
  top_artists: {
    artist_id: string;
    name: string;
    play_count: number;
  }[];
  top_tags: {
    tag: string;
    listen_count: number;
  }[];
  mood_breakdown: Record<string, number>;
}

export interface TopTracksResponse {
  period: Period;
  limit: number;
  tracks: {
    rank: number;
    track_id: string;
    name: string;
    artist_name: string;
    album: string | null;
    play_count: number;
    total_ms_played: number;
    mood_label: string | null;
    mood_confidence: number | null;
    top_tags: string[];
  }[];
}

export interface MoodDistribution {
  happy: number;
  sad: number;
  angry: number;
  calm: number;
  energetic: number;
  melancholic: number;
  unclassified: number;
}

export interface WeatherSummary {
  label: string;
  total_days: number;
  total_listens: number;
  avg_listens_per_day: number;
  avg_mood_score: number | null;
  avg_temp_c: number | null;
  total_precipitation: number;
  top_tags: {
    tag: string;
    listen_count: number;
  }[];
}

export interface WeatherCorrelationResponse {
  period: Period;
  weather_city: string;
  daily_data: {
    date: string;
    day_of_week: string;
    is_weekend: boolean;
    total_listens: number;
    mood_score: number | null;
    mood_distribution: MoodDistribution;
    temp_c: number | null;
    temp_min_c: number | null;
    temp_max_c: number | null;
    precipitation: number | null;
    rain: number | null;
    snowfall: number | null;
    precipitation_hours: number | null;
    weather_code: number | null;
    weather_category: string;
    temperature_bucket: string;
    season: string;
    had_precipitation: boolean;
  }[];
  summary_by_weather: WeatherSummary[];
  summary_by_temperature: WeatherSummary[];
  summary_by_season: WeatherSummary[];
}

export interface AppSettings {
  weather_city: string;
  weather_latitude: number | null;
  weather_longitude: number | null;
  weather_refresh_status?: string | null;
}

export interface CityOption {
  id: string;
  name: string;
  label: string;
  country: string;
  country_code: string;
  admin1: string | null;
  latitude: number;
  longitude: number;
}
