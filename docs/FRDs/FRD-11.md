# FRD 11: Weather-to-Playlist Recommender

## Page Placement

This feature should live on a page called **Create**.

The Weather-to-Playlist Recommender should be placed on the Create page because it is an action-oriented feature. Instead of only showing analytics, this feature helps the user generate a playlist based on their current context.

## 1. Feature Overview

The Weather-to-Playlist Recommender creates personalized playlist recommendations using the user’s Spotify history, current weather, time of day, month, and historical listening patterns.

The goal is to recommend songs that match what the user typically listens to in similar situations.

Example:

If the current context is rainy, cold, and late at night, the app should recommend songs the user historically plays during rainy late-night conditions, plus songs with similar mood characteristics.

## 2. User Goal

Users should be able to:

- Generate a playlist based on current weather.
- Generate a playlist based on time of day.
- Generate a playlist based on mood.
- Create a playlist that matches a specific context, such as “rainy night,” “sunny morning,” or “winter chill.”
- Save or export the recommended playlist to Spotify.

## 3. Data Inputs

### Spotify Data

- User’s saved tracks
- Top tracks
- Recently played tracks
- Listening history
- Artist data
- Track metadata
- Existing playlist data, if available

### Mood Classification Data

- Track valence
- Track energy/arousal
- Mood quadrant
- Optional: tempo, danceability, acousticness

### Weather Data

- Current weather condition
- Temperature
- Precipitation
- Cloud cover
- Season/month
- Time of day

### User Context

- Current date
- Current time
- User location, if permission is granted
- Manual mood selection, if provided

## 4. Functional Requirements

- The system shall retrieve the user’s current weather based on location.
- The system shall classify the current context using weather, time of day, and month.
- The system shall identify songs the user historically played in similar contexts.
- The system shall identify songs with similar mood profiles to the current context.
- The system shall recommend a ranked list of tracks.
- The system shall allow the user to choose a target mood.
- The system shall allow the user to choose playlist length.
- The system shall allow the user to refresh or regenerate recommendations.
- The system shall allow the user to save the generated playlist to Spotify, if Spotify write permissions are granted.

## 5. Context Matching Logic

The recommender should consider:

| Context Factor | Example |
|---|---|
| Weather | Rainy, sunny, cloudy, snowy |
| Time of day | Morning, afternoon, evening, late night |
| Month/season | Winter, spring, summer, fall |
| Mood | Happy, sad, calm, intense |
| Listening history | Songs played in similar conditions |
| Audio features | Valence, energy, tempo, acousticness |

## 6. Playlist Modes

The Create page should support different playlist creation modes.

### Current Weather Mode

Creates a playlist based on the current weather.

Example: “Create a playlist for right now.”

### Rainy Night Mode

Creates a playlist using songs historically associated with rainy weather and late-night listening.

### Sunny Hype Mode

Creates a high-valence, high-energy playlist for sunny weather.

### Winter Chill Mode

Creates a low-energy playlist based on winter listening patterns.

### Custom Mood Mode

Allows users to manually choose:

- Valence level
- Energy level
- Weather type
- Time of day
- Playlist length

## 7. Recommended Playlist Output

The generated playlist should show:

- Playlist name
- Playlist description
- Track list
- Artist names
- Mood score for each track
- Context match score
- Reason for recommendation
- Option to remove a track
- Option to regenerate
- Option to save to Spotify

## 8. Example Playlist Names

The system may generate names such as:

- Rainy Night Rotation
- Sunny Morning Hype
- Cloudy Day Comfort
- Winter Chill Archive
- Late-Night Main Character Mix
- Storm Mode
- Warm Weather Energy
- Snow Day Soft Mix

## 9. Example Recommendation Explanations

Each track should include a short reason, such as:

- “You often play this song during rainy nights.”
- “This track matches your low-energy, high-valence listening pattern.”
- “This artist appears frequently in your winter listening history.”
- “This song fits your current weather and time-of-day mood profile.”

## 10. Example Callouts

- “Based on your past behavior, this is your ideal rainy-night queue.”
- “You usually listen to lower-energy music when it rains, so this playlist leans calm and reflective.”
- “Sunny weather usually increases your energy score, so this playlist includes more upbeat tracks.”
- “This playlist was built from songs you historically play during similar weather and time conditions.”

## 11. Create Page UI Requirements

The Create page should include:

- Current context card
- Weather condition
- Time of day
- Suggested mood
- Playlist generation controls
- Playlist preview
- Track recommendation cards
- Save to Spotify button
- Regenerate button
- Manual customization controls

## 12. Acceptance Criteria

This feature is complete when:

- The user can generate a playlist from current weather and time context.
- The system recommends songs based on historical listening patterns.
- The system explains why each track was recommended.
- The user can adjust the mood or playlist length.
- The user can save the playlist to Spotify, if permissions are enabled.
- The feature lives on the Create page.
