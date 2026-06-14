# FRD 10: Artist Mood Fingerprints

## Page Placement

This feature should live on a page called **Overview**.

The Artist Mood Fingerprints feature should be part of the Overview page because it gives users a quick, high-level understanding of the emotional identity of their top artists.

## 1. Feature Overview

Artist Mood Fingerprints analyze the emotional profile of each artist based on the songs the user listens to most.

Instead of only showing “Top Artists,” the app should show what each artist emotionally represents in the user’s listening history.

For example, one artist may represent high-energy hype music, while another may represent sad late-night listening.

## 2. User Goal

Users should be able to answer:

- What mood does each of my top artists represent?
- Which artist is my happiest artist?
- Which artist is my saddest artist?
- Which artist is my highest-energy artist?
- Which artist do I listen to when I want calm music?
- How do my top artists compare emotionally?

## 3. Data Inputs

The feature should use:

- User’s top artists
- Tracks listened to by each artist
- Play count or listening minutes per artist
- Track-level valence
- Track-level energy/arousal
- Track-level mood quadrant
- Optional: weather, time of day, and month context for each artist

## 4. Functional Requirements

- The system shall calculate the average valence of each artist based on the user’s listening history.
- The system shall calculate the average energy of each artist based on the user’s listening history.
- The system shall classify each artist into a mood quadrant.
- The system shall rank artists by listening minutes or stream count.
- The system shall identify the user’s happiest artist.
- The system shall identify the user’s saddest artist.
- The system shall identify the user’s highest-energy artist.
- The system shall identify the user’s calmest artist.
- The system shall display top artists on a valence-energy scatter plot.
- The system shall provide a short explanation for each artist’s mood fingerprint.

## 5. Mood Fingerprint Labels

The system may assign artist labels such as:

| Label | Meaning |
|---|---|
| Hype Artist | High energy, high valence |
| Rage Artist | High energy, low valence |
| Sad Artist | Low energy, low valence |
| Comfort Artist | Low energy, high or neutral valence |
| Night Artist | Mostly played late at night |
| Rainy Day Artist | Mostly played during rainy/cloudy weather |
| Main Character Artist | Played often during evening or late-night sessions |
| Seasonal Artist | Strongly associated with a specific month or season |

## 6. Overview Page UI Requirements

The Overview page should include a section called **Artist Mood Fingerprints**.

This section should include:

- Top 5 to 10 artists
- Artist name and image, if available
- Mood fingerprint label
- Average valence score
- Average energy score
- Listening minutes or stream count
- Small visual bar for valence
- Small visual bar for energy
- Optional mini scatter plot showing artists on the mood map

## 7. Example Artist Cards

Each artist card should show:

- Artist name
- Artist image
- Mood fingerprint
- Average valence
- Average energy
- Dominant listening context
- Short insight

Example:

> Drake is one of your Late-Night Artists. You listen to him most often after 10 PM, and his average mood profile in your history is low-valence, medium-energy.

## 8. Example Callouts

- “Your happiest artist is Artist A, with an average valence of 0.82.”
- “Your highest-energy artist is Artist B.”
- “Artist C is your main comfort artist, appearing most often during late-night and rainy listening sessions.”
- “Your top artists split into two clear groups: high-energy hype and low-energy reflective.”

## 9. Acceptance Criteria

This feature is complete when:

- The Overview page displays artist mood fingerprints.
- Each artist has a calculated valence and energy score.
- Each artist is assigned a readable mood label.
- The user can visually compare artists by mood.
- The system generates at least one meaningful artist-based insight.
