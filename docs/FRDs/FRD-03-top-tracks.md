# FRD-003: Top Tracks# FRD-003: Top Tracks



## `/api/top-tracks` Endpoint + Top Tracks Display## `/api/top-tracks` Endpoint



**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)**Parent PRD:** [Spotify Listening Intelligence Platform — PRD v0.2](../PRD/prd.md)

**PRD Requirements:** P5-2**PRD Requirements:** P5-2

**Author:** Sahej Singh Sodhi**Author:** Sahej Singh Sodhi

**Created:** March 2, 2026**Created:** March 2, 2026

**Updated:** March 3, 2026**Status:** Draft

**Status:** Draft

---

---

## 1. Purpose

## 1. Purpose

This FRD specifies the Top Tracks endpoint, which returns the most-played tracks over a configurable time period. This data is consumed by the Overview Dashboard (top 5 tracks card) and can also support a dedicated top tracks page if desired.

This FRD specifies the Top Tracks endpoint and how top track data is displayed on the frontend. Top tracks are sourced from the Last.fm `user.getTopTracks` API and enriched with mood classification labels and community tags from the dbt star schema.

---

---

## 2. Scope

## 2. Scope

| In Scope | Out of Scope |

| In Scope | Out of Scope || --- | --- |

| --- | --- || `GET /api/top-tracks` endpoint | Frontend view (consumed by Overview Dashboard, see FRD-002) |

| `GET /api/top-tracks` endpoint | Data ingestion (see FRD-001) || Time period filtering | Data ingestion / transformation (see FRD-001) |

| Top tracks list display in frontend | Overview, heatmap, mood trends, weather views (see other FRDs) || Configurable result count | |

| Enrichment with `mood_label` and `top_tags` | |

---

---

## 3. Data Dependencies

## 3. Data Dependencies

| Table | Used For |

| Table | Used For || --- | --- |

| --- | --- || `fact_listens` | Counting plays per track within the period |

| `raw.top_tracks` | Source of ranked top tracks per period (from Last.fm `user.getTopTracks`) || `dim_tracks` | Track name, album, audio features |

| `dim_tracks` | Join for `mood_label`, `mood_confidence`, `top_tags` || `dim_artists` | Artist name (via `fact_listens.artist_id`, `is_current = TRUE`) |

| `fact_listens` | Fallback for custom period calculations (if needed) |

---

---

## 4. API Specification

## 4. API Specification

### `GET /api/top-tracks`

### `GET /api/top-tracks`

#### Request

#### Request

| Parameter | Type | Required | Default | Description |

| Parameter | Type | Required | Default | Description || --- | --- | --- | --- | --- |

| --- | --- | --- | --- | --- || `period` | query string | No | `all` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |

| `period` | query string | No | `7day` | Time period filter. See accepted values below. || `limit` | query integer | No | `10` | Number of tracks to return. Min: 1, Max: 50. |

| `limit` | query integer | No | `10` | Number of tracks to return. Max: `50`. |

**Period definitions:**

**Period values — Last.fm native periods:**

| Value | Meaning |

| Value | Last.fm `period` Parameter | Meaning || --- | --- |

| --- | --- | --- || `7d` | Last 7 calendar days (including today) |

| `7day` | `7day` | Last 7 days || `30d` | Last 30 calendar days (including today) |

| `1month` | `1month` | Last 1 month || `6m` | Last 6 calendar months (180 days from today) |

| `3month` | `3month` | Last 3 months || `all` | All data in the warehouse |

| `6month` | `6month` | Last 6 months |

| `12month` | `12month` | Last 12 months |#### Response



**Note:** These period values come from Last.fm's native `user.getTopTracks` API parameter. They differ from the `7d` / `30d` / `6m` / `all` periods used in other endpoints because the top tracks data is fetched pre-ranked from Last.fm with these specific period strings.```json

{

#### Response  "period": "30d",

  "limit": 10,

```json  "tracks": [

{    {

  "period": "7day",      "rank": 1,

  "limit": 10,      "track_id": "abc123",

  "tracks": [      "name": "Track Name",

    {      "artist_name": "Artist Name",

      "rank": 1,      "album": "Album Name",

      "track_name": "Track Name",      "play_count": 42,

      "artist_name": "Artist Name",      "total_ms_played": 176400000,

      "play_count": 42,      "audio_features": {

      "mood_label": "happy",        "energy": 0.78,

      "mood_confidence": 0.87,        "valence": 0.65,

      "top_tags": ["indie rock", "dream pop", "shoegaze"]        "danceability": 0.82,

    },        "tempo": 124.5,

    {        "acousticness": 0.12,

      "rank": 2,        "speechiness": 0.05,

      "track_name": "Another Track",        "instrumentalness": 0.01

      "artist_name": "Another Artist",      }

      "play_count": 38,    }

      "mood_label": null,  ]

      "mood_confidence": null,}

      "top_tags": ["hip hop", "trap"]```

    }

  ]#### Query Logic

}

``````sql

SELECT

#### Field Details  t.track_id,

  t.name,

| Field | Source | Logic |  a.name AS artist_name,

| --- | --- | --- |  t.album,

| `rank` | `raw.top_tracks.rank` | Rank from Last.fm (pre-ranked by Last.fm) |  COUNT(*) AS play_count,

| `track_name` | `raw.top_tracks.track_name` | From Last.fm |  SUM(f.ms_played) AS total_ms_played,

| `artist_name` | `raw.top_tracks.artist_name` | From Last.fm |  t.energy, t.valence, t.danceability, t.tempo,

