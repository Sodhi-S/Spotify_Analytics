# FRD-005: Listening Heatmap# FRD-005: Listening Heatmap



## `/api/listening/heatmap` Endpoint + Listening Heatmap Frontend View## `/api/listening/heatmap` Endpoint + Listening Heatmap Frontend View



**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)**Parent PRD:** [Spotify Listening Intelligence Platform — PRD v0.2](../PRD/prd.md)

**PRD Requirements:** P5-4, P6-3**PRD Requirements:** P5-4, P6-1

**Author:** Sahej Singh Sodhi**Author:** Sahej Singh Sodhi

**Created:** March 2, 2026**Created:** March 2, 2026

**Updated:** March 3, 2026**Status:** Draft

**Status:** Draft

---

---

## 1. Purpose

## 1. Purpose

This FRD specifies the Listening Heatmap feature: the FastAPI endpoint that returns listen counts bucketed by hour of day and day of week, and the React frontend view that renders a GitHub-style heatmap grid showing when the user listens to music most.

This FRD specifies the Listening Heatmap feature: the FastAPI endpoint that serves hourly listening activity data and the React frontend view that displays it as a Day-of-Week × Hour-of-Day heatmap grid. This feature helps the user understand their listening patterns (when they listen most/least).

---

---

## 2. Scope

## 2. Scope

| In Scope | Out of Scope |

| In Scope | Out of Scope || --- | --- |

| --- | --- || `GET /api/listening/heatmap` endpoint | Data ingestion and transformation (see FRD-001) |

| `GET /api/listening/heatmap` endpoint | Data ingestion (see FRD-001) || Listening Heatmap frontend view (D3 grid) | Other chart views (see other FRDs) |

| Hour × Day heatmap grid visualization (D3) | Other dashboard views (see other FRDs) || Time period filtering (7d, 30d, 6m, all) | |

| Period filtering | |

---

---

## 3. Data Dependencies

## 3. Data Dependencies

| Table | Used For |

| Table | Used For || --- | --- |

| --- | --- || `fact_listens` | `hour` column (0–23) and `date_id` for period filtering |

| `fact_listens` | Listen events with `played_at` timestamp (used to derive hour and day of week) || `dim_dates` | `day_of_week` for the day axis |

| `dim_dates` | `day_of_week`, period filtering |

---

---

## 4. API Specification

## 4. API Specification

### `GET /api/listening/heatmap`

### `GET /api/listening/heatmap`

#### Request

#### Request

| Parameter | Type | Required | Default | Description |

| Parameter | Type | Required | Default | Description || --- | --- | --- | --- | --- |

| --- | --- | --- | --- | --- || `period` | query string | No | `all` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |

| `period` | query string | No | `30d` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |

**Period definitions:** Same as other endpoints — `7d`, `30d`, `6m`, `all`.

**Period definitions:**

#### Response

| Value | Meaning |

| --- | --- |The response is a flat array of cells, one per `(day_of_week, hour)` combination. There are always exactly **168 cells** (7 days × 24 hours), even if some have a count of 0.

| `7d` | Last 7 calendar days |

| `30d` | Last 30 calendar days |```json

| `6m` | Last 6 calendar months (180 days) |{

| `all` | All data |  "period": "30d",

  "cells": [

#### Response    { "day_of_week": "Mon", "hour": 0, "listen_count": 3 },

    { "day_of_week": "Mon", "hour": 1, "listen_count": 1 },

```json    { "day_of_week": "Mon", "hour": 2, "listen_count": 0 },

