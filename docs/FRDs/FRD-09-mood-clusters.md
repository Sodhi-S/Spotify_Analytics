# FRD-009: Mood Clusters (Nice to Have)

## `/api/moods/clusters` Endpoint + Mood Cluster Scatter Plot

**Parent PRD:** [Music Listening Intelligence Platform — PRD v0.3](../PRD/prd.md)
**PRD Requirements:** P5-8 (Nice to Have), P6-2 (Nice to Have)
**Author:** Sahej Singh Sodhi
**Created:** March 3, 2026
**Status:** Draft — Nice to Have

---

## 1. Purpose

This FRD specifies the Mood Clusters feature: the FastAPI endpoint that serves mood cluster data for a scatter plot visualization. This is a **Nice to Have** feature — it is deprioritized relative to all Must-have features and depends on the resolution of **Open Question OQ1** (mood-to-numeric proxy scores).

---

## 2. Dependency on OQ1

### The Problem

The current data model has:
- `mood_label` — categorical (e.g., "happy", "sad", "calm")
- `mood_confidence` — a single float (0–1)

A scatter plot requires **at least two numeric dimensions** for the X and Y axes. With only `mood_confidence` as a numeric value, there is no meaningful second axis.

### OQ1: Mood-to-Numeric Proxy Scores

OQ1 proposes adding static mappings from `mood_label` to numeric proxy scores:

```python
mood_to_energy = {
    "happy":  0.8,
    "angry":  0.9,
    "calm":   0.3,
    "sad":    0.2,
    "energetic": 0.95,
    "melancholic": 0.25,
}

mood_to_valence = {
    "happy":  0.9,
    "angry":  0.3,
    "calm":   0.7,
    "sad":    0.1,
    "energetic": 0.7,
    "melancholic": 0.15,
}
```

This would add `mood_energy` (FLOAT) and `mood_valence` (FLOAT) columns to `dim_tracks`, providing two numeric axes for the scatter plot.

### Decision Timeline

OQ1 is deferred until Phase 3 when real mood classification data is available. The decision depends on:
1. Whether the mood label distribution is rich and well-distributed enough to make numeric proxies meaningful.
2. Whether the static mapping oversimplifies the model's output.

**If OQ1 is resolved YES:** This FRD is fully implementable as specified below.