| `play_count` | `raw.top_tracks.play_count` | From Last.fm (user's play count for this track in the period) |  t.acousticness, t.speechiness, t.instrumentalness

| `mood_label` | `dim_tracks.mood_label` | Joined by `(track_name, artist_name)` match. `NULL` if unclassified. |FROM fact_listens f

| `mood_confidence` | `dim_tracks.mood_confidence` | Joined by `(track_name, artist_name)` match. `NULL` if unclassified. |JOIN dim_tracks t ON f.track_id = t.track_id

| `top_tags` | `dim_tracks.top_tags` | Community tags from Last.fm `track.getTopTags`. Array of tag name strings. |JOIN dim_artists a ON f.artist_id = a.artist_id AND a.is_current = TRUE

WHERE f.date_id >= :start_date  -- computed from period

#### Join LogicGROUP BY t.track_id, t.name, a.name, t.album,

         t.energy, t.valence, t.danceability, t.tempo,

Top tracks from `raw.top_tracks` are joined to `dim_tracks` on a composite match of `(track_name, artist_name)` (case-insensitive). If no match is found in `dim_tracks`, `mood_label`, `mood_confidence`, and `top_tags` are returned as `null` / `[]`.         t.acousticness, t.speechiness, t.instrumentalness

ORDER BY play_count DESC

#### Error ResponsesLIMIT :limit

```

| Status | Condition | Body |

| --- | --- | --- |#### Error Responses

| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7day, 1month, 3month, 6month, 12month"}` |

| 400 | `limit` < 1 or > 50 | `{"detail": "Limit must be between 1 and 50"}` || Status | Condition | Body |

| 500 | Database error | `{"detail": "Internal server error"}` || --- | --- | --- |

| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |

---| 400 | `limit` out of range | `{"detail": "Limit must be between 1 and 50"}` |

| 500 | Database error | `{"detail": "Internal server error"}` |

## 5. Frontend Display

---

### 5.1 Layout

## 5. TypeScript Interface

The top tracks list is displayed as a ranked table/list, either as a standalone page section or as an expanded view accessible from the Overview Dashboard.

```typescript

```interface TopTracksResponse {

┌──────────────────────────────────────────────────────────────┐  period: "7d" | "30d" | "6m" | "all";

│  Top Tracks                                                  │  limit: number;

│  Period: [7 days] [1 month] [3 months] [6 months] [12 months]│  tracks: {

├──────────────────────────────────────────────────────────────┤    rank: number;

│  #   Track                Artist           Plays  Mood       │    track_id: string;

│  1   Track Name           Artist Name      42     😊 happy   │    name: string;

│  2   Another Track        Another Artist   38     —          │    artist_name: string;

│  3   Third Track          Third Artist     35     😢 sad     │    album: string;

│  ...                                                         │    play_count: number;

└──────────────────────────────────────────────────────────────┘    total_ms_played: number;

```    audio_features: {

      energy: number;

### 5.2 Components      valence: number;

      danceability: number;

| Component | Library | Props / Data |      tempo: number;

| --- | --- | --- |      acousticness: number;

| `PeriodSelector` | Native React | Emits Last.fm period value (`7day`, `1month`, `3month`, `6month`, `12month`) |      speechiness: number;

| `TopTrackRow` | Native React | `rank`, `trackName`, `artistName`, `playCount`, `moodLabel`, `topTags` |      instrumentalness: number;

    };

### 5.3 Mood Label Display  }[];

}

- If `mood_label` is not null, display a mood emoji + label text (e.g., "😊 happy", "😢 sad").```

- If `mood_label` is null, display a dash `—` or "Unclassified" in muted text.

- Color-code the mood label using the same palette as the Mood Donut Chart (FRD-002).---



### 5.4 Tags Display## 6. Acceptance Criteria



- Show tags as small pill/badge elements below the track row or on hover/expand.| Criteria | Verification |

- Max 3 tags displayed, with a "+N more" indicator if there are more.| --- | --- |

| Endpoint returns tracks ordered by `play_count` descending | Verify ordering in response |

### 5.5 TypeScript Interface| Period filter correctly scopes play counts | Compare `7d` vs `all` — counts for `7d` ≤ counts for `all` |

| `limit` parameter controls result count | Request `limit=3` and verify exactly 3 tracks returned |

```typescript| Invalid `period` or `limit` returns 400 | Send bad params and verify error response |

interface TopTracksResponse {| `rank` field is sequential starting from 1 | Inspect response |

  period: "7day" | "1month" | "3month" | "6month" | "12month";| Audio features are included for each track | Verify non-null values in `audio_features` object |

  limit: number;
  tracks: {
    rank: number;
    track_name: string;
    artist_name: string;
    play_count: number;
    mood_label: string | null;
    mood_confidence: number | null;
    top_tags: string[];
  }[];
}
```

---

## 6. Acceptance Criteria

| Criteria | Verification |
| --- | --- |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| Period parameter filters correctly using Last.fm native period values | Compare results across periods |
| `limit` parameter works (default 10, max 50) | Request with `limit=5` returns 5, `limit=51` returns 400 |
| Mood label and tags are correctly joined from `dim_tracks` | Spot-check a few tracks against the database |
| Tracks with no mood classification return `null` for `mood_label` and `mood_confidence` | Find a known unclassified track and verify |
| Rank ordering matches Last.fm ranking | Compare with Last.fm profile page |
| Frontend period selector re-fetches data | Click each period button and verify |
| Mood labels are color-coded and display correctly on frontend | Visual inspection |
