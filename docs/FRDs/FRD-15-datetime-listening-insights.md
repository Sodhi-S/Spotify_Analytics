# FRD 15: DateTime Listening Insights

## Page Placement

This feature should live on the **DateTime** page.

The DateTime page should help users understand when they listen, how their listening changes across calendar patterns, and what kinds of music dominate specific months, weekdays, weekends, and times of day.

## 1. Feature Overview

DateTime Listening Insights turns timestamped Last.fm scrobbles into time-based music intelligence.

The page should answer questions like:

- What music do I listen to most in each month?
- Do my weekdays and weekends sound different?
- What hours of the day do I listen most?
- Do mornings have higher energy than late nights?
- Which artists, tracks, tags, and moods define each month?
- How does my listening change across seasons?

The feature should combine listening counts, top tracks/artists/tags, mood labels, and valence/energy aggregates.

## 2. User Goal

Users should be able to:

- See their listening volume by month, day of week, and hour of day.
- Identify the mood profile of different times.
- Compare weekday vs weekend listening.
- Understand seasonal/monthly changes in taste.
- Find patterns like "sad late nights," "high-energy mornings," or "winter comfort artists."
- Filter the page by period.

## 3. Feasibility Summary

This feature is feasible with the current stack.

The app already stores:

- `played_at` from Last.fm scrobbles.
- `date_id` and `hour` in the dbt listen models.
- `day_of_week`, `month`, `year`, and `is_weekend` in `dim_dates`.
- Track metadata and mood features in `dim_tracks`.
- Modeled listen events in `fact_listens`.

No new external API is required for the MVP. The feature can be served entirely from PostgreSQL/dbt/FastAPI.

## 4. Data Inputs

### Existing Warehouse Data

- `fact_listens.listen_id`
- `fact_listens.track_id`
- `fact_listens.artist_id`
- `fact_listens.date_id`
- `fact_listens.played_at`
- `fact_listens.hour`
- `dim_dates.date_id`
- `dim_dates.day_of_week`
- `dim_dates.month`
- `dim_dates.year`
- `dim_dates.is_weekend`
- `dim_tracks.name`
- `dim_tracks.artist_name`
- `dim_tracks.album_image_url`
- `dim_tracks.top_tags`
- `dim_tracks.mood_label`
- `dim_tracks.valence`
- `dim_tracks.energy`
- `dim_artists.name`
- `dim_artists.image_url`

### Required Multi-User Scope

If multi-user auth is active, all DateTime queries must filter by `current_user.id`.

The frontend must never send `user_id`. The backend must derive `user_id` from the authenticated session.

## 5. Functional Requirements

- The system shall show listening volume by month.
- The system shall show listening volume by day of week.
- The system shall show listening volume by hour of day.
- The system shall show a day-of-week by hour heatmap.
- The system shall show top tracks, artists, and tags for a selected month.
- The system shall show dominant mood by month.
- The system shall show average valence and average energy by month.
- The system shall show average valence and average energy by hour of day.
- The system shall show average valence and average energy by day of week.
- The system shall support period filtering: `7d`, `30d`, `6m`, `all`.
- The system shall support drilling into a month, day, or hour bucket.
- The system shall include empty states when there is not enough data.
- The system shall exclude null valence/energy from numeric averages.
- The system shall count unclassified tracks separately in mood distributions.
- The system shall keep all responses scoped to the authenticated user.

## 6. Page Sections

### 6.1 Summary Cards

The page should show:

- Total listens in selected period.
- Most active month.
- Most active day of week.
- Most active hour.
- Highest-energy time bucket.
- Highest-valence time bucket.

### 6.2 Monthly Listening Timeline

Displays listens grouped by `year-month`.

Each month should include:

- Total listens
- Unique tracks
- Unique artists
- Top artist
- Dominant mood
- Average valence
- Average energy

Recommended visualization:

- Bar chart or area chart for listen count.
- Optional overlay line for average energy or valence.

### 6.3 Month Detail Panel

When the user selects a month, show:

- Top tracks for that month.
- Top artists for that month.
- Top tags for that month.
- Mood distribution.
- Average valence/energy.
- Short text summary, generated deterministically.

Example:

```text
March was your highest-energy month, led by Kendrick Lamar and high-intensity hip-hop tags.
```

### 6.4 Day Of Week Breakdown

Displays listening by Monday through Sunday.

Each day should include:

- Total listens
- Average valence
- Average energy
- Dominant mood
- Top artist

Recommended visualization:

- Seven compact cards or horizontal bars.
- Weekday/weekend comparison callout.

### 6.5 Hour Of Day Breakdown

Displays listening by hour `0` through `23`.

Each hour should include:

- Total listens
- Average valence
- Average energy
- Dominant mood

Recommended grouping labels:

| Time Segment | Hours |
|---|---|
| Late Night | 0-4 |
| Morning | 5-11 |
| Afternoon | 12-16 |
| Evening | 17-21 |
| Night | 22-23 |

### 6.6 Listening Heatmap

Displays day-of-week by hour.

