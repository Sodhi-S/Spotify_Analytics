import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { fetchTopTracks } from "../api";
import { formatCount, formatDuration } from "../privacy";
import type { Period, TopTracksResponse } from "../types";
import { AnimatedNumber } from "./AnimatedNumber";
import { ImageThumbnail } from "./ImageThumbnail";
import { pageCount, pageItems, PaginationControls } from "./PaginationControls";
import { PeriodSelector } from "./PeriodSelector";

const PAGE_SIZE_OPTIONS = [10, 25, 50];
const MAX_TRACKS = 50;

interface TopTracksViewProps {
  period: Period;
  onPeriodChange: (period: Period) => void;
}

function formatMood(label: string | null, confidence: number | null) {
  if (!label) {
    return "Unclassified";
  }
  if (confidence === null) {
    return label;
  }
  return `${label} ${(confidence * 100).toFixed(0)}%`;
}

export function TopTracksView({ period, onPeriodChange }: TopTracksViewProps) {
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<TopTracksResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchTopTracks(period, MAX_TRACKS)
      .then((response) => {
        if (!cancelled) {
          setData(response);
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

  useEffect(() => {
    setPage(1);
  }, [period, pageSize]);

  const tracks = data?.tracks ?? [];
  const totalPages = pageCount(tracks.length, pageSize);
  const safePage = Math.min(page, totalPages);
  const visibleTracks = pageItems(tracks, safePage, pageSize);

  return (
    <>
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>Top Tracks</h1>
        </div>
        <div className="header-controls">
          <PeriodSelector value={period} onChange={onPeriodChange} />
          <label className="select-control">
            <span>Rows</span>
            <select
              value={pageSize}
              onChange={(event) => setPageSize(Number(event.target.value))}
            >
              {PAGE_SIZE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <section className={isLoading ? "panel top-tracks-panel loading" : "panel top-tracks-panel"}>
        {tracks.length ? (
          <div className="tracks-table" role="table" aria-label="Top tracks">
            <div className="tracks-row tracks-head" role="row">
              <span>#</span>
              <span>Track</span>
              <span>Plays</span>
              <span>Time</span>
              <span>Mood</span>
            </div>
            {visibleTracks.map((track, index) => (
              <div
                className="tracks-row"
                role="row"
                key={track.track_id}
                style={{ "--row-index": index } as CSSProperties}
              >
                <strong>{track.rank}</strong>
                <div className="track-identity">
                  <ImageThumbnail
                    src={track.album_image_url}
                    className="track-artwork"
                    alt=""
                  />
                  <div className="track-cell">
                    <span>{track.name}</span>
                    <small>
                      {track.artist_name}
                      {track.album ? ` · ${track.album}` : ""}
                    </small>
                    {track.top_tags.length ? (
                      <div className="tag-strip">
                        {track.top_tags.slice(0, 4).map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
                <strong>
                  <AnimatedNumber value={track.play_count} formatter={formatCount} />
                </strong>
                <span>{formatDuration(track.total_ms_played)}</span>
                <span className={track.mood_label ? "mood-pill" : "mood-pill muted"}>
                  {formatMood(track.mood_label, track.mood_confidence)}
                </span>
              </div>
            ))}
            <PaginationControls
              page={safePage}
              pageSize={pageSize}
              totalItems={tracks.length}
              onPageChange={setPage}
              label="Top tracks pages"
            />
          </div>
        ) : (
          <p className="empty-state">No track data yet</p>
        )}
      </section>
    </>
  );
}
