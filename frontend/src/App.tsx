import { useEffect, useMemo, useState } from "react";
import { fetchOverview } from "./api";
import { MoodsView } from "./components/MoodsView";
import { PeriodSelector } from "./components/PeriodSelector";
import { SettingsView } from "./components/SettingsView";
import { StatCard } from "./components/StatCard";
import { TopTracksView } from "./components/TopTracksView";
import { TopList } from "./components/TopList";
import { WeatherView } from "./components/WeatherView";
import type { OverviewResponse, Period } from "./types";

type View = "overview" | "top-tracks" | "moods" | "weather" | "datetime" | "create" | "settings";

const VIEW_PATHS: Record<View, string> = {
  overview: "/overview",
  "top-tracks": "/top-tracks",
  moods: "/moods",
  weather: "/weather",
  datetime: "/datetime",
  create: "/create",
  settings: "/settings",
};

function viewFromPath(pathname: string): View {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/top-tracks") {
    return "top-tracks";
  }
  if (path === "/moods") {
    return "moods";
  }
  if (path === "/weather") {
    return "weather";
  }
  if (path === "/datetime") {
    return "datetime";
  }
  if (path === "/create") {
    return "create";
  }
  if (path === "/settings") {
    return "settings";
  }
  return "overview";
}

function App() {
  const [view, setView] = useState<View>(() => viewFromPath(window.location.pathname));
  const [period, setPeriod] = useState<Period>("30d");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigateToPath = (path: string, replace = false) => {
    if (window.location.pathname === path) {
      return;
    }
    if (replace) {
      window.history.replaceState(null, "", path);
      return;
    }
    window.history.pushState(null, "", path);
  };

  const navigateToView = (nextView: View, replace = false) => {
    setView(nextView);
    navigateToPath(VIEW_PATHS[nextView], replace);
  };

  useEffect(() => {
    navigateToView(view, true);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setView(viewFromPath(window.location.pathname));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

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
        imageUrl: track.album_image_url,
        imageKind: "album" as const,
      })) ?? [],
    [overview],
  );

  const topArtists = useMemo(
    () =>
      overview?.top_artists.map((artist) => ({
        id: artist.artist_id,
        name: artist.name,
        count: artist.play_count,
        imageUrl: artist.image_url,
        imageKind: "artist" as const,
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
          onClick={() => navigateToView("overview")}
        >
          Overview
        </button>
        <button
          type="button"
          className={view === "top-tracks" ? "active" : ""}
          onClick={() => navigateToView("top-tracks")}
        >
          Top Tracks
        </button>
        <button
          type="button"
          className={view === "moods" ? "active" : ""}
          onClick={() => navigateToView("moods")}
        >
          Moods
        </button>
        <button
          type="button"
          className={view === "weather" ? "active" : ""}
          onClick={() => navigateToView("weather")}
        >
          Weather
        </button>
        <button
          type="button"
          className={view === "datetime" ? "active" : ""}
          onClick={() => navigateToView("datetime")}
        >
          DateTime
        </button>
        <button
          type="button"
          className={view === "create" ? "ai-tab active" : "ai-tab"}
          onClick={() => navigateToView("create")}
        >
          Create
        </button>
      </nav>
      <button
        type="button"
        className={view === "settings" ? "settings-corner-button active" : "settings-corner-button"}
        aria-label="Settings"
        title="Settings"
        onClick={() => navigateToView("settings")}
      >
        ⚙
      </button>

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

            <section className="overview-feature-grid">
              <TopList
                title="Top 5 Tracks"
                items={topTracks}
                countLabel="plays"
                variant="media"
                showCountLabel
              />
              <TopList
                title="Top 5 Artists"
                items={topArtists}
                countLabel="plays"
                variant="media"
                showCountLabel
              />
            </section>

            <section className="overview-bottom-grid">
              <TopList
                title="Top 5 Tags"
                items={topTags}
                countLabel="listens"
                className="overview-tags-panel"
              />
            </section>
          </div>
        </>
      ) : view === "top-tracks" ? (
        <TopTracksView period={period} onPeriodChange={setPeriod} />
      ) : view === "moods" ? (
        <MoodsView
          period={period}
          onPeriodChange={setPeriod}
          moodBreakdown={overview?.mood_breakdown ?? {}}
          isLoading={isLoading}
          error={error}
        />
      ) : view === "weather" ? (
        <WeatherView period={period} onPeriodChange={setPeriod} />
      ) : view === "datetime" ? (
        <DateTimeView />
      ) : view === "create" ? (
        <CreateView />
      ) : (
        <SettingsView />
      )}
    </main>
  );
}

function DateTimeView() {
  return <section className="empty-page" aria-label="DateTime" />;
}

function CreateView() {
  return (
    <>
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>Create</h1>
        </div>
      </header>
      <section className="panel create-panel">
        <button type="button" className="ai-create-button">
          Create with AI
        </button>
      </section>
    </>
  );
}

export default App;
