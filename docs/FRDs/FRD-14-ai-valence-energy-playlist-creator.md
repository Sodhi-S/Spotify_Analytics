# FRD 14: AI Valence/Energy Playlist Creator

## Page Placement

This feature should live on the **Create** page.

The Create page is the right place because this is an action-oriented workflow: the user chooses a desired musical mood profile, the system generates a curated playlist, and the user can optionally export/save it.

## 1. Feasibility Summary

This feature is feasible with the current stack, with one important boundary:

- **Feasible now:** generate an in-app curated playlist preview from the user's Last.fm listening history plus local `valence` and `energy` scores from Music2Emo.
- **Feasible with OpenRouter:** use an LLM to produce playlist names, descriptions, and short human-readable explanations for why each track fits.
- **Not possible with Last.fm alone:** saving a real playlist into Spotify requires Spotify OAuth and Spotify playlist write scopes.
- **Recommended MVP:** generate and display the playlist inside the app first; add Spotify export after a dedicated Spotify connection flow exists.

Last.fm can provide listening history, top tracks, top artists, tags, and similar-track candidates. It cannot create Spotify playlists. Spotify playlist creation requires Spotify Web API authorization for the current Spotify user.

## 2. Feature Overview

The AI Valence/Energy Playlist Creator lets a user generate a playlist based on the emotional and intensity profile they want.

Users can choose:

- Target valence: darker to brighter
- Target energy: calmer to more intense
- Playlist length
- Familiarity preference: mostly known tracks vs more discovery
- Optional prompt, such as "gym but not too aggressive" or "late-night hopeful"

The system should recommend tracks using the user's listening history and enriched track features. It should then use OpenRouter to create an appealing playlist title, description, and concise rationale.

## 3. User Goal

Users should be able to:

- Generate a playlist for a target mood without manually searching through their library.
- Choose high-energy, low-energy, high-valence, low-valence, or mixed mood profiles.
- Understand why each track was recommended.
- Regenerate the playlist when the first result does not feel right.
- Remove unwanted tracks before export.
- Save or export the playlist to Spotify once Spotify permissions are connected.

## 4. Data Inputs

### Existing App Data

- `fact_listens.user_id`
- `fact_listens.listen_id`
- `fact_listens.played_at`
- `dim_tracks.track_id`
- `dim_tracks.name`
- `dim_tracks.artist_name`
- `dim_tracks.album`
- `dim_tracks.album_image_url`
- `dim_tracks.top_tags`
- `dim_tracks.valence`
- `dim_tracks.energy`
- `dim_tracks.mood_label`
- `dim_artists.artist_id`
- `dim_artists.name`
- `mart_tag_listen_counts`

### Last.fm API Data

Useful Last.fm methods:

- `user.getTopTracks` for high-confidence personal favorites.
- `user.getRecentTracks` for recency-aware candidate weighting.
- `track.getSimilar` for discovery candidates related to seed tracks.
- `artist.getSimilar`, optional for artist-level expansion.
- `track.getTopTags` and `artist.getTopTags` for genre/style context.

### OpenRouter Inputs

The OpenRouter prompt should receive only structured playlist candidates and user preferences, not raw private session cookies or secrets.

Recommended LLM input:

```json
{
  "target_valence": 0.75,
  "target_energy": 0.65,
  "playlist_length": 25,
  "user_prompt": "warm evening walk",
  "candidate_tracks": [
    {
      "track_id": "...",
      "name": "...",
      "artist_name": "...",
      "valence": 0.72,
      "energy": 0.61,
      "top_tags": ["indie", "dream pop"],
      "play_count": 14,
      "last_played_at": "2026-06-01"
    }
  ]
}
```

### Spotify Inputs, Optional Export Phase

To save a real Spotify playlist, the app must add:

- Spotify OAuth connection per app user.
- Spotify access and refresh token storage.
- Spotify track URI matching for each recommended track.
- Playlist write scopes.

## 5. Functional Requirements

