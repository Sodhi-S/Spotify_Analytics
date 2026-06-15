# Functional Requirements Document: Weather-Music Insight Visualizations

## 1. Product Context

The app connects a user's listening history with weather context to explain how weather changes their music mood. The system assumes each listening event has track-level mood values, especially:

- Valence: how positive or negative the song feels
- Energy: how calm or intense the song feels

The goal is not to build a weather dashboard. The goal is to show how weather affects the user's music behavior through clean visualizations, short callouts, and personalized insight cards.

## 2. Core User Goal

Users should be able to understand:

- How their music changes when the weather changes
- Which weather condition makes their music happier, sadder, calmer, or more energetic
- Whether temperature affects their listening mood
- Which weather context best matches their current music identity
- What playlist or listening behavior naturally fits the current weather

## 3. Required Data Inputs

Each listening event should include:

```ts
{
  trackId: string;
  trackName: string;
  artistName: string;
  playedAt: Date;
  valence: number; // 0 to 1
  energy: number; // 0 to 1
  durationMs: number;
  weatherCondition: "sunny" | "cloudy" | "rainy" | "snowy" | "stormy" | "foggy" | "clear";
  temperatureCelsius: number;
  precipitationMm?: number;
  cloudCover?: number;
  timeBlock: "morning" | "afternoon" | "evening" | "late_night";
}
```

Derived fields should include:

```ts
{
  moodQuadrant: "happy_hype" | "sad_reflective" | "calm_chill" | "intense_dark";
  temperatureBucket: "freezing" | "cold" | "mild" | "warm" | "hot";
  weatherLabel: string;
}
```

## 4. Mood Quadrant Logic

The system should classify tracks using valence and energy.

| Mood Quadrant | Valence | Energy | Label |
|---|---:|---:|---|
| Happy / Hype | High | High | Positive and energetic |
| Calm / Chill | High | Low | Positive and relaxed |
| Sad / Reflective | Low | Low | Negative and calm |
| Intense / Dark | Low | High | Negative and energetic |

Default threshold:

```ts
valence >= 0.5 = high valence
energy >= 0.5 = high energy
```

---

# Feature 1: Weather Mood Shift Card

## 1.1 Feature Overview

The Weather Mood Shift Card shows how one weather condition changes the user's average valence and energy compared to their overall listening average.

This should be one of the cleanest and most visible weather insights in the app.

## 1.2 Purpose

The card should answer:

> "When this weather happens, how does my music change?"

## 1.3 Functional Requirements

- The system shall calculate the user's overall average valence.
- The system shall calculate the user's overall average energy.
- The system shall calculate average valence and energy for each weather condition.
- The system shall calculate the valence delta for each weather condition.
- The system shall calculate the energy delta for each weather condition.
- The system shall display one card per major weather condition.
- The system shall identify the strongest positive and negative weather mood shifts.
- The system shall generate a short plain-language insight for each card.

## 1.4 Calculation Logic

```ts
overallAvgValence = average(valence for all listening events)
overallAvgEnergy = average(energy for all listening events)

weatherAvgValence = average(valence where weatherCondition = selectedWeather)
weatherAvgEnergy = average(energy where weatherCondition = selectedWeather)

valenceDelta = weatherAvgValence - overallAvgValence
energyDelta = weatherAvgEnergy - overallAvgEnergy

valencePercentChange = valenceDelta / overallAvgValence
energyPercentChange = energyDelta / overallAvgEnergy
```

## 1.5 UI Requirements

Each Weather Mood Shift Card should include:

- Weather condition title
- Weather icon
- Average valence shift
- Average energy shift
- Dominant mood quadrant
- One short insight sentence
- Optional top artist or top song for that weather

## 1.6 Example Card

```text
Rainy Days

Valence down 18%
Energy down 31%

Your rainy-day music is calmer and more reflective than your usual listening.
Dominant mood: Calm / Chill
Top rainy-day artist: SZA
```

## 1.7 Example Callouts

- "Rain lowers your energy more than any other weather condition."
- "Sunny days bring out your happiest listening."
- "Cloudy weather makes your music slightly darker, but not less energetic."
- "Snowy days are your calmest listening context."

