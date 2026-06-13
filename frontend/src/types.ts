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
