# FRD-006: Mood vs Weather Correlation# FRD-006: Weather Correlation



## `/api/weather-correlation` Endpoint + Mood vs Weather Frontend View## `/api/weather-correlation` Endpoint + Weather Display



**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)**Parent PRD:** [Spotify Listening Intelligence Platform — PRD v0.2](../PRD/prd.md)

**PRD Requirements:** P5-6, P6-1 (Mood vs Weather view)**PRD Requirements:** P3-2, P3-3, P5-6

**Author:** Sahej Singh Sodhi**Author:** Sahej Singh Sodhi

**Created:** March 2, 2026**Created:** March 2, 2026

**Updated:** March 3, 2026**Status:** Draft

**Status:** Draft

---

---

## 1. Purpose

## 1. Purpose

This FRD specifies the Weather Correlation feature: the FastAPI endpoint that returns listening mood (average valence) alongside weather conditions, enabling the user to see whether their music choices are influenced by weather. The core question it answers: *"Do you listen to sadder music on rainy days?"*

This FRD specifies the Mood vs Weather Correlation feature: the FastAPI endpoint that serves mood label distribution alongside daily weather conditions, and the React frontend view that visualizes the relationship. The core question this feature answers is: **"Do you listen to sadder music on rainy days?"**

---

---

## 2. Scope

## 2. Scope

| In Scope | Out of Scope |

| In Scope | Out of Scope || --- | --- |

| --- | --- || `GET /api/weather-correlation` endpoint | Weather data ingestion (see FRD-001) |

| `GET /api/weather-correlation` endpoint | Weather data ingestion (see FRD-001) || Correlation between listening mood (avg valence) and weather conditions | Advanced statistical analysis (regression, p-values) |

| Mood vs Weather frontend view (bar or scatter chart) | Mood classification pipeline (see FRD-001) || Frontend visualization | K-Means mood clustering (see FRD-007, Nice to Have) |

| Period filtering | Other dashboard views (see other FRDs) |

---

---

## 3. Key Definitions

## 3. Data Dependencies

### Listening Mood = Average Valence

| Table | Used For |

| --- | --- |- **Mood** in this feature is defined as the **average valence** of all tracks listened to on a given day.

| `mart_listening_summary` | Daily mood count columns (`mood_happy_count`, `mood_sad_count`, etc.) |- Valence is a Spotify audio feature (0.0 to 1.0) that measures how "happy" or "positive" a track sounds.

| `dim_weather` | Daily weather: `temp_c`, `precipitation`, `weather_code` |  - **Low valence** (< 0.3): Sad, angry, or dark-sounding music.

| `dim_dates` | Join key between listening summary and weather, period filtering |  - **Mid valence** (0.3–0.7): Neutral or mixed mood.

  - **High valence** (> 0.7): Happy, cheerful, euphoric music.

---- This is a simplified but effective proxy for "mood." Future iterations could incorporate energy and danceability for a richer mood definition.



## 4. Weather Code Grouping---



Open-Meteo's `weather_code` follows the WMO (World Meteorological Organization) standard. For this feature, raw weather codes are grouped into human-readable weather condition categories:## 4. Data Dependencies



| Weather Group | WMO Codes | Description || Table | Used For |

| --- | --- | --- || --- | --- |

| `clear` | 0, 1 | Clear sky, mainly clear || `mart_listening_summary` | `avg_valence` and `total_listens` per day |

| `cloudy` | 2, 3 | Partly cloudy, overcast || `dim_weather` | `temp_c`, `precipitation`, `weather_code` per day |

| `fog` | 45, 48 | Fog, depositing rime fog || `dim_dates` | Join key (`date_id`), plus `day_of_week`, `is_weekend` |

| `drizzle` | 51, 53, 55 | Drizzle (light, moderate, dense) |

| `rain` | 61, 63, 65, 80, 81, 82 | Rain (slight, moderate, heavy) + rain showers |---