## 1.8 Acceptance Criteria

This feature is complete when:

- Each major weather condition has a mood shift card.
- Valence and energy shifts are calculated against the user's baseline.
- The largest weather-driven mood shift is clearly highlighted.
- Each card has a human-readable insight.

---

# Feature 2: Weather vs Mood Heatmap

## 2.1 Feature Overview

The Weather vs Mood Heatmap shows how listening mood is distributed across different weather conditions.

Rows represent weather conditions. Columns represent mood quadrants. Each cell shows how much listening occurred in that weather-mood combination.

## 2.2 Purpose

The heatmap should answer:

> "Which moods do I listen to most under each weather condition?"

## 2.3 Functional Requirements

- The system shall group listening events by weather condition.
- The system shall classify each listening event into a mood quadrant.
- The system shall calculate listening volume for each weather-mood pair.
- The system shall support viewing by percentage, stream count, or listening minutes.
- The system shall highlight the strongest weather-mood pairing.
- The system shall generate a top insight above the heatmap.

## 2.4 Heatmap Structure

Rows:

```text
Sunny
Cloudy
Rainy
Snowy
Stormy
Foggy
Clear night
```

Columns:

```text
Happy / Hype
Calm / Chill
Sad / Reflective
Intense / Dark
```

Cell value options:

```text
Percentage of listening
Total listening minutes
Number of streams
```

## 2.5 Calculation Logic

```ts
cellValue = listeningEvents.filter(
  event.weatherCondition === weather &&
  event.moodQuadrant === mood
).sum(durationMs)
```

Percentage mode:

```ts
cellPercentage = cellListeningMinutes / totalListeningMinutesForWeather
```

## 2.6 UI Requirements

The heatmap should include:

- Weather conditions on the left axis
- Mood categories across the top axis
- Color intensity based on listening volume or percentage
- Hover state with exact value
- A top insight card
- Toggle between percentage, minutes, and stream count

## 2.7 Example Callouts

- "Rainy days are your strongest Calm/Chill trigger."
- "Sunny weather is the only condition where Happy/Hype becomes your top mood."
- "Snowy days have the highest share of low-energy listening."
- "Stormy weather pushes your music toward Intense/Dark."

## 2.8 Acceptance Criteria

This feature is complete when:

- The user can visually compare weather conditions against mood categories.
- The strongest weather-mood combination is highlighted.
- The heatmap supports at least percentage and listening minutes.
- The chart remains clean and readable on desktop and mobile.

---

# Feature 3: Valence/Energy Weather Quadrant Map

## 3.1 Feature Overview

The Valence/Energy Weather Quadrant Map plots each weather condition as a point on a two-axis mood map.

- X-axis: average valence
- Y-axis: average energy

Each point represents the user's average listening mood during that weather condition.

## 3.2 Purpose

The quadrant map should answer:

> "Where does each type of weather move my music emotionally?"

## 3.3 Functional Requirements

- The system shall calculate average valence for each weather condition.
- The system shall calculate average energy for each weather condition.
- The system shall plot each weather condition on a 2D mood map.
- The system shall label each quadrant.
- The system shall identify the weather condition farthest from the user's overall average.
- The system shall show the user's overall average listening point for comparison.

## 3.4 Quadrant Labels

| Quadrant | Meaning |
|---|---|
| High valence, high energy | Happy / Hype |
| High valence, low energy | Calm / Chill |
| Low valence, low energy | Sad / Reflective |
| Low valence, high energy | Intense / Dark |

## 3.5 UI Requirements

The chart should include:

- X-axis labeled "Valence"
- Y-axis labeled "Energy"
- Four soft background quadrant regions
- One point per weather condition
- One neutral point for "Your overall average"
- Tooltip with average valence, average energy, dominant artist, and listening minutes
- Optional connecting line from overall average to selected weather point

## 3.6 Example Callouts

- "Sunny days move your music toward Happy/Hype."
- "Rainy days pull your music toward Sad/Reflective."
- "Stormy weather is your most intense listening condition."
- "Your weather moods separate clearly: sunny is high-valence, rainy is low-energy, and stormy is high-energy."

## 3.7 Acceptance Criteria