The heatmap should:

- Always render 168 cells: 7 days x 24 hours.
- Color cells by listen count by default.
- Optionally toggle color mode to dominant mood or average energy.
- Show tooltip with day, hour, listen count, dominant mood, average valence, and average energy.

## 7. API Requirements

### DateTime Overview

```http
GET /api/datetime/overview?period=30d
```

Response:

```ts
{
  period: "7d" | "30d" | "6m" | "all";
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
```

### Month Detail

```http
GET /api/datetime/months/{year_month}?period=all
```

Example `year_month`: `2026-06`.

Response:

```ts
{
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
```

### Shared Type Shapes

```ts
interface DateTimeMonthBucket {
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

interface DateTimeDayBucket {
  day_of_week: "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun";
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
  top_artist_name: string | null;
  is_weekend: boolean;
}

interface DateTimeHourBucket {
  hour: number;
  time_segment: string;
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
}

interface DateTimeHeatmapCell {
  day_of_week: string;
  hour: number;
  total_listens: number;
  avg_valence: number | null;
  avg_energy: number | null;
  dominant_mood: string | null;
}
```

## 8. dbt Requirements

The MVP can query existing marts directly, but preferred implementation is to add dedicated marts for performance and consistency.

Recommended models:

```text
mart_datetime_monthly
mart_datetime_day_of_week
mart_datetime_hourly
mart_datetime_heatmap
```

### `mart_datetime_monthly`

Grain: one row per user/month.

Required columns:

- `user_id`, if multi-user mode is active
- `year`
- `month`
- `year_month`
- `total_listens`
- `unique_tracks`
- `unique_artists`
- `avg_valence`
- `avg_energy`
- `dominant_mood`
- `top_artist_id`
- `top_artist_name`

### `mart_datetime_heatmap`

Grain: one row per user/day-of-week/hour.

Required columns:

- `user_id`, if multi-user mode is active
- `day_of_week`
- `hour`
- `total_listens`
- `avg_valence`
- `avg_energy`
- `dominant_mood`

The API layer should fill missing heatmap cells with zero-count rows so the frontend always renders a stable grid.

## 9. Query Logic

### Monthly Aggregation

```sql
select
    dates.year,
    dates.month,
    concat(dates.year, '-', lpad(dates.month::text, 2, '0')) as year_month,
    count(*) as total_listens,
    count(distinct listens.track_id) as unique_tracks,
    count(distinct listens.artist_id) as unique_artists,
    avg(tracks.valence) filter (where tracks.valence is not null) as avg_valence,
    avg(tracks.energy) filter (where tracks.energy is not null) as avg_energy
from fact_listens listens
join dim_dates dates on listens.date_id = dates.date_id
left join dim_tracks tracks on listens.track_id = tracks.track_id
where listens.date_id >= :start_date
group by dates.year, dates.month;
```

### Hourly Aggregation

```sql
select
    listens.hour,
    count(*) as total_listens,
    avg(tracks.valence) filter (where tracks.valence is not null) as avg_valence,
    avg(tracks.energy) filter (where tracks.energy is not null) as avg_energy
from fact_listens listens
left join dim_tracks tracks on listens.track_id = tracks.track_id
where listens.date_id >= :start_date
group by listens.hour
order by listens.hour;
```

## 10. UI Requirements

The DateTime page should include:

- Page header with period selector.
- Summary cards.
- Monthly timeline chart.
- Month detail panel.
- Day-of-week breakdown.
- Hour-of-day breakdown.
- Day/hour heatmap.
- Toggle for heatmap color mode: listens, mood, energy.
- Loading, error, and empty states.
- Mobile layout that stacks charts vertically.

## 11. Empty States

The page should show empty states when:

- The user has no listening data.
- The selected period has no listening data.
- Mood/valence/energy data is unavailable for most tracks.
- A selected month has no matching records.

Example:

```text
No DateTime patterns yet. Once more Last.fm listens are imported, this page will show when your music habits change.
```

## 12. Security and Privacy Requirements

- All endpoints must require authentication if auth is enabled.
- The backend must derive user identity from the session.
- The frontend must not send `user_id`.
- All SQL queries must filter user-owned data by current user.
- Aggregated data should not mix users.

## 13. Acceptance Criteria

This feature is complete when:

- The DateTime page is reachable from the top nav.
- The page shows monthly, day-of-week, hour-of-day, and heatmap sections.
- The period selector filters all DateTime views consistently.
- The heatmap always renders 168 cells.
- Month detail shows top tracks, artists, tags, and mood summary.
- Valence and energy averages are calculated only from non-null values.
- Unclassified tracks are counted separately in mood distributions.
- Multi-user data is scoped to the current session user.
- Empty states render without layout breakage.

## 14. Open Questions

- Should the page default to `30d`, `6m`, or `all`?
- Should time-of-day use the user's local timezone explicitly?
- Should month detail summaries be deterministic or AI-generated later?
- Should DateTime include weather overlays, or should weather remain isolated to the Weather page?
- Should the heatmap color by mood, energy, or listens by default?
