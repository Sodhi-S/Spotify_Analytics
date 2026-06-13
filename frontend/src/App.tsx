import { useEffect, useMemo, useState } from "react";
import { fetchOverview } from "./api";
import { MoodDonutChart } from "./components/MoodDonutChart";
import { PeriodSelector } from "./components/PeriodSelector";
import { StatCard } from "./components/StatCard";
import { TopList } from "./components/TopList";
import type { OverviewResponse, Period } from "./types";

function App() {
  const [period, setPeriod] = useState<Period>("30d");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchOverview(period)
      .then((data) => {
        if (!cancelled) {
          setOverview(data);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  const topTracks = useMemo(
    () =>
      overview?.top_tracks.map((track) => ({
        id: track.track_id,
        name: track.name,
        subtitle: track.artist_name,
        count: track.play_count,
      })) ?? [],
    [overview],
  );

  const topArtists = useMemo(
    () =>
      overview?.top_artists.map((artist) => ({
        id: artist.artist_id,
        name: artist.name,
        count: artist.play_count,
      })) ?? [],
    [overview],
  );

  const topTags = useMemo(
    () =>
      overview?.top_tags.map((tag) => ({
        id: tag.tag,
        name: tag.tag,
        count: tag.listen_count,
      })) ?? [],
    [overview],
  );

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>Overview</h1>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <div className={isLoading ? "content loading" : "content"}>
        <section className="stats-grid" aria-busy={isLoading}>
          <StatCard label="Total Listens" value={overview?.total_listens ?? 0} />
          <StatCard label="Unique Tracks" value={overview?.unique_tracks ?? 0} />
          <StatCard label="Unique Artists" value={overview?.unique_artists ?? 0} />
        </section>

        <section className="overview-grid">
          <TopList title="Top 5 Tracks" items={topTracks} countLabel="plays" />
          <TopList title="Top 5 Artists" items={topArtists} countLabel="plays" />
          <TopList title="Top 5 Tags" items={topTags} countLabel="listens" />
          <MoodDonutChart moodBreakdown={overview?.mood_breakdown ?? {}} />
        </section>
      </div>
    </main>
  );
}

export default App;