| `snow` | 71, 73, 75, 77, 85, 86 | Snow (slight, moderate, heavy) + snow showers + snow grains |

| `thunderstorm` | 95, 96, 99 | Thunderstorm, with hail |## 5. API Specification



This grouping should be implemented as a dbt model or a Python utility function so it's reusable and easy to update. The grouping logic is applied in the API layer or a dbt intermediate model — not in the frontend.### `GET /api/weather-correlation`



---#### Request



## 5. API Specification| Parameter | Type | Required | Default | Description |

| --- | --- | --- | --- | --- |

### `GET /api/weather-correlation`| `period` | query string | No | `all` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |



#### Request#### Response



| Parameter | Type | Required | Default | Description |```json

| --- | --- | --- | --- | --- |{

| `period` | query string | No | `6m` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |  "period": "6m",

  "daily_data": [

#### Response    {

      "date": "2025-12-15",

```json      "day_of_week": "Mon",

{      "is_weekend": false,

  "period": "6m",      "avg_valence": 0.42,

  "data": [      "total_listens": 34,

    {      "temp_c": 2.5,

      "weather_group": "clear",      "precipitation": 12.3,

      "day_count": 42,      "weather_code": 61,

      "total_listens": 1893,      "weather_description": "Rain: Slight intensity"

      "mood_distribution": {    }

        "happy": 512,  ],

        "sad": 198,  "summary_by_weather": [

        "angry": 87,    {

        "calm": 345,      "weather_category": "Clear",

        "energetic": 498,      "avg_valence": 0.62,

        "melancholic": 156,      "avg_temp_c": 18.4,

        "unclassified": 97      "total_days": 45,

      }      "total_listens": 1520

    },    },

    {    {

      "weather_group": "rain",      "weather_category": "Rain",

      "day_count": 18,      "avg_valence": 0.48,

      "total_listens": 876,      "avg_temp_c": 8.2,

      "mood_distribution": {      "total_days": 22,

        "happy": 134,      "total_listens": 780

        "sad": 231,    },

        "angry": 98,    {

        "calm": 178,      "weather_category": "Snow",

        "energetic": 112,      "avg_valence": 0.44,

        "melancholic": 89,      "avg_temp_c": -3.1,

        "unclassified": 34      "total_days": 10,

      }      "total_listens": 340

    }    }

  ]  ]

}}

``````



#### Field Details#### Field Descriptions



| Field | Source | Logic |**`daily_data`** — One row per calendar date (where both listening data and weather data exist):

| --- | --- | --- |

| `weather_group` | `dim_weather.weather_code` | Mapped to group using the WMO grouping table above || Field | Source | Description |

| `day_count` | `dim_weather` + `dim_dates` | `COUNT(DISTINCT date_id)` per weather group in the filtered period || --- | --- | --- |

| `total_listens` | `mart_listening_summary.total_listens` | `SUM(total_listens)` for all days in this weather group || `date` | `dim_dates.date_id` | Calendar date |

| `mood_distribution.happy` | `mart_listening_summary.mood_happy_count` | `SUM(mood_happy_count)` for all days in this weather group || `day_of_week` | `dim_dates.day_of_week` | Three-letter abbreviation |

| `mood_distribution.sad` | `mart_listening_summary.mood_sad_count` | `SUM(mood_sad_count)` for all days in this weather group || `is_weekend` | `dim_dates.is_weekend` | Boolean |

| ... (etc.) | ... | Same pattern for all mood classes || `avg_valence` | `mart_listening_summary.avg_valence` | Average valence of listens that day (the "mood" metric) |

| `mood_distribution.unclassified` | `mart_listening_summary.mood_null_count` | `SUM(mood_null_count)` for all days in this weather group || `total_listens` | `mart_listening_summary.total_listens` | Number of listens that day |

| `temp_c` | `dim_weather.temp_c` | Daily max temperature (°C) |