This feature is complete when:

- Each weather condition appears as a point on the mood map.
- The overall listening average is visible.
- The app identifies the most emotionally distinct weather condition.
- The visualization is simple enough to understand without explanation.

---

# Feature 4: Temperature vs Mood Line Chart

## 4.1 Feature Overview

The Temperature vs Mood Line Chart shows how valence and energy change as temperature changes.

This feature uses numeric temperature instead of broad weather labels.

## 4.2 Purpose

The line chart should answer:

> "Does my music get happier, calmer, or more energetic as the temperature changes?"

## 4.3 Functional Requirements

- The system shall group listening events into temperature buckets.
- The system shall calculate average valence per temperature bucket.
- The system shall calculate average energy per temperature bucket.
- The system shall display valence and energy as separate lines.
- The system shall identify the temperature bucket with the highest valence.
- The system shall identify the temperature bucket with the highest energy.
- The system shall generate a short trend-based insight.

## 4.4 Temperature Buckets

Default buckets:

| Bucket | Temperature |
|---|---:|
| Freezing | Below 0 C |
| Cold | 0 C to 10 C |
| Mild | 10 C to 20 C |
| Warm | 20 C to 28 C |
| Hot | 28 C+ |

## 4.5 Calculation Logic

```ts
avgValenceByTemperatureBucket = average(valence grouped by temperatureBucket)
avgEnergyByTemperatureBucket = average(energy grouped by temperatureBucket)
```

## 4.6 UI Requirements

The chart should include:

- X-axis: temperature bucket
- Y-axis: score from 0 to 1
- Line 1: average valence
- Line 2: average energy
- Tooltip showing average valence, average energy, and listening volume
- Highlight on the highest valence bucket
- Highlight on the highest energy bucket

## 4.7 Example Callouts

- "Your music gets happier as the temperature rises."
- "Your highest-energy listening happens during warm weather."
- "Cold weather increases your calm/chill listening."
- "Hot days bring out your most positive music, but not your highest-energy music."

## 4.8 Acceptance Criteria

This feature is complete when:

- Temperature is grouped into readable buckets.
- Valence and energy are visible as separate trends.
- The system identifies the strongest temperature-mood pattern.
- The chart avoids unnecessary weather-app details.

---

# 5. Recommended Page Placement

## Overview Page

The Overview page should show only summary-level weather insights:

- Weather Mood Shift Card
- Weather Soundtrack Profile
- Current Weather Music Match
- Strongest weather callout

Example:

```text
You are a Rain Romantic.
Rain lowers your energy by 31% and shifts your listening toward Calm/Chill.
```

## Analytics Page

The Analytics page should contain the deeper visualizations:

- Weather vs Mood Heatmap
- Valence/Energy Weather Quadrant Map
- Temperature vs Mood Line Chart

## Create Page

The Create page should use weather as an input for playlist generation:

- Current weather context
- Suggested mood
- Create weather playlist button
- Manual weather override

---

# 6. Insight Generation Rules

The system should generate callouts using this structure:

```text
When [weather/context], your music becomes [measurable change], especially [artist/song/mood].
```

Examples:

```text
When it rains, your music becomes 31% lower in energy.
```

```text
Sunny days are your highest-valence listening condition.
```

```text
Rainy late nights are your strongest Calm/Chill context.
```

```text
Your music gets happier as the temperature rises.
```

```text
Stormy weather pushes your listening toward darker, higher-energy tracks.
```

---

# 7. MVP Priority

| Priority | Feature | Reason |
|---:|---|---|
| 1 | Weather Mood Shift Card | Fastest and clearest insight |
| 2 | Weather vs Mood Heatmap | Best main analytics visual |
| 3 | Valence/Energy Weather Quadrant Map | Best emotional positioning visual |
| 4 | Temperature vs Mood Line Chart | Best trend-based weather visual |

---

# 8. Success Criteria

The weather-music feature set is successful when:

- Users can clearly see how weather changes their music mood.
- Weather insights are based on valence and energy, not generic weather facts.
- Each visualization produces at least one strong personalized callout.
- The UI feels like a music insight product, not a weather app.
- The user can understand the main insight within five seconds.
