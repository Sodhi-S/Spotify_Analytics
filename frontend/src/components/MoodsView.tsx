import type { CSSProperties, WheelEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { fetchArtistMoodFingerprints } from "../api";
import { formatCount, hideRealNumbers } from "../privacy";
import type {
  ArtistMoodFingerprint,
  ArtistMoodFingerprintsResponse,
  Period,
} from "../types";
import { MoodDonutChart } from "./MoodDonutChart";
import { AnimatedNumber } from "./AnimatedNumber";
import { ImageThumbnail } from "./ImageThumbnail";
import { PeriodSelector } from "./PeriodSelector";

interface MoodsViewProps {
  period: Period;
  onPeriodChange: (period: Period) => void;
  moodBreakdown: Record<string, number>;
  isLoading: boolean;
  error: string | null;
}

interface MoodTooltipProps {
  active?: boolean;
  payload?: {
    payload: ArtistMoodFingerprint & { display_weight: number };
  }[];
}

type MoodDomain = [number, number];

const DEFAULT_DOMAIN: MoodDomain = [0, 1];

function clampDomain(domain: MoodDomain): MoodDomain {
  const width = domain[1] - domain[0];
  if (domain[0] < 0) {
    return [0, width];
  }
  if (domain[1] > 1) {
    return [1 - width, 1];
  }
  return domain;
}

function zoomDomain(domain: MoodDomain, direction: "in" | "out", anchor = 0.5): MoodDomain {
  const width = domain[1] - domain[0];
  const nextWidth = direction === "in" ? Math.max(width * 0.72, 0.18) : Math.min(width / 0.72, 1);
  const center = domain[0] + width * anchor;
  return clampDomain([center - nextWidth * anchor, center + nextWidth * (1 - anchor)]);
}

function formatScore(value: number | null) {
  return value === null ? "Pending" : value.toFixed(2);
}

function formatPercent(value: number | null) {
  return value === null ? "0%" : `${Math.round(value * 100)}%`;
}

function MoodMapTooltip({ active, payload }: MoodTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  const artist = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <ImageThumbnail
        src={artist.image_url}
        className="tooltip-artist-image"
        alt=""
      />
      <strong>{artist.name}</strong>
      <span>{artist.mood_label}</span>
      <span>
        Upbeatness {formatScore(artist.avg_valence)} · Energy {formatScore(artist.avg_energy)}
      </span>
      <span>{formatCount(artist.play_count, "plays")}</span>
      <span>{artist.dominant_context}</span>
    </div>
  );
}

function FingerprintCard({ artist, index }: { artist: ArtistMoodFingerprint; index: number }) {
  return (
    <article className="fingerprint-card" style={{ "--row-index": index } as CSSProperties}>
      <div className="fingerprint-card-top">
        <ImageThumbnail
          src={artist.image_url}
          className="artist-avatar"
          alt=""
        />
        <div>
          <span>#{artist.rank}</span>
          <strong>{artist.name}</strong>
          <small>{artist.mood_label}</small>
        </div>
      </div>

      <div className="fingerprint-bars">
        <div>
          <span>Valence</span>
          <strong>{formatScore(artist.avg_valence)}</strong>
          <div className="fingerprint-meter">
            <span style={{ width: formatPercent(artist.avg_valence) }} />
          </div>
        </div>
        <div>
          <span>Energy</span>
          <strong>{formatScore(artist.avg_energy)}</strong>
          <div className="fingerprint-meter">
            <span style={{ width: formatPercent(artist.avg_energy) }} />
          </div>
        </div>
      </div>

      <div className="fingerprint-meta">
        <span>
          <AnimatedNumber
            value={artist.play_count}
            formatter={(value) => formatCount(value, "plays")}
          />
        </span>
        <span>
          <AnimatedNumber
            value={artist.listening_minutes}
            formatter={(value) => formatCount(value, "min")}
          />
        </span>
        <span>{artist.dominant_context}</span>
      </div>

      <p>{artist.insight}</p>
    </article>
  );
}

