# FRD-002: Overview Dashboard

## `/api/stats/overview` Endpoint + Overview Frontend View

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Requirements:** P5-1, P6-1
**Author:** Sahej Singh Sodhi
**Created:** March 2, 2026
**Updated:** March 3, 2026
**Status:** Draft

---

## 1. Purpose

This FRD specifies the Overview Dashboard feature: the FastAPI endpoint that serves summary statistics and the React frontend view that displays them. The Overview is the landing page of the dashboard and gives a quick snapshot of the user's listening activity, including mood breakdown, top community tags, and top tracks/artists.

---

## 2. Scope

| In Scope | Out of Scope |
| --- | --- |
| `GET /api/stats/overview` endpoint | Data ingestion and transformation (see FRD-001) |
| Overview frontend view (total stats, top tracks, top artists, top community tags, mood breakdown donut chart) | Heatmap, mood trends, weather, and cluster views (see other FRDs) |

---

## 3. Data Dependencies

This feature reads from the following dbt mart/dimension tables:

| Table | Used For |
| --- | --- |
| `mart_listening_summary` | Total listens, unique tracks, unique artists, mood distribution counts (aggregated over requested period) |
| `fact_listens` | Top tracks and tag calculations (join through dimensions) |
| `dim_tracks` | Track names, `mood_label`, `top_tags` |
| `dim_artists` | Artist names, `genres` (from Last.fm top tags) |

---

## 4. API Specification

### `GET /api/stats/overview`

#### Request

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `period` | query string | No | `all` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |

**Period definitions:**

| Value | Meaning |
| --- | --- |
| `7d` | Last 7 calendar days (including today) |
| `30d` | Last 30 calendar days (including today) |
| `6m` | Last 6 calendar months (180 days from today) |
| `all` | All data in the warehouse |

#### Response

```json
{
  "period": "30d",
  "total_listens": 1423,
  "unique_tracks": 312,
  "unique_artists": 87,
  "top_tracks": [
    {
      "track_id": "abc123",
      "name": "Track Name",
      "artist_name": "Artist Name",
      "play_count": 42
    }
  ],
  "top_artists": [
    {
      "artist_id": "def456",
      "name": "Artist Name",
      "play_count": 98
    }
  ],
  "top_tags": [
    {
      "tag": "indie rock",
      "listen_count": 215
    }
  ],
  "mood_breakdown": {
    "happy": 312,
    "sad": 198,
    "angry": 87,
    "calm": 256,
    "energetic": 345,
    "melancholic": 142,
    "unclassified": 83
  }
}
```

#### Field Details

| Field | Source | Logic |
| --- | --- | --- |
| `total_listens` | `mart_listening_summary` | `SUM(total_listens)` over the filtered date range |
| `unique_tracks` | `fact_listens` | `COUNT(DISTINCT track_id)` over the filtered date range |
| `unique_artists` | `fact_listens` | `COUNT(DISTINCT artist_id)` over the filtered date range |
| `top_tracks` | `fact_listens` → `dim_tracks` | Top 5 by `COUNT(*)` grouped by `track_id`, joined to `dim_tracks` for name |
| `top_artists` | `fact_listens` → `dim_artists` | Top 5 by `COUNT(*)` grouped by `artist_id`, joined to `dim_artists` (WHERE `is_current = TRUE`) for name |
| `top_tags` | See Section 5 | Top 5 community tags by weighted listen count |
| `mood_breakdown` | `mart_listening_summary` | `SUM(mood_<label>_count)` per mood class over filtered date range. `unclassified` = `SUM(mood_null_count)`. |

#### Error Responses

| Status | Condition | Body |
| --- | --- | --- |
| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

---

## 5. Top Tags Calculation Logic

Community tags come from two sources: `dim_tracks.top_tags` (track-level tags from `track.getTopTags`) and `dim_artists.genres` (artist-level tags from `artist.getTopTags`). For the overview, we use **artist-level tags** as the genre proxy, calculated by **listen-weighted tag counting**:

1. For each listen in `fact_listens` (within the requested period), look up the artist via `artist_id` → `dim_artists` (WHERE `is_current = TRUE`).
2. Retrieve the artist's `genres` array (sourced from Last.fm `artist.getTopTags`).
3. For that listen, **credit each tag in the array equally with 1 listen count**. (If an artist has 3 tags, each tag gets +1 for that listen.)
4. Aggregate across all listens in the period: `SUM(listen_count)` per tag.
5. Return the top 5 tags by total listen count.