- The system shall allow the user to select target valence from `0.0` to `1.0`.
- The system shall allow the user to select target energy from `0.0` to `1.0`.
- The system shall allow the user to choose playlist length, initially 10, 25, or 50 tracks.
- The system shall allow optional text guidance.
- The system shall generate candidate tracks only from rows owned by the current app user.
- The system shall exclude tracks where both `valence` and `energy` are null.
- The system shall rank tracks by closeness to the target valence/energy profile.
- The system shall consider play count, recency, artist diversity, and tag similarity.
- The system shall avoid returning too many tracks by the same artist unless explicitly requested.
- The system shall show a generated playlist name.
- The system shall show a generated playlist description.
- The system shall show track-level reasons.
- The system shall allow the user to regenerate.
- The system shall allow the user to remove tracks from the preview.
- The system shall allow Spotify export only after Spotify is connected.
- The system shall gracefully fall back to deterministic names/reasons if OpenRouter is unavailable.

## 6. Recommendation Logic

The deterministic recommender should produce the candidate list before the LLM is called.

### Candidate Sources

MVP candidates:

- User's previously listened tracks with `valence` and `energy`.
- User's top tracks for familiarity.
- Recent tracks for current taste.

V2 candidates:

- Last.fm `track.getSimilar` results from seed tracks.
- Matched Spotify tracks, if Spotify catalog search is enabled.
- Discovery tracks that the user has not listened to before.

### Scoring

Recommended MVP score:

```text
mood_distance = sqrt(
  (track.valence - target_valence)^2 +
  (track.energy - target_energy)^2
)

base_score = 1 - mood_distance

final_score =
  base_score * 0.60 +
  familiarity_score * 0.20 +
  recency_score * 0.10 +
  tag_match_score * 0.10
```

The scoring weights should be configurable later, but hard-coded defaults are acceptable for the MVP.

### Mood Quadrants

The UI should expose quick presets:

| Preset | Valence | Energy | Meaning |
|---|---:|---:|---|
| Happy / Hype | High | High | Bright, active, upbeat |
| Calm / Peaceful | High | Low | Warm, gentle, relaxed |
| Angry / Intense | Low | High | Dark, aggressive, activated |
| Sad / Gloomy | Low | Low | Reflective, downcast, quiet |
| Custom | User-selected | User-selected | Manual slider settings |

## 7. OpenRouter Usage

OpenRouter should enhance the playlist, not be the sole ranking engine.

The backend should call OpenRouter after deterministic candidate selection to generate:

- Playlist title
- Playlist description
- One-line explanation per track
- Optional short callout, such as "This leans bright but not frantic."

The prompt should require strict JSON output:

```json
{
  "title": "Warm Evening Voltage",
  "description": "A bright, moderately energetic mix built from your recent indie and pop listening.",
  "tracks": [
    {
      "track_id": "...",
      "reason": "Close to your requested bright, mid-energy target and one of your recurring evening listens."
    }
  ]
}
```

The backend must validate the JSON and ignore any LLM-proposed track that was not in the deterministic candidate set.

## 8. API Requirements

### Generate Playlist

```http
POST /api/create/playlists
```

Request:

```ts
{
  target_valence: number;
  target_energy: number;
  length: number;
  prompt?: string;
  familiarity: "balanced" | "familiar" | "discovery";
}
```

Response:

```ts
{
  generation_id: string;
  title: string;
  description: string;
  target_valence: number;
  target_energy: number;
  tracks: {
    track_id: string;
    name: string;
    artist_name: string;
    album: string | null;
    album_image_url: string | null;
    valence: number | null;
    energy: number | null;
    mood_label: string | null;
    score: number;
    reason: string;
    spotify_uri?: string | null;
  }[];
  can_export_to_spotify: boolean;
}
```

### Export To Spotify, Future

```http
POST /api/create/playlists/{generation_id}/export/spotify
```

This endpoint should require:

- Authenticated app session.
- Connected Spotify account.
- Valid Spotify access token.
- Playlist write scope.

## 9. Data Model Requirements

Recommended tables:

