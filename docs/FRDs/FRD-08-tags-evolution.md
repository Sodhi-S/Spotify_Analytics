# FRD-008: Community Tag Evolution

## `/api/tags/evolution` Endpoint

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Requirements:** P5-7
**Author:** Sahej Singh Sodhi
**Created:** March 3, 2026
**Status:** Draft

---

## 1. Purpose

This FRD specifies the Community Tag Evolution endpoint: the FastAPI endpoint that shows how the user's top Last.fm community tags shift over time. This answers questions like "Am I listening to more electronic music lately?" or "When did I start getting into jazz?"

---

## 2. Scope

| In Scope | Out of Scope |
| --- | --- |
| `GET /api/tags/evolution` endpoint | Data ingestion and tag fetching (see FRD-001) |
| Tag ranking by month over time | Dedicated frontend view (see Section 6 for integration notes) |
| Period filtering | |

---

## 3. Data Dependencies

| Table | Used For |
| --- | --- |
| `fact_listens` | Listen events with `date_id`, `artist_id` |
| `dim_artists` | `genres` array (from Last.fm `artist.getTopTags`) — used as the tag source |
| `dim_dates` | Month grouping, period filtering |

**Tag Source Decision:** This endpoint uses **artist-level tags** (`dim_artists.genres` from `artist.getTopTags`) rather than track-level tags (`dim_tracks.top_tags` from `track.getTopTags`). Artist-level tags provide a more stable and meaningful genre/style signal for trend analysis. Track-level tags tend to be noisier (e.g., "love", "favorites", "2024"). This is consistent with the Top Tags calculation in FRD-002 (Overview Dashboard).

---

## 4. API Specification

### `GET /api/tags/evolution`

#### Request

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `period` | query string | No | `6m` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |
| `top_n` | query integer | No | `10` | Number of top tags to include. Max: `25`. |

**Granularity:** Data is always returned per **month**. For `7d` and `30d` periods, only 1 month of data may be returned — the current month.

#### Response

```json
{
  "period": "6m",
  "top_n": 10,
  "tags": ["indie rock", "dream pop", "hip hop", "electronic", "jazz", "shoegaze", "r&b", "punk", "ambient", "folk"],
  "data": [
    {
      "month": "2025-10",
      "tag_counts": {
        "indie rock": 187,
        "dream pop": 134,
        "hip hop": 98,
        "electronic": 76,
        "jazz": 45,
        "shoegaze": 42,
        "r&b": 38,
        "punk": 31,
        "ambient": 28,
        "folk": 22
      }
    },
    {
      "month": "2025-11",
      "tag_counts": {
        "indie rock": 201,
        "dream pop": 112,
        "hip hop": 115,
        "electronic": 89,
        "jazz": 67,
        "shoegaze": 38,
        "r&b": 42,
        "punk": 25,
        "ambient": 34,
        "folk": 19
      }
    }
  ]
}
```

#### Field Details

| Field | Source | Logic |
| --- | --- | --- |
| `tags` | Derived | The top N tags across the entire requested period, ranked by total listen count. This array defines which tags appear in each month's `tag_counts`. |
| `month` | `dim_dates.date_id` | `DATE_TRUNC('month', date_id)` formatted as `YYYY-MM` |
| `tag_counts.*` | `fact_listens` → `dim_artists.genres` | Listen-weighted tag count per month (same methodology as FRD-002 Section 5) |

#### Tag Counting Methodology

Same as FRD-002:

1. For each listen in `fact_listens` (within the requested period), look up the artist's `genres` array from `dim_artists` (WHERE `is_current = TRUE`).
2. Credit each tag in the array equally with +1 listen count.
3. Group by month and tag.
4. Determine the top N tags across the entire period (sum across all months).
5. Return monthly counts for only those top N tags.

**Why top N across the whole period (not per month)?** This ensures consistent tag columns across all months. If top N were calculated per month, different months would have different tags, making trend visualization difficult.

#### Error Responses

| Status | Condition | Body |
| --- | --- | --- |
| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |
| 400 | `top_n` < 1 or > 25 | `{"detail": "top_n must be between 1 and 25"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

---

## 5. dbt Model Considerations

This query involves:
1. Exploding the `genres` array from `dim_artists` (one row per tag per artist).
2. Joining to `fact_listens` (one row per listen).
3. Grouping by month and tag.

This can be expensive if done in real-time via FastAPI SQL. Consider creating a dbt mart model:

**`mart_tag_listen_counts_monthly`**

| Column | Type | Description |
| --- | --- | --- |
| `month` | DATE | First of month (truncated) |
| `tag` | VARCHAR | Normalized tag name (lowercase, trimmed) |
| `listen_count` | INTEGER | Number of listens credited to this tag in this month |

This mart table pre-computes the listen-weighted tag counts by month, and the FastAPI endpoint simply queries, ranks, and returns the top N.

---

## 6. Frontend Integration

The PRD does not assign this endpoint to a specific named frontend view. Integration options:

### Option A: Line Chart on Overview or Separate Tab

A multi-line chart (Recharts `LineChart`) with one line per top tag, X-axis = month, Y-axis = listen count. This shows how tag popularity rises and falls over time.

### Option B: Stacked Area Chart

Similar to Mood Over Time (FRD-004) but with tags instead of mood classes. Shows proportional composition of listening by tag.

### Option C: Bump Chart / Rank Chart

Show tag rank (1st, 2nd, 3rd...) over time rather than absolute counts. Highlights overtaking moments (e.g., "hip hop overtook dream pop in December").

**Decision:** Defer to Phase 6 implementation. The endpoint is built in Phase 5; the frontend visualization approach is decided during Phase 6.

### TypeScript Interface

```typescript
interface TagsEvolutionResponse {
  period: "7d" | "30d" | "6m" | "all";
  top_n: number;
  tags: string[];
  data: {
    month: string; // "YYYY-MM"
    tag_counts: {
      [tag: string]: number;
    };
  }[];
}
```

---

## 7. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| `tags` array contains exactly `top_n` entries | Verify length matches `top_n` param |
| Tags are consistent across all months in `data` | Verify every `tag_counts` object has the same keys |
| Tag counts use listen-weighted methodology (each artist tag gets +1 per listen) | Manually verify with a SQL query |
| Period filter correctly scopes data | Compare data for `30d` vs `all` |
| `top_n` parameter works (default 10, max 25) | Request with `top_n=5` returns 5 tags, `top_n=26` returns 400 |
| Monthly granularity is correct | Verify `month` values are `YYYY-MM` format |
| Tag names are normalized (lowercase, trimmed) | Check response for inconsistent casing |