**If OQ1 is resolved NO:** This feature is dropped, or reimagined as a non-scatter visualization (e.g., a grouped bar chart of tracks per mood class, which doesn't require numeric axes).

---

## 3. Scope (Contingent on OQ1 = YES)

| In Scope | Out of Scope |
| --- | --- |
| `GET /api/moods/clusters` endpoint | Actual K-Means clustering (see Section 4.2) |
| Scatter plot visualization | Data ingestion, mood classification (see FRD-001) |
| Period filtering | |

---

## 4. Design Decisions

### 4.1 Clustering Approach

The PRD originally mentioned K-Means clustering but later deprioritized it. Two approaches are possible:

**Approach A: No Clustering — Raw Scatter**

Plot each track as a point on the scatter plot using `mood_energy` (X) and `mood_valence` (Y), colored by `mood_label`. The "clusters" are the natural groupings formed by the mood label mapping. No K-Means needed.

**Approach B: K-Means Clustering**

Run K-Means on `(mood_energy, mood_valence)` and assign each track a cluster ID. This provides tighter cluster boundaries but adds complexity.

**Recommended:** Approach A (no clustering). The `mood_label` itself acts as the cluster label. K-Means would just re-derive groups that already exist from the label mapping.

### 4.2 Why K-Means Is Not Needed

Since `mood_energy` and `mood_valence` are both derived from `mood_label` via a static mapping, all tracks with the same `mood_label` will have the same `(energy, valence)` point. K-Means would produce clusters identical to the existing mood labels.

To make the scatter plot visually interesting despite identical coordinates per label, add **jitter** (small random offsets) to the plotted positions so points don't stack exactly on top of each other.

---

## 5. API Specification (Contingent on OQ1 = YES)

### `GET /api/moods/clusters`

#### Request

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `period` | query string | No | `all` | Time period filter. Accepted values: `7d`, `30d`, `6m`, `all`. |
| `limit` | query integer | No | `200` | Max number of tracks to return. Max: `500`. |

#### Response

```json
{
  "period": "all",
  "tracks": [
    {
      "track_id": "abc123",
      "track_name": "Track Name",
      "artist_name": "Artist Name",
      "mood_label": "happy",
      "mood_confidence": 0.87,
      "mood_energy": 0.8,
      "mood_valence": 0.9
    },
    {
      "track_id": "def456",
      "track_name": "Another Track",
      "artist_name": "Another Artist",
      "mood_label": "sad",
      "mood_confidence": 0.72,
      "mood_energy": 0.2,
      "mood_valence": 0.1
    }
  ]
}
```

#### Field Details

| Field | Source | Logic |
| --- | --- | --- |
| `track_id` | `dim_tracks.track_id` | |
| `track_name` | `dim_tracks.name` | |
| `artist_name` | `dim_artists.name` (WHERE `is_current = TRUE`) | |
| `mood_label` | `dim_tracks.mood_label` | Exclude tracks where `mood_label IS NULL` |
| `mood_confidence` | `dim_tracks.mood_confidence` | |
| `mood_energy` | `dim_tracks.mood_energy` | Derived from `mood_label` via static mapping (OQ1) |
| `mood_valence` | `dim_tracks.mood_valence` | Derived from `mood_label` via static mapping (OQ1) |

**Track selection:** Return tracks that the user actually listened to in the requested period (i.e., tracks that appear in `fact_listens` within the date range), not all tracks in `dim_tracks`. Deduplicate — each track appears once, regardless of how many times it was listened to. Order by play count descending and apply `limit`.

#### Error Responses

| Status | Condition | Body |
| --- | --- | --- |
| 400 | Invalid `period` value | `{"detail": "Invalid period. Accepted values: 7d, 30d, 6m, all"}` |
| 400 | `limit` < 1 or > 500 | `{"detail": "Limit must be between 1 and 500"}` |
| 500 | Database error | `{"detail": "Internal server error"}` |

---

## 6. Frontend View — Mood Cluster Scatter Plot (Contingent on OQ1 = YES)

### 6.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Mood Clusters                                               │
│  Period: [7d] [30d] [6m] [All Time]                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Valence ▲                                             │  │
│  │          │     ● ●                                     │  │
│  │          │   ●  ● ●            ●  ●                    │  │
│  │          │    ●                  ●  ●  ●               │  │
│  │          │                                             │  │
│  │          │                                             │  │
│  │          │        ● ●                                  │  │
│  │          │      ●  ● ●         ●  ●                    │  │
│  │          │                      ●                      │  │
│  │          └──────────────────────────────► Energy        │  │
│  │                                                        │  │
│  │  ● Happy  ● Sad  ● Angry  ● Calm  ● Energetic         │  │
│  │  ● Melancholic                                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Chart Specification

- **Chart type:** Recharts `ScatterChart` with one `Scatter` component per mood label.
- **X-axis:** `mood_energy` (0–1) — labeled "Energy".
- **Y-axis:** `mood_valence` (0–1) — labeled "Valence".
- **Points:** One per track. Colored by `mood_label` using the standard mood palette.
- **Jitter:** Apply ±0.05 random offset to both X and Y coordinates to prevent points from stacking (since all tracks with the same `mood_label` have the same base coordinates).
- **Point size:** Optionally scale by `mood_confidence` (higher confidence = larger dot). Or keep uniform size for simplicity.
- **Colors:** Same palette as other mood visualizations (FRD-002, FRD-004, FRD-006).

### 6.3 Interaction

- **Hover tooltip:** Show track name, artist name, mood label, mood confidence.
- **Legend:** Toggles visibility of mood classes.
- **Period selector:** Re-fetches data and re-renders.

### 6.4 TypeScript Interface

```typescript
interface MoodClustersResponse {
  period: "7d" | "30d" | "6m" | "all";
  tracks: {
    track_id: string;
    track_name: string;
    artist_name: string;
    mood_label: string;
    mood_confidence: number;
    mood_energy: number;
    mood_valence: number;
  }[];
}
```

---

## 7. Fallback if OQ1 = NO

If OQ1 is resolved NO (no numeric proxy scores), this feature can be reimagined as:

### Alternative: Mood Distribution Bar Chart

- Group tracks by `mood_label`.
- Display a bar chart where X = mood label, Y = track count (or listen count).
- Each bar can be segmented by `mood_confidence` buckets (e.g., low < 0.5, medium 0.5–0.8, high > 0.8).
- This requires no numeric axes and works with the existing data model.

This alternative would use a different endpoint response shape and is not specified further here. If OQ1 is resolved NO, this FRD should be updated or replaced.

---

## 8. Acceptance Criteria (Contingent on OQ1 = YES)

| Criteria | Verification |
| --- | --- |
| OQ1 resolved YES before implementation begins | PRD updated with decision |
| `mood_energy` and `mood_valence` columns exist in `dim_tracks` | Database inspection |
| Endpoint returns valid JSON matching the response schema | Automated API test or manual curl |
| Only tracks with non-NULL `mood_label` are included | Verify no null mood labels in response |
| Tracks are scoped to the requested period | Verify tracks appear in `fact_listens` within the date range |
| `limit` parameter works (default 200, max 500) | Request with `limit=10` returns 10 |
| Scatter plot renders with visible clusters (with jitter) | Visual inspection |
| Tooltip shows track name, artist, mood, confidence | Hover and verify |
| Legend toggles mood class visibility | Click legend items |
| Deduplication works — each track appears once | Verify no duplicate `track_id` in response |