#### SQL Logic (pseudocode)| `precipitation` | `dim_weather.precipitation` | Daily precipitation sum (mm) |

| `weather_code` | `dim_weather.weather_code` | WMO weather code (integer) |

```sql| `weather_description` | Derived from `weather_code` | Human-readable description (see Section 5.1) |

SELECT

    weather_group(w.weather_code) AS weather_group,**`summary_by_weather`** — Aggregated view, one row per weather category:

    COUNT(DISTINCT d.date_id) AS day_count,

    SUM(m.total_listens) AS total_listens,| Field | Description |

    SUM(m.mood_happy_count) AS happy,| --- | --- |

    SUM(m.mood_sad_count) AS sad,| `weather_category` | Grouped weather label (see Section 5.1) |

    SUM(m.mood_angry_count) AS angry,| `avg_valence` | Listen-weighted average valence across all days in this category |

    SUM(m.mood_calm_count) AS calm,| `avg_temp_c` | Average temperature across days in this category |

    SUM(m.mood_energetic_count) AS energetic,| `total_days` | Number of days in this category |

    SUM(m.mood_melancholic_count) AS melancholic,| `total_listens` | Total listens across days in this category |

    SUM(m.mood_null_count) AS unclassified

FROM mart_listening_summary m### 5.1 Weather Code → Category Mapping

JOIN dim_dates d ON m.date_id = d.date_id

JOIN dim_weather w ON d.date_id = w.date_idOpen-Meteo uses WMO weather codes. Group them into high-level categories:

WHERE d.date_id >= :period_start

GROUP BY weather_group(w.weather_code)| WMO Codes | Category | Description |

ORDER BY total_listens DESC;| --- | --- | --- |

```| 0, 1 | Clear | Clear sky, mainly clear |

| 2, 3 | Cloudy | Partly cloudy, overcast |

#### Error Responses| 45, 48 | Fog | Fog, depositing rime fog |

| 51, 53, 55 | Drizzle | Drizzle (light, moderate, dense) |

| Status | Condition | Body || 61, 63, 65 | Rain | Rain (slight, moderate, heavy) |

| --- | --- | --- || 66, 67 | Freezing Rain | Freezing rain (light, heavy) |

| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` || 71, 73, 75, 77 | Snow | Snowfall (slight, moderate, heavy), snow grains |

| 500 | Database error | `{"detail": "Internal server error"}` || 80, 81, 82 | Showers | Rain showers (slight, moderate, violent) |

| 85, 86 | Snow Showers | Snow showers (slight, heavy) |

---| 95, 96, 99 | Thunderstorm | Thunderstorm, thunderstorm with hail |



## 6. Frontend View — Mood vs WeatherThis mapping is implemented as a lookup table or Python dictionary in FastAPI — not stored in the database.



### 6.1 Layout#### Query Logic



``````sql

┌──────────────────────────────────────────────────────────────┐SELECT

│  Mood vs Weather                                             │  d.date_id AS date,

│  Period: [7d] [30d] [6m] [All Time]                          │  d.day_of_week,

├──────────────────────────────────────────────────────────────┤  d.is_weekend,

│                                                              │  m.avg_valence,

│  ┌────────────────────────────────────────────────────────┐  │  m.total_listens,

│  │                                                        │  │  w.temp_c,

│  │   ████████████████████████████████  Clear (42 days)    │  │  w.precipitation,

│  │   ████████████████████            Rain (18 days)       │  │  w.weather_code

│  │   ██████████████                  Cloudy (23 days)     │  │FROM mart_listening_summary m

│  │   ██████                          Snow (7 days)        │  │JOIN dim_dates d ON m.date_id = d.date_id

│  │   ████                            Fog (4 days)         │  │JOIN dim_weather w ON d.date_id = w.date_id

│  │                                                        │  │WHERE d.date_id >= :start_date  -- computed from period

│  │   ● Happy  ● Sad  ● Angry  ● Calm  ● Energetic        │  │ORDER BY d.date_id ASC

│  │   ● Melancholic  ● Unclassified                        │  │```