**Example:**

| Listen | Artist | Artist Tags | Credits |
| --- | --- | --- | --- |
| Listen 1 | Artist A | `["indie rock", "dream pop"]` | indie rock: +1, dream pop: +1 |
| Listen 2 | Artist A | `["indie rock", "dream pop"]` | indie rock: +1, dream pop: +1 |
| Listen 3 | Artist B | `["hip hop", "indie rock"]` | hip hop: +1, indie rock: +1 |

**Result:** indie rock: 3, dream pop: 2, hip hop: 1.

This approach is implemented as a dbt model or a SQL query in FastAPI. Prefer a dbt model (`mart_tag_listen_counts` or similar) if the query is expensive.

---

## 6. Frontend View — Overview Dashboard

### 6.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Period Selector: [7d] [30d] [6m] [All Time]                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │  Total    │  │  Unique      │  │  Unique        │        │
│  │  Listens  │  │  Tracks      │  │  Artists       │        │
│  │  1,423    │  │  312         │  │  87            │        │
│  └──────────┘  └──────────────┘  └────────────────┘        │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │  Top 5 Tracks        │  │  Top 5 Artists            │     │
│  │  1. Track A (42)     │  │  1. Artist A (98)         │     │
│  │  2. Track B (38)     │  │  2. Artist B (76)         │     │
│  │  ...                 │  │  ...                      │     │
│  └──────────────────────┘  └──────────────────────────┘     │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │  Top 5 Tags          │  │  Mood Breakdown           │     │
│  │  1. indie rock (215) │  │  (Donut Chart)            │     │
│  │  2. dream pop (189)  │  │                           │     │
│  │  ...                 │  │                           │     │
│  └──────────────────────┘  └──────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Components

| Component | Library | Props / Data |
| --- | --- | --- |
| `PeriodSelector` | Native React | Emits `period` value (`7d`, `30d`, `6m`, `all`) |
| `StatCard` | Native React | `label`, `value` (formatted with locale separators) |
| `TopList` | Native React | `title`, `items: { name, subtitle?, count }[]` |
| `MoodDonutChart` | Recharts (`PieChart`) | Mood label distribution with donut hole |

### 6.3 Mood Donut Chart Specification

- **Chart type:** Recharts `PieChart` with `Pie` (inner radius > 0 for donut effect).
- **Segments:** One segment per mood class (happy, sad, angry, calm, energetic, melancholic) + one for "Unclassified".
- **Colors:** Distinct, accessible color per mood class. Example palette:
  - Happy: `#facc15` (yellow)
  - Sad: `#3b82f6` (blue)
  - Angry: `#ef4444` (red)
  - Calm: `#a78bfa` (violet)
  - Energetic: `#f97316` (orange)
  - Melancholic: `#6b7280` (gray)
  - Unclassified: `#e5e7eb` (light gray)
- **Labels:** Percentage and count shown on hover (tooltip).
- **Center label:** Total classified listens count (exclude unclassified).

### 6.4 Interaction

- Clicking a period button fetches `GET /api/stats/overview?period=<value>` and re-renders all components.
- Loading state shown while fetching.
- If the API returns an error, a toast/banner message is displayed.

### 6.5 TypeScript Interface

```typescript
interface OverviewResponse {
  period: "7d" | "30d" | "6m" | "all";
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
  mood_breakdown: {
    [mood_label: string]: number; // e.g., "happy": 312, "unclassified": 83
  };
}
```

---

## 7. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| Period filter correctly scopes all returned data | Compare `total_listens` for `7d` vs `all` — `7d` ≤ `all` |
| Top tags use listen-weighted counting across all artist tags | Manually verify with a SQL query against `fact_listens` + `dim_artists` |
| Mood breakdown sums to `total_listens` (including unclassified) | Verify `sum(mood_breakdown values) == total_listens` |
| Donut chart displays all mood classes with correct proportions | Visual inspection |
| Period selector re-fetches and updates all components | Click each period button and verify data changes |
| Loading and error states work | Throttle network / kill API and verify UI feedback |
