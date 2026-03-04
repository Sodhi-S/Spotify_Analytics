# FRD-004: Mood Trends (Mood Over Time)

## `/api/mood/trends` Endpoint + Mood Over Time Frontend View

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Requirements:** P5-3, P6-2
**Author:** Sahej Singh Sodhi
**Created:** March 2, 2026
**Updated:** March 3, 2026
**Status:** Draft

---

## 1. Purpose

This FRD specifies the Mood Trends feature: the FastAPI endpoint that serves mood distribution over time and the React frontend view that displays it as a stacked area chart. This replaces the previous "Taste Over Time" concept (which used Spotify audio features like energy, valence, danceability) with mood label distribution derived from the Librosa-based mood classifier.

---

## 2. Scope

| In Scope | Out of Scope |
| --- | --- |
| `GET /api/mood/trends` endpoint | Data ingestion, mood classification pipeline (see FRD-001) |
| Stacked area chart of mood distribution by month | Overview, heatmap, weather, cluster views (see other FRDs) |
| Period filtering | Real-time streaming updates |

---

## 3. Data Dependencies

| Table | Used For |
| --- | --- |
| `mart_listening_summary` | Pre-aggregated daily mood counts (`mood_happy_count`, `mood_sad_count`, etc.) |
| `dim_dates` | Grouping by month, filtering by period |

---

## 4. API Specification

### `GET /api/mood/trends`

#### Request

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `period` | query string | No | `6m` | Time window. Accepted values: `7d`, `30d`, `6m`, `all`. |

**Period definitions:**

| Value | Meaning |
| --- | --- |
| `7d` | Last 7 calendar days — data returned per **day** |
| `30d` | Last 30 calendar days — data returned per **day** |
| `6m` | Last 6 calendar months — data returned per **month** |
| `all` | All data — data returned per **month** |

**Granularity note:** For shorter periods (`7d`, `30d`), data is aggregated per day. For longer periods (`6m`, `all`), data is aggregated per month. This prevents charts with excessive data points or charts with too few data points.

#### Response

```json
{
  "period": "6m",
  "granularity": "month",
  "data": [
    {
      "date": "2026-01",
      "total_listens": 487,
      "mood_happy": 98,
      "mood_sad": 67,
      "mood_angry": 23,
      "mood_calm": 112,
      "mood_energetic": 134,
      "mood_melancholic": 41,
      "mood_unclassified": 12
    },
    {
      "date": "2026-02",
      "total_listens": 523,
      "mood_happy": 112,
      "mood_sad": 54,
      "mood_angry": 31,
      "mood_calm": 98,
      "mood_energetic": 156,
      "mood_melancholic": 55,
      "mood_unclassified": 17
    }
  ]
}
```

#### Field Details

| Field | Source | Logic |
| --- | --- | --- |
| `date` | `mart_listening_summary.date_id` | Formatted as `YYYY-MM-DD` for daily granularity, `YYYY-MM` for monthly granularity |
| `total_listens` | `mart_listening_summary.total_listens` | `SUM(total_listens)` grouped by date/month |
| `mood_happy` | `mart_listening_summary.mood_happy_count` | `SUM(mood_happy_count)` grouped by date/month |
| `mood_sad` | `mart_listening_summary.mood_sad_count` | `SUM(mood_sad_count)` grouped by date/month |
| `mood_angry` | `mart_listening_summary.mood_angry_count` | `SUM(mood_angry_count)` grouped by date/month |
| `mood_calm` | `mart_listening_summary.mood_calm_count` | `SUM(mood_calm_count)` grouped by date/month |
| `mood_energetic` | `mart_listening_summary.mood_energetic_count` | `SUM(mood_energetic_count)` grouped by date/month |
| `mood_melancholic` | `mart_listening_summary.mood_melancholic_count` | `SUM(mood_melancholic_count)` grouped by date/month |
| `mood_unclassified` | `mart_listening_summary.mood_null_count` | `SUM(mood_null_count)` grouped by date/month |

**Aggregation:** The `mart_listening_summary` table has one row per day. For monthly granularity, the endpoint groups by `DATE_TRUNC('month', date_id)` and sums all mood count columns.

#### Error Responses

| Status | Condition | Body |
| --- | --- | --- |
| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

---

## 5. Frontend View — Mood Over Time

### 5.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Mood Over Time                                              │
│  Period: [7d] [30d] [6m] [All Time]                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                                                        │  │
│  │        ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄              │  │
│  │      ▄▄████████████████████████████████▄▄             │  │
│  │    ▄▄██████████████████████████████████████▄▄         │  │
│  │   ████████████████████████████████████████████        │  │
│  │  ██████████████████████████████████████████████       │  │
│  │  ██████████████████████████████████████████████       │  │
│  │  ──────────────────────────────────────────────       │  │
│  │  Jan    Feb    Mar    Apr    May    Jun                │  │
│  │                                                        │  │
│  │  ● Happy  ● Sad  ● Angry  ● Calm  ● Energetic        │  │
│  │  ● Melancholic  ● Unclassified                        │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Chart Specification

- **Chart type:** Recharts `AreaChart` with stacked areas (`stackId="mood"`).
- **X-axis:** Date labels (month name for monthly, date for daily).
- **Y-axis:** Listen count.
- **Areas:** One `Area` component per mood class, stacked vertically.
- **Colors:** Same palette as Mood Donut Chart (FRD-002):
  - Happy: `#facc15` (yellow)
  - Sad: `#3b82f6` (blue)
  - Angry: `#ef4444` (red)
  - Calm: `#a78bfa` (violet)
  - Energetic: `#f97316` (orange)
  - Melancholic: `#6b7280` (gray)
  - Unclassified: `#e5e7eb` (light gray)
- **Tooltip:** On hover, show the date, total listens, and count per mood class.
- **Legend:** Below chart, showing mood class name + color swatch.

### 5.3 Variant: Percentage Mode (Nice-to-Have)

An optional toggle to switch the Y-axis from absolute counts to percentages (each time bucket sums to 100%). This makes it easier to see proportional mood shifts over time even when total listening volume changes.

- Implementation: Divide each `mood_<label>` by `total_listens` × 100 for each data point.
- Tooltip shows both count and percentage.

### 5.4 Interaction

- Period selector re-fetches data and re-renders the chart.
- Clicking a mood in the legend toggles its visibility (Recharts built-in feature).
- Loading state shown while fetching.

### 5.5 TypeScript Interface

```typescript
interface MoodTrendsResponse {
  period: "7d" | "30d" | "6m" | "all";
  granularity: "day" | "month";
  data: {
    date: string; // "YYYY-MM-DD" or "YYYY-MM"
    total_listens: number;
    mood_happy: number;
    mood_sad: number;
    mood_angry: number;
    mood_calm: number;
    mood_energetic: number;
    mood_melancholic: number;
    mood_unclassified: number;
  }[];
}
```

---

## 6. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| Period filter correctly scopes data | Compare data for `7d` vs `all` |
| Granularity is daily for `7d`/`30d` and monthly for `6m`/`all` | Check `granularity` field and `date` format in response |
| Mood counts per time bucket sum to `total_listens` (including unclassified) | `SUM(mood_*) == total_listens` for each data point |
| Stacked area chart renders correctly | Visual inspection |
| All mood classes visible as distinct colored areas | Visual inspection |
| Tooltip shows correct values on hover | Interactive testing |
| Legend toggles area visibility | Click legend items and verify |
| Period selector re-fetches and re-renders | Click each period button |
| Loading and error states work | Throttle network / kill API and verify |
