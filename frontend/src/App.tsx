import { useEffect, useMemo, useState } from "react";
import { fetchOverview } from "./api";
import { MoodDonutChart } from "./components/MoodDonutChart";
import { PeriodSelector } from "./components/PeriodSelector";
import { SettingsView } from "./components/SettingsView";
import { StatCard } from "./components/StatCard";
import { TopTracksView } from "./components/TopTracksView";
import { TopList } from "./components/TopList";
import { WeatherView } from "./components/WeatherView";
import type { OverviewResponse, Period } from "./types";

type View = "overview" | "top-tracks" | "weather" | "settings";

function App() {
  const [view, setView] = useState<View>("overview");
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
      <nav className="view-tabs" aria-label="Dashboard views">
        <button
          type="button"
          className={view === "overview" ? "active" : ""}
          onClick={() => setView("overview")}
        >
          Overview
        </button>
        <button
          type="button"
          className={view === "top-tracks" ? "active" : ""}
          onClick={() => setView("top-tracks")}
        >
          Top Tracks
        </button>
        <button
          type="button"
          className={view === "weather" ? "active" : ""}
          onClick={() => setView("weather")}
        >
          Weather
        </button>
        <button
          type="button"
          className={view === "settings" ? "active" : ""}
          onClick={() => setView("settings")}
        >
          Settings
        </button>
      </nav>

      {view === "overview" ? (
        <>
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
        </>
      ) : view === "top-tracks" ? (
        <TopTracksView period={period} onPeriodChange={setPeriod} />
      ) : view === "weather" ? (
        <WeatherView period={period} onPeriodChange={setPeriod} />
      ) : (
        <SettingsView />
      )}
    </main>
  );
}

export default App;