```sql
create table app.playlist_generations (
    id text primary key,
    user_id text not null references app.users(id) on delete cascade,
    title text not null,
    description text,
    target_valence numeric,
    target_energy numeric,
    prompt text,
    length integer not null,
    familiarity text not null,
    provider text,
    model text,
    created_at timestamptz not null default current_timestamp
);

create table app.playlist_generation_tracks (
    generation_id text not null references app.playlist_generations(id) on delete cascade,
    position integer not null,
    track_id text not null,
    score numeric not null,
    reason text,
    spotify_uri text,
    primary key (generation_id, position)
);
```

Optional Spotify connection table:

```sql
create table app.spotify_connections (
    user_id text primary key references app.users(id) on delete cascade,
    spotify_user_id text not null,
    access_token_encrypted text not null,
    refresh_token_encrypted text not null,
    scopes text not null,
    expires_at timestamptz not null,
    connected_at timestamptz not null default current_timestamp
);
```

## 10. UI Requirements

The Create page should include:

- Preset mood buttons.
- Valence slider.
- Energy slider.
- Playlist length selector.
- Familiarity selector.
- Optional prompt field.
- AI-styled "Create with AI" button.
- Loading state while generation runs.
- Playlist preview with album art.
- Track reason text.
- Remove-track action.
- Regenerate action.
- Export to Spotify button, disabled until Spotify is connected.
- Spotify connection prompt when export is unavailable.

## 11. Security and Privacy Requirements

- The backend must derive `user_id` from the app session, never from the client request body.
- Playlist candidates must be filtered to `current_user.id`.
- OpenRouter requests must not include session cookies, auth tokens, Last.fm session keys, Spotify tokens, or app password hashes.
- Spotify tokens must be encrypted at rest if Spotify export is implemented.
- LLM output must be treated as untrusted text and validated before storage/display.
- Rate limits should be added for playlist generation to control LLM cost.

## 12. Implementation Phases

### Phase 1: In-App Playlist Preview

- Build deterministic recommender from existing `dim_tracks`, `fact_listens`, and `dim_artists`.
- Add Create page controls.
- Generate playlist preview without OpenRouter.
- Store playlist generations.

### Phase 2: OpenRouter Enhancement

- Add `OPENROUTER_API_KEY`.
- Add backend OpenRouter client.
- Generate title, description, and reasons.
- Add deterministic fallback.

### Phase 3: Last.fm Discovery Expansion

- Use `track.getSimilar` for discovery candidates.
- Match returned tracks back to app metadata where possible.
- Keep unmatched discovery candidates visible but not exportable until matched.

### Phase 4: Spotify Export

- Add Spotify OAuth.
- Store encrypted Spotify refresh tokens.
- Match app tracks to Spotify URIs via Spotify Search.
- Create playlist via Spotify API.
- Add tracks in batches.

## 13. Acceptance Criteria

This feature is complete for MVP when:

- A logged-in user can open the Create page.
- A logged-in user can choose target valence and energy.
- The backend returns a ranked playlist preview using only the current user's data.
- Tracks without valence/energy are excluded or clearly marked.
- The UI shows playlist name, description, album art, tracks, and reasons.
- The same request does not leak another user's tracks.
- The feature works without Spotify connection.
- Spotify export is clearly marked unavailable until Spotify OAuth is implemented.

## 14. Open Questions

- Should the MVP use only previously listened tracks, or include Last.fm similar-track discovery immediately?
- Should valence/energy be generated for more tracks before launch to improve coverage?
- Should OpenRouter be allowed to reorder deterministic results, or only write names/reasons?
- Should playlist generations be permanent history or temporary previews?
- Should Spotify export create private playlists by default?

## 15. Source Notes

- Last.fm `user.getTopTracks` can fetch a user's top tracks by period and does not require authentication.
- Last.fm `track.getSimilar` can fetch similar tracks based on Last.fm listening data and does not require authentication.
- Spotify playlist creation requires OAuth and playlist modification scopes.
- Spotify track search can map artist/title candidates to Spotify track objects and URIs.
- OpenRouter exposes an OpenAI-style chat completion endpoint at `/api/v1/chat/completions`.