{    ...

  "period": "30d",    { "day_of_week": "Sun", "hour": 23, "listen_count": 5 }

  "heatmap": [  ],

    {  "max_count": 47,

      "day": "Monday",  "total_listens": 1423

      "hour": 0,}

      "listen_count": 3```

    },

    {**Field descriptions:**

      "day": "Monday",

      "hour": 1,| Field | Description |

      "listen_count": 1| --- | --- |

    },| `cells` | Array of 168 objects (7 × 24). Ordered by day (Mon → Sun), then hour (0 → 23). |

    {| `day_of_week` | Three-letter day abbreviation: `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`. |

      "day": "Monday",| `hour` | Integer 0–23 representing hour of day. |

      "hour": 8,| `listen_count` | Number of listens in this `(day, hour)` bucket for the given period. |

      "listen_count": 12| `max_count` | The maximum `listen_count` across all 168 cells (for color scale normalization). |

    }| `total_listens` | Sum of all `listen_count` values (convenience field). |

  ]

}#### Query Logic

```

```sql

The response contains one object per `(day, hour)` combination. There are up to 168 entries (7 days × 24 hours).SELECT

  d.day_of_week,

#### Field Details  f.hour,

  COUNT(*) AS listen_count

| Field | Type | Description |FROM fact_listens f

| --- | --- | --- |JOIN dim_dates d ON f.date_id = d.date_id

| `day` | string | Day of week: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday` |WHERE f.date_id >= :start_date  -- computed from period

| `hour` | integer | Hour of day: 0–23 (24-hour format) |GROUP BY d.day_of_week, f.hour

| `listen_count` | integer | Number of listens in this `(day, hour)` bucket for the requested period |ORDER BY

  CASE d.day_of_week

#### SQL Logic    WHEN 'Mon' THEN 1 WHEN 'Tue' THEN 2 WHEN 'Wed' THEN 3

    WHEN 'Thu' THEN 4 WHEN 'Fri' THEN 5 WHEN 'Sat' THEN 6

```sql    WHEN 'Sun' THEN 7

SELECT  END,

    dim_dates.day_of_week AS day,  f.hour

    fact_listens.hour AS hour,```

    COUNT(*) AS listen_count

FROM fact_listens**Filling zeros:** The SQL query only returns rows where `listen_count > 0`. The FastAPI endpoint must fill in missing `(day, hour)` combinations with `listen_count: 0` to always return exactly 168 cells. This is done in Python after the query:

JOIN dim_dates ON fact_listens.date_id = dim_dates.date_id

WHERE dim_dates.date_id >= :period_start```python

GROUP BY dim_dates.day_of_week, fact_listens.hour# Generate all 168 combinations

ORDER BY dim_dates.day_of_week, fact_listens.hour;DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

```all_cells = {(day, hour): 0 for day in DAYS for hour in range(24)}



**Timezone consideration:** `fact_listens.hour` is derived from `played_at` during dbt staging. The timezone used for extraction should be the user's local timezone (stored in `.env` as `USER_TIMEZONE` or defaulting to UTC). This must be documented.# Overlay query results

for row in query_results:

#### Error Responses    all_cells[(row.day_of_week, row.hour)] = row.listen_count



| Status | Condition | Body |# Convert to response format

| --- | --- | --- |cells = [

| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |    {"day_of_week": day, "hour": hour, "listen_count": count}

| 500 | Database error | `{"detail": "Internal server error"}` |    for (day, hour), count in sorted(

        all_cells.items(),

---        key=lambda x: (DAYS.index(x[0][0]), x[0][1])

    )

## 5. Frontend View — Listening Heatmap]

```

### 5.1 Layout

#### Error Responses

```

┌──────────────────────────────────────────────────────────────┐| Status | Condition | Body |

│  Listening Heatmap                                           │| --- | --- | --- |

│  Period: [7d] [30d] [6m] [All Time]                          │| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |

├──────────────────────────────────────────────────────────────┤| 500 | Database error | `{"detail": "Internal server error"}` |

│                                                              │

│         0  1  2  3  4  5  6  7  8  9 10 11 12 ...  23       │---

│  Mon   [  ][  ][  ][  ][  ][  ][  ][██][██][██][██][ ]       │

│  Tue   [  ][  ][  ][  ][  ][  ][  ][██][██][██][██][ ]       │## 5. Frontend View — Listening Heatmap

│  Wed   [  ][  ][  ][  ][  ][  ][  ][██][██][  ][██][ ]       │

│  Thu   [  ][  ][  ][  ][  ][  ][  ][██][██][██][██][ ]       │### 5.1 Layout

│  Fri   [  ][  ][  ][  ][  ][  ][  ][  ][██][██][██][█]       │

│  Sat   [  ][  ][██][██][  ][  ][  ][  ][  ][██][██][█]       │```

│  Sun   [  ][  ][██][  ][  ][  ][  ][  ][  ][██][██][█]       │┌─────────────────────────────────────────────────────────────┐

│                                                              ││  Period: [7d] [30d] [6m] [All Time]                         │

│  ░░░░░░░░░░░░████████████████████████  (color gradient)      │├─────────────────────────────────────────────────────────────┤

│  0 listens              max listens                          ││                                                             │

│                                                              ││  Listening Heatmap                                          │

└──────────────────────────────────────────────────────────────┘│                                                             │

```│        Mon  Tue  Wed  Thu  Fri  Sat  Sun                    │

│   0:00  ░    ░    ░    ░    ░    ░    ░                     │

### 5.2 Chart Specification│   1:00  ░    ░    ░    ░    ░    ░    ░                     │

│   2:00  ░    ░    ░    ░    ░    ░    ░                     │

- **Chart type:** D3.js custom heatmap grid (not Recharts — D3 provides finer control for grid-based heatmaps).│   ...                                                       │

- **Grid:** 7 rows (days of week, Monday–Sunday) × 24 columns (hours, 0–23).│   8:00  ▓    ▓    ▓    ▓    ▓    ░    ░                     │

- **Cell size:** Fixed square cells with small gap between.│   9:00  ▓    ▓    ▓    ▓    ▓    ░    ░                     │

- **Color scale:** Sequential single-hue gradient (e.g., white → dark green, or white → dark blue).│   ...                                                       │

  - Min value (0 or lowest count): lightest color / white.│  20:00  █    █    █    █    █    ██   ██                    │

  - Max value: darkest color.│  21:00  ██   ██   ██   ██   █    ██   ██                   │

  - Use D3 `scaleSequential` with `interpolateGreens` or similar.│  22:00  █    █    █    █    ▓    █    █                     │

- **Legend:** A continuous gradient bar at the bottom with min and max labels.│  23:00  ▓    ▓    ░    ░    ░    ▓    ▓                     │

│                                                             │

### 5.3 Interaction│  ░ = 0  ▒ = low  ▓ = medium  █ = high                      │

│                                                             │

- **Hover tooltip:** On hover over a cell, show: "Monday 8:00 AM — 12 listens".│  Total listens: 1,423                                       │

- **Period selector:** Re-fetches data and re-renders the heatmap.│                                                             │

- **Loading state:** Skeleton grid shown while fetching.└─────────────────────────────────────────────────────────────┘

```

### 5.4 Empty Cells

### 5.2 Components

- `(day, hour)` combinations not present in the API response default to 0 listens.

- The frontend must generate a full 7×24 grid and fill in missing cells with 0.| Component | Library | Details |

| --- | --- | --- |

### 5.5 TypeScript Interface| `PeriodSelector` | Native React | Same reusable component as other views |

| `HeatmapGrid` | **D3** | Custom D3 SVG heatmap (not Recharts) |

```typescript| `HeatmapTooltip` | D3 / Native React | Tooltip on hover showing `day`, `hour`, `listen_count` |

interface HeatmapResponse {

  period: "7d" | "30d" | "6m" | "all";### 5.3 D3 Heatmap Specification

  heatmap: {

    day: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday";- **Grid:** 7 columns (Mon–Sun) × 24 rows (0:00–23:00).

    hour: number; // 0-23- **Cell size:** Computed dynamically to fill the container width. Recommended: ~30–40px per cell.

    listen_count: number;- **X-axis labels:** Day of week (Mon, Tue, …, Sun) across the top.

  }[];- **Y-axis labels:** Hour of day (0:00, 1:00, …, 23:00) along the left side.

}- **Color scale:** Sequential single-hue scale (e.g., green or blue) using D3's `d3.scaleSequential(d3.interpolateGreens)`.

```  - Domain: `[0, max_count]` (from the API response).

  - A `listen_count` of 0 renders as the lightest shade or a neutral background color.

---- **Tooltip:** On hover over a cell, display:

  - Day of week

## 6. Acceptance Criteria  - Hour (e.g., "8:00 PM – 9:00 PM")

  - Listen count

| Criteria | Verification |- **Legend:** A small gradient bar below the grid showing the color scale from 0 to `max_count`.

| --- | --- |

| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |### 5.4 Interaction

| Period filter correctly scopes data | Compare listen counts for `7d` vs `all` |

| All 168 (day, hour) cells are represented in the grid (missing → 0) | Count cells on frontend |- Changing the period re-fetches from the API and re-renders the heatmap.

| Color scale correctly maps from min to max | Visual inspection — darkest cells should have highest counts |- Hovering over a cell shows the tooltip.

| Tooltip shows correct day, hour, and listen count | Hover over cells and verify |- No click interaction required.

| Period selector re-fetches and re-renders | Click each period button |

| Timezone handling is documented | Check README or `.env` for timezone config |### 5.5 TypeScript Interface

| Loading and error states work | Throttle network / kill API and verify |

```typescript
interface HeatmapResponse {
  period: "7d" | "30d" | "6m" | "all";
  cells: {
    day_of_week: "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun";
    hour: number; // 0–23
    listen_count: number;
  }[];
  max_count: number;
  total_listens: number;
}
```

---

## 6. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint always returns exactly 168 cells | `response.cells.length === 168` |
| All 7 × 24 combinations are present (including zeros) | Verify all day/hour combos exist |
| `max_count` equals the actual maximum across all cells | `max_count === Math.max(...cells.map(c => c.listen_count))` |
| Period filter scopes the data correctly | Compare `total_listens` for `7d` vs `all` |
| D3 heatmap renders a 7×24 grid | Visual inspection |
| Color intensity corresponds to listen count | Cells with 0 are lightest, cells with max are darkest |
| Tooltip displays correct day, hour, and count | Hover over cells and verify |
| Period selector re-fetches and re-renders | Change period and verify grid updates |
| Heatmap is rendered with D3, not Recharts | Code inspection — must use `d3.select()`, not `<ResponsiveContainer>` |
