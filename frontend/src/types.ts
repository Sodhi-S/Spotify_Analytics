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
    album_image_url: string | null;
  }[];
  top_artists: {
    artist_id: string;
    name: string;
    play_count: number;
    image_url: string | null;
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
    album_image_url: string | null;
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

export interface ArtistMoodFingerprint {
  rank: number;
  artist_id: string;
  name: string;
  image_url: string | null;
  mood_label: string;
  avg_valence: number | null;
  avg_energy: number | null;
  play_count: number;
  listening_minutes: number;
  dominant_context: string;
  insight: string;
}

export interface ArtistMoodCallout {
  kind: string;
  artist_name: string | null;
  value: number | null;
  text: string;
}

export interface ArtistMoodFingerprintsResponse {
  period: Period;
  artists: ArtistMoodFingerprint[];
  callouts: ArtistMoodCallout[];
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

export interface WeatherArtistContext {
  artist_id: string;
  name: string;
  image_url: string | null;
  weather_category: string;
  total_listens: number;
  weather_share: number;
  insight: string;
}

export interface WeatherMoodBaseline {
  avg_valence: number | null;
  avg_energy: number | null;
  total_listens: number;
  listening_minutes: number;
}

export interface WeatherMoodShift {
  weather_category: string;
  total_listens: number;
  listening_minutes: number;
  avg_valence: number;
  avg_energy: number;
  valence_delta: number;
  energy_delta: number;
  valence_percent_change: number;
  energy_percent_change: number;
  dominant_mood_quadrant: string;
  top_artist_name: string | null;
  insight: string;
  is_strongest_shift: boolean;
}

export interface WeatherMoodHeatmapCell {
  weather_category: string;
  mood_quadrant: string;
  stream_count: number;
  listening_minutes: number;
  percentage: number;
  is_strongest: boolean;
}

export interface WeatherMoodPoint {
  weather_category: string;
  avg_valence: number;
  avg_energy: number;
  dominant_mood_quadrant: string;
  top_artist_name: string | null;
  stream_count: number;
  listening_minutes: number;
  distance_from_overall: number;
  is_most_distinct: boolean;
}

export interface TemperatureMoodTrend {
  temperature_bucket: string;
  avg_valence: number;
  avg_energy: number;
  stream_count: number;
  listening_minutes: number;
  is_highest_valence: boolean;
  is_highest_energy: boolean;
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
  artist_weather_contexts: WeatherArtistContext[];
  mood_baseline: WeatherMoodBaseline;
  weather_mood_shifts: WeatherMoodShift[];
  weather_mood_heatmap: WeatherMoodHeatmapCell[];
  weather_mood_points: WeatherMoodPoint[];
  temperature_mood_trends: TemperatureMoodTrend[];
  weather_mood_callout: string | null;
  temperature_mood_callout: string | null;
}

export interface DateTimeMonthBucket {
  year: number;
  month: number;
  year_month: string;
  total_listens: number;
  unique_tracks: number;
  unique_artists: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
  top_artist_name: string | null;
}

export interface DateTimeDayBucket {
  day_of_week: string;
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
  top_artist_name: string | null;
  is_weekend: boolean;
}

export interface DateTimeHourBucket {
  hour: number;
  time_segment: string;
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
}

export interface DateTimeHeatmapCell {
  day_of_week: string;
  hour: number;
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
}

export interface DateTimeOverviewResponse {
  period: Period;
  total_listens: number;
  most_active_month: string | null;
  most_active_day: string | null;
  most_active_hour: number | null;
  highest_energy_bucket: string | null;
  highest_valence_bucket: string | null;
  monthly: DateTimeMonthBucket[];
  days: DateTimeDayBucket[];
  hours: DateTimeHourBucket[];
  heatmap: DateTimeHeatmapCell[];
}

export interface DateTimeMonthDetailResponse {
  year_month: string;
  total_listens: number;
  unique_tracks: number;
  unique_artists: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
  top_tracks: {
    track_id: string;
    name: string;
    artist_name: string;
    play_count: number;
    album_image_url: string | null;
  }[];
  top_artists: {
    artist_id: string;
    name: string;
    play_count: number;
    image_url: string | null;
  }[];
  top_tags: {
    tag: string;
    listen_count: number;
  }[];
  summary: string;
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