│  │                                                        │  │

│  └────────────────────────────────────────────────────────┘  │The `summary_by_weather` aggregation is computed in Python after the query, using the weather code → category mapping to group rows and compute weighted averages.

│                                                              │

│  Toggle: [Absolute Counts] [Percentages]                     │#### Error Responses

│                                                              │

└──────────────────────────────────────────────────────────────┘| Status | Condition | Body |

```| --- | --- | --- |

| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |

### 6.2 Chart Specification — Stacked Horizontal Bar Chart| 500 | Database error | `{"detail": "Internal server error"}` |



- **Chart type:** Recharts `BarChart` with `layout="vertical"` and stacked bars.---

- **Y-axis:** Weather group labels (Clear, Rain, Cloudy, etc.) — sorted by total listens descending.

- **X-axis:** Listen count (absolute mode) or percentage (percentage mode).## 6. Frontend Visualization

- **Bars:** Each bar is stacked by mood class — same segments as the Mood Donut Chart.

- **Colors:** Same mood palette as FRD-002 and FRD-004:The Weather Correlation view is part of the main dashboard. Suggested visualization approach:

  - Happy: `#facc15`, Sad: `#3b82f6`, Angry: `#ef4444`, Calm: `#a78bfa`, Energetic: `#f97316`, Melancholic: `#6b7280`, Unclassified: `#e5e7eb`

### 6.1 Layout

### 6.3 Percentage Mode Toggle

```

- **Absolute mode (default):** X-axis shows raw listen counts. Each stacked bar's total width = `total_listens` for that weather group.┌─────────────────────────────────────────────────────────────┐

- **Percentage mode:** Each bar is normalized to 100% width. Each mood segment shows its proportion of the weather group's total listens.│  Period: [7d] [30d] [6m] [All Time]                         │

- Percentage mode makes it much easier to compare mood distributions across weather groups of very different sizes (e.g., 42 clear days vs 4 fog days).├─────────────────────────────────────────────────────────────┤

│                                                             │

### 6.4 Interaction│  ┌─────────────────────────────────────────────────────┐    │

│  │  Mood vs Weather (Scatter / Line)                    │    │

- Period selector re-fetches data and re-renders.│  │                                                      │    │

- Toggle switches between absolute and percentage modes (client-side recalculation, no new API call).│  │  1.0 ┤                                  ● Clear       │    │

- Tooltip on hover over a bar segment: "Rain — Sad: 231 listens (26.4%)".│  │      │          ●                       ● Cloudy      │    │

- Weather groups with 0 days in the period are not displayed.│  │ Avg  │   ●  ●     ●  ●                 ● Rain        │    │

- Legend toggles mood class visibility.│  │ Val  │ ●       ●       ●  ●                          │    │

│  │  0.5 ┤    ●                                          │    │

### 6.5 Insight Callout (Nice-to-Have)│  │      │ ●                                              │    │

│  │      │                                                │    │

A text callout below the chart that auto-generates a natural language insight. Example:│  │  0.0 ┤──────────────────────────                     │    │

│  │      -5    0    5    10   15   20   25  °C            │    │

> "On rainy days, you listen to 31% more sad music compared to clear days."│  └─────────────────────────────────────────────────────┘    │

│                                                             │

Calculation: Compare `sad` proportion in `rain` group vs `clear` group. Only show if the difference is statistically meaningful (> 5 percentage points).│  ┌─────────────────────────────────────────────────────┐    │

│  │  Average Mood by Weather Category                    │    │

### 6.6 TypeScript Interface│  │                                                      │    │

│  │  Clear       ████████████████████  0.62              │    │

```typescript│  │  Cloudy      ██████████████████    0.56              │    │

interface WeatherCorrelationResponse {│  │  Rain        ████████████          0.48              │    │

