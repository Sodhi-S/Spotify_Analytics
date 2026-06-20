import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  fetchOverview,
  lastfmLoginUrl,
  loginWithPassword,
  logout as logoutUser,
  setAppPassword,
} from "./api";
import { DateTimeView } from "./components/DateTimeView";
import { MoodsView } from "./components/MoodsView";
import { PeriodSelector } from "./components/PeriodSelector";
import { SettingsView } from "./components/SettingsView";
import { StatCard } from "./components/StatCard";
import { TopTracksView } from "./components/TopTracksView";
import { TopList } from "./components/TopList";
import { WeatherView } from "./components/WeatherView";
import type { AuthUser, IngestionJob, OverviewResponse, Period } from "./types";

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

function shouldReplaceWithOverview(pathname: string) {
  const path = pathname.replace(/\/+$/, "") || "/";
  return path === "/" || path === "/login" || path === "/auth" || path === "/auth/callback";
}

function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [forcePasswordSetup, setForcePasswordSetup] = useState(
    () => new URLSearchParams(window.location.search).get("set_password") === "1",
  );
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

  const clearPasswordSetupParam = () => {
    if (new URLSearchParams(window.location.search).has("set_password")) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  };

  useEffect(() => {
    if (shouldReplaceWithOverview(window.location.pathname)) {
      navigateToView("overview", true);
      return;
    }
    navigateToView(view, true);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setView(viewFromPath(window.location.pathname));
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const refreshAuth = () =>
    fetchCurrentUser()
      .then((user) => {
        setAuthUser(user);
        setAuthError(null);
      })
      .catch((err: Error) => {
        setAuthError(err.message);
      })
      .finally(() => {
        setIsAuthLoading(false);
      });

  useEffect(() => {
    refreshAuth();
  }, []);

  useEffect(() => {
    if (authUser) {
      return undefined;
    }

    const handleFocus = () => {
      refreshAuth();
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [authUser]);

  const latestJob = authUser?.ingestion_job ?? null;
  const isImporting = latestJob?.status === "queued" || latestJob?.status === "running";

  useEffect(() => {
    if (!isImporting) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      refreshAuth();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [isImporting]);

  useEffect(() => {
    if (!authUser || isImporting) {
      setIsLoading(false);
      return;
    }

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
  }, [period, authUser?.id, isImporting]);

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

  const handleLogout = () => {
    logoutUser()
      .catch((err: Error) => setAuthError(err.message))
      .finally(() => {
        setAuthUser(null);
        setOverview(null);
        setView("overview");
      });
  };

  if (isAuthLoading) {
    return <AuthLoadingView />;
  }

  if (!authUser) {
    return (
      <LoginView
        error={authError}
        onLogin={(user) => {
          setAuthUser(user);
          setAuthError(null);
        }}
      />
    );
  }

  if (!authUser.has_password || forcePasswordSetup) {
    return (
      <SetPasswordView
        user={authUser}
        onPasswordSet={(user) => {
          setAuthUser(user);
          setAuthError(null);
          setForcePasswordSetup(false);
          clearPasswordSetupParam();
        }}
        onLogout={handleLogout}
      />
    );
  }

  if (isImporting) {
    return (
      <ImportStatusView
        user={authUser}
        job={latestJob}
        onRefresh={refreshAuth}
        onLogout={handleLogout}
      />
    );
  }

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
      <button
        type="button"
        className="signout-corner-button"
        onClick={handleLogout}
      >
        Sign out
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

          {latestJob?.status === "failed" ? (
            <div className="banner">
              {latestJob.error_message ?? "Last.fm import failed."}
            </div>
          ) : null}
          {authError ? <div className="banner">{authError}</div> : null}
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
              <ValenceEnergyExplainer />
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

function ValenceEnergyExplainer() {
  return (
    <section className="panel metric-explainer-panel">
      <div className="panel-heading">
        <h2>Valence & Energy - Explained</h2>
        <span>0.00 to 1.00</span>
      </div>
      <div className="metric-explainer-grid">
        <article className="metric-explainer-card">
          <span>Valence</span>
          <strong>Emotional brightness</strong>
          <p>
            Valence estimates how positive or negative a track feels. Lower values
            are darker, sadder, or more tense; higher values feel brighter, happier,
            or more uplifting.
          </p>
          <div className="metric-scale" aria-hidden="true">
            <span>0.00</span>
            <i />
            <span>1.00</span>
          </div>
        </article>
        <article className="metric-explainer-card">
          <span>Energy</span>
          <strong>Intensity and activity</strong>
          <p>
            Energy estimates how active, loud, fast, or intense a track feels. Lower
            values are calmer and softer; higher values are more driving, loud, or
            physically energetic.
          </p>
          <div className="metric-scale" aria-hidden="true">
            <span>0.00</span>
            <i />
            <span>1.00</span>
          </div>
        </article>
      </div>
    </section>
  );
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

function AuthLoadingView() {
  return (
    <main className="dashboard-shell auth-shell">
      <section className="panel auth-panel">
        <p className="auth-kicker">Music Listening Intelligence</p>
        <h1>Loading</h1>
      </section>
    </main>
  );
}

function LoginView({
  error,
  onLogin,
}: {
  error: string | null;
  onLogin: (user: AuthUser) => void;
}) {
  const [lastfmUsername, setLastfmUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  function handlePasswordLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const username = lastfmUsername.trim();
    if (!username || !password) {
      setLoginError("Username and password are required.");
      return;
    }

    setIsSubmitting(true);
    setLoginError(null);
    loginWithPassword(username, password)
      .then(onLogin)
      .catch((err: Error) => setLoginError(err.message))
      .finally(() => setIsSubmitting(false));
  }

  return (
    <main className="dashboard-shell auth-shell">
      <section className="panel auth-panel">
        <p className="auth-kicker">Music Listening Intelligence</p>
        <h1>Last.fm sign in</h1>
        {error ? <div className="banner">{error}</div> : null}
        {loginError ? <div className="banner">{loginError}</div> : null}
        <form className="auth-form" onSubmit={handlePasswordLogin}>
          <label className="settings-field">
            <span>Last.fm username</span>
            <input
              value={lastfmUsername}
              onChange={(event) => setLastfmUsername(event.target.value)}
              placeholder="Username"
              autoComplete="username"
              disabled={isSubmitting}
            />
          </label>
          <label className="settings-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="App password"
              autoComplete="current-password"
              disabled={isSubmitting}
            />
          </label>
          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Signing in" : "Log in"}
          </button>
        </form>
        <div className="auth-actions">
          <a
            className="secondary-link-button"
            href={lastfmLoginUrl("set_password")}
            target="_blank"
            rel="noreferrer"
          >
            Connect or reset with Last.fm
          </a>
          <a className="secondary-link-button" href="https://www.last.fm/join">
            Create Last.fm account
          </a>
        </div>
      </section>
    </main>
  );
}

function SetPasswordView({
  user,
  onPasswordSet,
  onLogout,
}: {
  user: AuthUser;
  onPasswordSet: (user: AuthUser) => void;
  onLogout: () => void;
}) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  function handleSetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    setPasswordError(null);
    setAppPassword(password)
      .then(onPasswordSet)
      .catch((err: Error) => setPasswordError(err.message))
      .finally(() => setIsSubmitting(false));
  }

  return (
    <main className="dashboard-shell auth-shell">
      <section className="panel auth-panel">
        <p className="auth-kicker">@{user.display_name ?? user.lastfm_username}</p>
        <h1>Create password</h1>
        {passwordError ? <div className="banner">{passwordError}</div> : null}
        <form className="auth-form" onSubmit={handleSetPassword}>
          <label className="settings-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              autoComplete="new-password"
              disabled={isSubmitting}
            />
          </label>
          <label className="settings-field">
            <span>Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat password"
              autoComplete="new-password"
              disabled={isSubmitting}
            />
          </label>
          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Saving" : "Save password"}
          </button>
        </form>
        <div className="auth-actions">
          <button type="button" className="secondary-button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </section>
    </main>
  );
}

function ImportStatusView({
  user,
  job,
  onRefresh,
  onLogout,
}: {
  user: AuthUser;
  job: IngestionJob | null;
  onRefresh: () => void;
  onLogout: () => void;
}) {
  return (
    <main className="dashboard-shell auth-shell">
      <section className="panel auth-panel">
        <p className="auth-kicker">@{user.display_name ?? user.lastfm_username}</p>
        <h1>Importing Last.fm</h1>
        <div className="import-status">
          <span>{job?.status ?? "queued"}</span>
          <strong>{job?.started_at ? "Sync in progress" : "Waiting to start"}</strong>
        </div>
        <div className="auth-actions">
          <button type="button" className="primary-button" onClick={onRefresh}>
            Refresh
          </button>
          <button type="button" className="secondary-button" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </section>
    </main>
  );
}

export default App;
