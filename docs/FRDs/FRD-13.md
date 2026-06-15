# FRD 13: Album Covers and Artist Images

## Page Placement

This feature should improve the existing **Overview**, **Top Tracks**, **Moods**, and future weather/music insight surfaces.

The feature should not create a new page. It should enrich existing music cards, tables, lists, and charts with album artwork and artist imagery so the app feels more visual, personal, and recognizable.

## 1. Feature Overview

Album Covers and Artist Images add visual identity to tracks and artists throughout the app.

The app currently shows listening analytics using text, counts, charts, mood labels, and generated placeholders. This feature should replace placeholders with real album covers and artist images when available, while keeping graceful fallbacks when images are missing.

The goal is to make the app feel more like a music intelligence product, not only a data dashboard.

## 2. User Goal

Users should be able to:

- Recognize tracks faster by album cover.
- Recognize artists faster by artist image.
- Browse top tracks and mood fingerprints with richer visual context.
- Trust that missing images will not break the UI.
- See a consistent visual language across Overview, Top Tracks, Moods, and Weather-related artist sections.

## 3. Data Inputs

The feature should use:

- Track name
- Artist name
- Album name, if available
- Existing track IDs
- Existing artist IDs
- iTunes/Apple Music lookup results
- Last.fm artist metadata, if available
- Existing `dim_tracks` and `dim_artists` records

Optional future inputs:

- Spotify track IDs
- Spotify album image URLs
- Spotify artist image URLs
- MusicBrainz IDs
- Cover Art Archive URLs

## 4. Data Model Requirements

The system should store image metadata in existing mart tables or a dedicated enrichment table.

Recommended track fields:

```sql
album_image_url
album_image_source
album_image_width
album_image_height
album_image_updated_at
```

Recommended artist fields:

```sql
image_url
image_source
image_width
image_height
image_updated_at
```

The system should store image URLs and metadata, not image files, for the MVP.

## 5. Functional Requirements

- The system shall identify tracks missing album artwork.
- The system shall identify artists missing artist images.
- The system shall enrich track records with album image URLs.
- The system shall enrich artist records with artist image URLs.
- The system shall store the source of each image.
- The system shall avoid repeated API calls for records that already have valid image data.
- The system shall support a backfill job for missing images.
- The system shall support incremental enrichment for newly ingested tracks and artists.
- The frontend shall display album covers for tracks when available.
- The frontend shall display artist images for artists when available.
- The frontend shall use existing placeholder artwork when no image is available.
- The frontend shall handle broken image URLs without showing broken image icons.

## 6. Image Source Priority

The MVP should use sources already aligned with the project.

Recommended track image source order:

| Priority | Source | Use Case |
|---:|---|---|
| 1 | iTunes / Apple Music lookup | Album covers for known track and artist pairs |
| 2 | Existing manual iTunes overrides | Tracks that need corrected Apple IDs |
| 3 | Spotify API, if permissions are added later | Album covers from Spotify track metadata |
| 4 | Placeholder | No reliable artwork found |

Recommended artist image source order:

| Priority | Source | Use Case |
|---:|---|---|
| 1 | Last.fm artist metadata | Artist images when available |
| 2 | Spotify API, if permissions are added later | Artist profile images |
| 3 | MusicBrainz / fanart source, if added later | Fallback artist image enrichment |
| 4 | Placeholder | No reliable artist image found |

## 7. Enrichment Job Requirements

The system should include an image enrichment job that can run manually or on a schedule.

The job should:

- Query tracks with missing `album_image_url`.
- Query artists with missing `image_url`.
- Look up images using available external metadata sources.
- Match results conservatively using track name, artist name, and album name.
- Save image URLs and source metadata.
- Skip records that already have image data unless a refresh flag is provided.
- Log unresolved tracks and artists for later review.
- Respect external API rate limits.

## 8. Matching Rules

The enrichment process should prefer precision over coverage.

For album covers:

- Exact or near-exact artist match should be required.
- Exact or near-exact track match should be preferred.
- Album name should be used when available.
- If multiple results match, prefer the result with matching artist and album.

For artist images:

- Exact or near-exact artist name match should be required.
- If multiple artists share a name, prefer the one with stronger metadata confidence.
- The system should avoid assigning images when the match is ambiguous.

## 9. API Requirements

Existing API responses should include image fields where relevant.

Top tracks should include:

```ts
{
  album_image_url: string | null;
}
```

Artist mood fingerprints should include:

```ts
{
  image_url: string | null;
}
```

Overview top tracks should include:

```ts
{
  album_image_url: string | null;
}
```

Overview top artists should include:

```ts
{
  image_url: string | null;
}
```

## 10. UI Requirements

### Overview Page

The Overview page should show:

- Album covers in the Top Tracks list.
- Artist images in the Top Artists list.
- Existing placeholder visuals when images are missing.

### Top Tracks Page

The Top Tracks page should show:

- Album cover thumbnail for each track.
- Track name and artist name beside the artwork.
- Placeholder artwork when no album image is available.

### Moods Page

The Moods page should show:

- Artist image in each Artist Mood Fingerprint card.
- Artist image in mood map tooltip, if practical.
- Existing generated avatar when no artist image is available.

### Weather Page

If artist context cards are shown in Weather-related sections, they should use artist images when available.

## 11. Fallback Requirements

The frontend must not show broken image icons.

If an image URL is missing or fails to load:

- Album cards should show the existing album placeholder.
- Artist cards should show the existing artist placeholder.
- The card layout should not shift.
- The fallback should preserve the app’s current visual style.

## 12. Privacy and Performance Requirements

- The app should store only public image URLs and metadata.
- The app should not store private user images.
- The frontend should use appropriately sized thumbnails where available.
- Large source images should not be loaded when a small thumbnail is sufficient.
- Image loading should not block core analytics data from rendering.
- Broken or slow images should degrade gracefully.

## 13. MVP Scope

The MVP should include:

- Track album cover enrichment using iTunes / Apple Music lookup.
- Artist image enrichment using the best available existing artist metadata source.
- Album covers in Top Tracks.
- Album covers in Overview Top Tracks.
- Artist images in Moods artist fingerprint cards.
- Placeholder fallback behavior.

The MVP does not need:

- Locally hosted image files.
- Image cropping tools.
- User-uploaded artwork.
- Full Spotify write/read permission expansion.
- Perfect image coverage for every track and artist.

## 14. Example User Experience

Example Top Tracks row:

```text
[Album cover] Track Name
              Artist Name
              42 plays
```

Example Artist Mood Fingerprint card:

```text
[Artist image]
SZA
Comfort Artist
Valence 0.62
Energy 0.41

SZA reads as a comfort artist: brighter, low-energy, and most associated with late-night listening.
```

## 15. Acceptance Criteria

This feature is complete when:

- Top Tracks displays album covers when available.
- Overview Top Tracks displays album covers when available.
- Moods artist fingerprint cards display artist images when available.
- Missing images fall back to existing placeholders.
- Broken image URLs do not show broken image icons.
- The backend stores image URLs and image source metadata.
- The enrichment job can backfill missing images.
- API responses expose image URLs needed by the frontend.
- The UI remains visually consistent with the current app.