  period: "7d" | "30d" | "6m" | "all";│  │  Snow        ██████████            0.44              │    │

  data: {│  │  Thunderstorm████████              0.38              │    │

    weather_group: string;│  └─────────────────────────────────────────────────────┘    │

    day_count: number;│                                                             │

    total_listens: number;└─────────────────────────────────────────────────────────────┘

    mood_distribution: {```

      [mood_label: string]: number;

    };### 6.2 Chart Specifications

  }[];

}#### Scatter Plot: Mood vs Temperature

```

- **Chart type:** Recharts `ScatterChart`.

---- **X-axis:** Temperature (°C) from `daily_data`.

- **Y-axis:** Average valence (0–1) from `daily_data`.

## 7. Acceptance Criteria- **Point color:** Coded by `weather_category` (e.g., Clear = yellow, Rain = blue, Snow = white, etc.).

- **Point size:** Proportional to `total_listens` on that day (larger dot = more listens = more confidence in the average).

| Criteria | Verification |- **Tooltip:** On hover, show date, weather description, temperature, valence, and listen count.

| --- | --- |

| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |#### Bar Chart: Average Mood by Weather Category

| Weather codes are correctly grouped | Spot-check: verify WMO code 63 (moderate rain) → `rain` group |

| Period filter correctly scopes data | Compare data for `7d` vs `all` |- **Chart type:** Recharts `BarChart` (horizontal).

| `mood_distribution` values sum to `total_listens` for each weather group | Verify per group |- **X-axis:** Average valence (0–1).

| Stacked bar chart renders correctly with correct proportions | Visual inspection |- **Y-axis:** Weather category labels.

| Percentage mode toggle works (client-side) | Toggle and verify bars normalize to 100% |- **Bar label:** Valence value displayed at the end of each bar.

| Tooltip shows correct weather group, mood, count, and percentage | Hover and verify |- **Bar color:** Same color scheme as scatter plot dots for consistency.

| Weather groups with 0 days are excluded | Verify by choosing a short period where some weather groups won't appear |

| Period selector re-fetches and re-renders | Click each period button |### 6.3 Components

| Loading and error states work | Throttle network / kill API and verify |

| Component | Library | Details |
| --- | --- | --- |
| `PeriodSelector` | Native React | Same reusable component |
| `MoodWeatherScatter` | Recharts (`ScatterChart`) | Daily scatter: temp vs valence, colored by weather |
| `MoodByCategoryBar` | Recharts (`BarChart`) | Horizontal bar chart of avg valence per weather category |

### 6.4 TypeScript Interface

```typescript
interface WeatherCorrelationResponse {
  period: "7d" | "30d" | "6m" | "all";
  daily_data: {
    date: string; // YYYY-MM-DD
    day_of_week: string;
    is_weekend: boolean;
    avg_valence: number;
    total_listens: number;
    temp_c: number;
    precipitation: number;
    weather_code: number;
    weather_description: string;
  }[];
  summary_by_weather: {
    weather_category: string;
    avg_valence: number;
    avg_temp_c: number;
    total_days: number;
    total_listens: number;
  }[];
}
```

---

## 7. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns `daily_data` only for dates where both listening and weather data exist | Check that no rows have null valence or null weather fields |
| `weather_description` maps correctly from WMO codes | Verify a sample of codes against the WMO table |
| `summary_by_weather` groups are mutually exclusive and cover all weather codes | Every `weather_code` in `daily_data` maps to exactly one category in `summary_by_weather` |
| Average valence in `summary_by_weather` is listen-weighted | Manually compute for one category and compare |
| Period filter scopes both `daily_data` and `summary_by_weather` | Change period and verify data changes |
| Scatter plot renders with correctly colored/sized dots | Visual inspection |
| Bar chart shows categories ordered by valence or alphabetically | Visual inspection |
| Tooltip on scatter plot shows all expected fields | Hover and verify |
