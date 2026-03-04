# FRD-007: Mood by Time of Day

## `/api/mood/by-time` Endpoint

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Requirements:** P5-5
**Author:** Sahej Singh Sodhi
**Created:** March 3, 2026
**Status:** Draft

---

## 1. Purpose

This FRD specifies the Mood by Time endpoint: the FastAPI endpoint that serves mood label distribution broken down by hour of day and day of week. This feature enables analysis like "Do you listen to more energetic music in the morning?" or "Are weekends calmer than weekdays?"

---

## 2. Scope

| In Scope | Out of Scope |
| --- | --- |
| `GET /api/mood/by-time` endpoint | Data ingestion, mood classification pipeline (see FRD-001) |
| Mood distribution by hour of day | Dedicated frontend view (data may be rendered as an overlay on the Listening Heatmap or as a supplementary chart) |
| Mood distribution by day of week | |
| Period filtering | |

---

## 3. Data Dependencies

| Table | Used For |
| --- | --- |
| `fact_listens` | Listen events with `hour` and `date_id` — joined to `dim_tracks` for `mood_label` |
| `dim_tracks` | `mood_label` per track |
| `dim_dates` | `day_of_week`, period filtering |

---

## 4. API Specification

### `GET /api/mood/by-time`

#### Request

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `period` | query string | No | `30d` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |
| `group_by` | query string | No | `hour` | Grouping dimension. Accepted values: `hour`, `day`. |

**`group_by` behavior:**

| Value | Result |
| --- | --- |
| `hour` | Mood distribution aggregated by hour of day (0–23). 24 buckets. |
| `day` | Mood distribution aggregated by day of week (Monday–Sunday). 7 buckets. |

#### Response — `group_by=hour`

```json
{
  "period": "30d",
  "group_by": "hour",
  "data": [
    {
      "hour": 0,
      "total_listens": 34,
      "mood_distribution": {
        "happy": 5,
        "sad": 12,
        "angry": 2,
        "calm": 8,
        "energetic": 3,
        "melancholic": 3,
        "unclassified": 1
      }
    },
    {
      "hour": 8,
      "total_listens": 87,
      "mood_distribution": {
        "happy": 22,
        "sad": 8,
        "angry": 5,
        "calm": 12,
        "energetic": 31,
        "melancholic": 5,
        "unclassified": 4
      }
    }
  ]
}
```

#### Response — `group_by=day`

```json
{
  "period": "30d",
  "group_by": "day",
  "data": [
    {
      "day": "Monday",
      "total_listens": 198,
      "mood_distribution": {
        "happy": 42,
        "sad": 31,
        "angry": 18,
        "calm": 38,
        "energetic": 45,
        "melancholic": 16,
        "unclassified": 8
      }
    }
  ]
}
```

#### Field Details

| Field | Source | Logic |
| --- | --- | --- |
| `hour` | `fact_listens.hour` | Hour of day (0–23). Present only when `group_by=hour`. |
| `day` | `dim_dates.day_of_week` | Day of week. Present only when `group_by=day`. |
| `total_listens` | `fact_listens` | `COUNT(*)` per bucket |
| `mood_distribution.*` | `fact_listens` → `dim_tracks.mood_label` | `COUNT(*)` per mood label per bucket. `unclassified` = count where `mood_label IS NULL`. |

#### SQL Logic (pseudocode for `group_by=hour`)

```sql
SELECT
    f.hour,
    COUNT(*) AS total_listens,
    COUNT(*) FILTER (WHERE t.mood_label = 'happy') AS happy,
    COUNT(*) FILTER (WHERE t.mood_label = 'sad') AS sad,
    COUNT(*) FILTER (WHERE t.mood_label = 'angry') AS angry,
    COUNT(*) FILTER (WHERE t.mood_label = 'calm') AS calm,
    COUNT(*) FILTER (WHERE t.mood_label = 'energetic') AS energetic,
    COUNT(*) FILTER (WHERE t.mood_label = 'melancholic') AS melancholic,
    COUNT(*) FILTER (WHERE t.mood_label IS NULL) AS unclassified
FROM fact_listens f
JOIN dim_tracks t ON f.track_id = t.track_id
JOIN dim_dates d ON f.date_id = d.date_id
WHERE d.date_id >= :period_start
GROUP BY f.hour
ORDER BY f.hour;
```

**Warehouse portability note:** `FILTER (WHERE ...)` is PostgreSQL-specific. For Snowflake compatibility, use `CASE WHEN ... THEN 1 ELSE 0 END` inside `SUM()` instead — or isolate behind a dbt macro. This is one of the queries that should be moved into a dbt model rather than raw SQL in FastAPI.

#### Error Responses

| Status | Condition | Body |
| --- | --- | --- |
| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |
| 400 | Invalid `group_by` value | `{"detail": "Invalid group_by. Accepted values: hour, day"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

---

## 5. Frontend Integration

The PRD does not specify a dedicated standalone view for this endpoint. The data can be integrated into existing views:

### Option A: Heatmap Overlay

Enhance the Listening Heatmap (FRD-005) with a "Color by mood" toggle. Instead of coloring cells by listen count, color them by dominant mood label. This would use the `group_by=hour` data cross-referenced with day of week.

### Option B: Supplementary Bar Chart

Add a small stacked bar chart below the Listening Heatmap showing mood distribution per hour (or per day of week) as a summary view.

### Option C: Standalone Section

Render as its own section with two tabs: "By Hour" and "By Day of Week", each showing a stacked bar chart of mood distribution.

**Decision:** Defer to Phase 6 implementation. The endpoint is built in Phase 5; the frontend integration approach is decided during Phase 6 based on the overall dashboard layout.

### TypeScript Interface

```typescript
interface MoodByTimeResponse {
  period: "7d" | "30d" | "6m" | "all";
  group_by: "hour" | "day";
  data: {
    hour?: number;         // 0-23, present when group_by=hour
    day?: string;          // Monday-Sunday, present when group_by=day
    total_listens: number;
    mood_distribution: {
      [mood_label: string]: number;
    };
  }[];
}
```

---

## 6. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| `group_by=hour` returns up to 24 buckets (0–23) | Verify response has entries for hours with listens |
| `group_by=day` returns up to 7 buckets (Monday–Sunday) | Verify response has entries for days with listens |
| `mood_distribution` values sum to `total_listens` for each bucket | Verify per bucket |
| Period filter correctly scopes data | Compare data for `7d` vs `all` |
| SQL is warehouse-portable (no PostgreSQL-specific syntax in production queries) | Code review or `dbt run --target snowflake` |
| Invalid `group_by` returns 400 | Send `group_by=invalid` and verify |