export function MoodsView({
  period,
  onPeriodChange,
  moodBreakdown,
  isLoading,
  error,
}: MoodsViewProps) {
  const [fingerprints, setFingerprints] = useState<ArtistMoodFingerprintsResponse | null>(null);
  const [isFingerprintLoading, setIsFingerprintLoading] = useState(true);
  const [fingerprintError, setFingerprintError] = useState<string | null>(null);
  const [fingerprintsExpanded, setFingerprintsExpanded] = useState(false);
  const [xDomain, setXDomain] = useState<MoodDomain>(DEFAULT_DOMAIN);
  const [yDomain, setYDomain] = useState<MoodDomain>(DEFAULT_DOMAIN);

  useEffect(() => {
    let cancelled = false;
    setIsFingerprintLoading(true);
    setFingerprintError(null);
    setFingerprintsExpanded(false);

    fetchArtistMoodFingerprints(period)
      .then((response) => {
        if (!cancelled) {
          setFingerprints(response);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setFingerprintError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsFingerprintLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [period]);

  const scatterArtists = useMemo(
    () =>
      fingerprints?.artists
        .filter((artist) => artist.avg_valence !== null && artist.avg_energy !== null)
        .map((artist) => ({
          ...artist,
          display_weight: hideRealNumbers ? 1 : artist.play_count,
        })) ?? [],
    [fingerprints],
  );

  const fingerprintArtists = fingerprints?.artists ?? [];
  const visibleFingerprintArtists = fingerprintsExpanded
    ? fingerprintArtists
    : fingerprintArtists.slice(0, 2);

  const isZoomed = xDomain[0] !== 0 || xDomain[1] !== 1 || yDomain[0] !== 0 || yDomain[1] !== 1;

  function handleZoom(direction: "in" | "out") {
    setXDomain((domain) => zoomDomain(domain, direction));
    setYDomain((domain) => zoomDomain(domain, direction));
  }

  function resetZoom() {
    setXDomain(DEFAULT_DOMAIN);
    setYDomain(DEFAULT_DOMAIN);
  }

  function handleMoodMapWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const xAnchor = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
    const yAnchor = 1 - Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1);
    const direction = event.deltaY > 0 ? "out" : "in";
    setXDomain((domain) => zoomDomain(domain, direction, xAnchor));
    setYDomain((domain) => zoomDomain(domain, direction, yAnchor));
  }

  return (
    <>
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>Moods</h1>
        </div>
        <PeriodSelector value={period} onChange={onPeriodChange} />
      </header>

      {error ? <div className="banner">{error}</div> : null}
      {fingerprintError ? <div className="banner">{fingerprintError}</div> : null}

      <div className={isLoading || isFingerprintLoading ? "content loading" : "content"}>
        <section className="mood-callout-grid">
          {(fingerprints?.callouts ?? []).map((callout) => (
            <article className="mood-callout" key={callout.kind}>
              <span>{callout.kind.replace(/_/g, " ")}</span>
              <strong>{callout.artist_name ?? "Pending"}</strong>
              <p>{callout.text}</p>
            </article>
          ))}
        </section>

        <section className="mood-dashboard-grid">
          <section className="panel mood-map-panel">
            <div className="panel-heading">
              <h2>Artist Mood Map</h2>
              <div className="mood-map-controls" aria-label="Mood map zoom controls">
                <span>{scatterArtists.length} scored artists</span>
                <button type="button" onClick={() => handleZoom("out")} disabled={!isZoomed}>
                  -
                </button>
                <button type="button" onClick={() => handleZoom("in")}>
                  +
                </button>
                <button type="button" onClick={resetZoom} disabled={!isZoomed}>
                  Reset
                </button>
              </div>
            </div>
            {scatterArtists.length ? (
              <div className="mood-map-axis-note">
                <span>Left: darker/less upbeat</span>
                <span>Right: brighter/more upbeat</span>
                <span>Bottom: low energy</span>
                <span>Top: high energy</span>
              </div>
            ) : null}
            {scatterArtists.length ? (
              <div className="mood-map-frame" onWheel={handleMoodMapWheel}>
                <div className="mood-quadrant-label mood-quadrant-calm">calm / grounded</div>
                <div className="mood-quadrant-label mood-quadrant-hype">bright / hype</div>
                <div className="mood-quadrant-label mood-quadrant-heavy">dark / intense</div>
                <div className="mood-quadrant-label mood-quadrant-soft">soft / reflective</div>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 16, right: 18, bottom: 18, left: 0 }}>
                    <CartesianGrid stroke="rgb(255 255 255 / 8%)" />
                    <XAxis
                      type="number"
                      dataKey="avg_valence"
                      name="Upbeatness"
                      domain={xDomain}
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      stroke="rgb(255 255 255 / 24%)"
                      label={{
                        value: "Upbeatness / valence",
                        position: "insideBottom",
                        offset: -10,
                        fill: "#b7beb8",
                        fontSize: 12,
                      }}
                    />
                    <YAxis
                      type="number"
                      dataKey="avg_energy"
                      name="Energy"
                      domain={yDomain}
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      stroke="rgb(255 255 255 / 24%)"
                      label={{
                        value: "Energy / arousal",
                        angle: -90,
                        position: "insideLeft",
                        fill: "#b7beb8",
                        fontSize: 12,
                      }}
                    />
                    <ZAxis type="number" dataKey="display_weight" range={[120, 240]} />
                    <ReferenceLine x={0.5} stroke="rgb(84 245 139 / 24%)" />
                    <ReferenceLine y={0.5} stroke="rgb(84 245 139 / 24%)" />
                    <Tooltip content={<MoodMapTooltip />} />
                    <Scatter data={scatterArtists} fill="#54f58b" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="empty-state">Artist mood scores are pending.</p>
            )}
          </section>

          <MoodDonutChart moodBreakdown={moodBreakdown} />
        </section>

        <section className="panel artist-fingerprints-panel">
          <div className="panel-heading">
            <h2>Artist Mood Fingerprints</h2>
            <span>Top artists by plays</span>
          </div>
          {fingerprintArtists.length ? (
            <>
              <div className="fingerprint-grid">
                {visibleFingerprintArtists.map((artist, index) => (
                  <FingerprintCard artist={artist} index={index} key={artist.artist_id} />
                ))}
              </div>
              {fingerprintArtists.length > 2 ? (
                <button
                  type="button"
                  className="fingerprint-expand-button"
                  aria-expanded={fingerprintsExpanded}
                  onClick={() => setFingerprintsExpanded((expanded) => !expanded)}
                >
                  <span>{fingerprintsExpanded ? "Show first row" : `Show all ${fingerprintArtists.length}`}</span>
                  <span className="fingerprint-expand-icon" aria-hidden="true" />
                </button>
              ) : null}
            </>
          ) : (
            <p className="empty-state">No artist fingerprints yet.</p>
          )}
        </section>
      </div>
    </>
  );
}
