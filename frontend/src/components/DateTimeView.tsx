import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchDateTimeMonthDetail, fetchDateTimeOverview } from "../api";
import { formatCount, hideRealNumbers } from "../privacy";
import type {
  DateTimeDayBucket,
  DateTimeHeatmapCell,
  DateTimeHourBucket,
  DateTimeMonthBucket,
  DateTimeMonthDetailResponse,
  DateTimeOverviewResponse,
  Period,
} from "../types";
import { AnimatedNumber } from "./AnimatedNumber";
import { ImageThumbnail } from "./ImageThumbnail";
import { PeriodSelector } from "./PeriodSelector";
import { StatCard } from "./StatCard";

type HeatmapMode = "listens" | "mood" | "energy";

const DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HEATMAP_MODES: HeatmapMode[] = ["listens", "mood", "energy"];
const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const MOOD_COLORS: Record<string, string> = {
  happy: "#54f58b",
  energetic: "#ffd166",
  calm: "#8cc7ff",
  melancholic: "#b47cff",
  sad: "#5f7d9a",
  angry: "#ff6b73",
};

function formatScore(value: number | null) {
  return value === null ? "N/A" : value.toFixed(2);
}

function formatMonthLabel(yearMonth: string) {
  const [year, month] = yearMonth.split("-");
  const index = Number(month) - 1;
  if (Number.isNaN(index) || index < 0 || index > 11) {
    return yearMonth;
  }
  return `${MONTH_NAMES[index]} ${year}`;
}

function formatHour(hour: number | null) {
  if (hour === null) {
    return "N/A";
  }
  if (hour === 0) return "12 AM";
  if (hour === 12) return "12 PM";
  return hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
}

function moodColor(mood: string | null) {
  if (!mood) {
    return "rgb(255 255 255 / 8%)";
  }
  return MOOD_COLORS[mood.toLowerCase()] ?? "rgb(255 255 255 / 16%)";
}

interface TimelineTooltipProps {
  active?: boolean;
  payload?: { payload: DateTimeMonthBucket }[];
}

function TimelineTooltip({ active, payload }: TimelineTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  const bucket = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{formatMonthLabel(bucket.year_month)}</strong>
      <span>{formatCount(bucket.total_listens, "listens")}</span>
      <span>
        Valence {formatScore(bucket.avg_valence)} · Energy {formatScore(bucket.avg_energy)}
      </span>
      {bucket.dominant_mood ? <span>Mostly {bucket.dominant_mood}</span> : null}
      {bucket.top_artist_name ? <span>Top: {bucket.top_artist_name}</span> : null}
    </div>
  );
}

interface HourTooltipProps {
  active?: boolean;
  payload?: { payload: DateTimeHourBucket }[];
}

function HourTooltip({ active, payload }: HourTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  const bucket = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{formatHour(bucket.hour)}</strong>
      <span>{bucket.time_segment}</span>
      <span>{formatCount(bucket.total_listens, "listens")}</span>
      <span>
        Valence {formatScore(bucket.avg_valence)} · Energy {formatScore(bucket.avg_energy)}
      </span>
      {bucket.dominant_mood ? <span>Mostly {bucket.dominant_mood}</span> : null}
    </div>
  );
}

function DayCard({ day, maxListens }: { day: DateTimeDayBucket; maxListens: number }) {
  return (
    <article className={day.is_weekend ? "datetime-day-card weekend" : "datetime-day-card"}>
      <div className="datetime-day-head">
        <strong>{day.day_of_week}</strong>
        <span>
          <AnimatedNumber
            value={day.total_listens}
            formatter={(value) => formatCount(value, "listens")}
          />
        </span>
      </div>
      <div className="weather-meter" aria-hidden="true">
        <span
          style={{
            width: hideRealNumbers ? "100%" : `${(day.total_listens / maxListens) * 100}%`,
          }}
        />
      </div>
      <div className="datetime-day-meta">
        <span>Valence {formatScore(day.avg_valence)}</span>
        <span>Energy {formatScore(day.avg_energy)}</span>
      </div>
      <div className="datetime-day-meta">
        <span>{day.dominant_mood ?? "Unclassified"}</span>
        <span>{day.top_artist_name ?? "—"}</span>
      </div>
    </article>
  );
}

function heatmapIntensity(cell: DateTimeHeatmapCell, mode: HeatmapMode, maxListens: number) {
  if (mode === "energy") {
    return cell.avg_energy ?? 0;
  }
  if (mode === "listens") {
    return maxListens === 0 ? 0 : cell.total_listens / maxListens;
  }
  return cell.total_listens === 0 ? 0 : 1;
}

function MonthDetailPanel({
  detail,
  isLoading,
  error,
}: {
  detail: DateTimeMonthDetailResponse | null;
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <section className="panel datetime-month-detail-panel">
      <div className="panel-heading">
        <h2>{detail ? formatMonthLabel(detail.year_month) : "Month Detail"}</h2>
        <span>{detail ? formatCount(detail.total_listens, "listens") : "Select a month"}</span>
      </div>
      {error ? <p className="empty-state">{error}</p> : null}
      {isLoading ? (
        <p className="empty-state">Loading month…</p>
      ) : !detail ? (
        <p className="empty-state">Select a month in the timeline to see its detail.</p>
      ) : detail.total_listens === 0 ? (
        <p className="empty-state">No listening recorded for this month yet.</p>
      ) : (
        <>
          <p className="datetime-month-summary">{detail.summary}</p>
          <div className="datetime-month-stats">
            <div>
              <span>Unique tracks</span>
              <strong>{formatCount(detail.unique_tracks)}</strong>
            </div>
            <div>
              <span>Unique artists</span>
              <strong>{formatCount(detail.unique_artists)}</strong>
            </div>
            <div>
              <span>Valence</span>
              <strong>{formatScore(detail.avg_valence)}</strong>
            </div>
            <div>
              <span>Energy</span>
              <strong>{formatScore(detail.avg_energy)}</strong>
            </div>
          </div>
          <div className="datetime-month-columns">
            <div>
              <h3>Top Tracks</h3>
              {detail.top_tracks.length ? (
                <ul className="datetime-rank-list">
                  {detail.top_tracks.slice(0, 5).map((track, index) => (
                    <li key={track.track_id}>
                      <span className="datetime-rank">{index + 1}</span>
                      <ImageThumbnail
                        src={track.album_image_url}
                        className="datetime-rank-image"
                        alt=""
                      />
                      <div>
                        <strong>{track.name}</strong>
                        <small>{track.artist_name}</small>
                      </div>
                      <span className="datetime-rank-count">
                        {formatCount(track.play_count)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-state">No tracks.</p>
              )}
            </div>
            <div>
              <h3>Top Artists</h3>
              {detail.top_artists.length ? (
                <ul className="datetime-rank-list">
                  {detail.top_artists.slice(0, 5).map((artist, index) => (
                    <li key={artist.artist_id}>
                      <span className="datetime-rank">{index + 1}</span>
                      <ImageThumbnail
                        src={artist.image_url}
                        className="datetime-rank-image artist"
                        alt=""
                      />
                      <div>
                        <strong>{artist.name}</strong>
                      </div>
                      <span className="datetime-rank-count">
                        {formatCount(artist.play_count)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-state">No artists.</p>
              )}
            </div>
          </div>
          {detail.top_tags.length ? (
            <div className="tag-strip">
              {detail.top_tags.slice(0, 6).map((tag) => (
                <span key={tag.tag}>
                  {tag.tag} (<AnimatedNumber value={tag.listen_count} formatter={formatCount} />)
                </span>
              ))}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

export function DateTimeView() {
  const [period, setPeriod] = useState<Period>("7d");
  const [data, setData] = useState<DateTimeOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heatmapMode, setHeatmapMode] = useState<HeatmapMode>("listens");

  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [monthDetail, setMonthDetail] = useState<DateTimeMonthDetailResponse | null>(null);
  const [isMonthLoading, setIsMonthLoading] = useState(false);
  const [monthError, setMonthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchDateTimeOverview(period)
      .then((response) => {
        if (!cancelled) {
          setData(response);
          const fallbackMonth =
            response.most_active_month ??
            response.monthly[response.monthly.length - 1]?.year_month ??
            null;
          setSelectedMonth(fallbackMonth);
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
    if (!selectedMonth) {
      setMonthDetail(null);
      return;
    }
    let cancelled = false;
    setIsMonthLoading(true);
    setMonthError(null);

    fetchDateTimeMonthDetail(selectedMonth, "all")
      .then((response) => {
        if (!cancelled) {
          setMonthDetail(response);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setMonthError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsMonthLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMonth]);

  const monthly = data?.monthly ?? [];
  const days = data?.days ?? [];
  const hours = data?.hours ?? [];
  const heatmap = data?.heatmap ?? [];

  const maxDayListens = useMemo(
    () => (hideRealNumbers ? 1 : Math.max(...days.map((day) => day.total_listens), 1)),
    [days],
  );

  const maxHeatmapListens = useMemo(
    () => Math.max(...heatmap.map((cell) => cell.total_listens), 0),
    [heatmap],
  );

  const heatmapByCell = useMemo(() => {
    const map = new Map<string, DateTimeHeatmapCell>();
    heatmap.forEach((cell) => map.set(`${cell.day_of_week}-${cell.hour}`, cell));
    return map;
  }, [heatmap]);

  const weekdayWeekend = useMemo(() => {
    const weekdays = days.filter((day) => !day.is_weekend);
    const weekend = days.filter((day) => day.is_weekend);
    const sum = (items: DateTimeDayBucket[]) =>
      items.reduce((total, day) => total + day.total_listens, 0);
    const avgEnergy = (items: DateTimeDayBucket[]) => {
      const scored = items.filter((day) => day.avg_energy !== null);
      if (!scored.length) return null;
      return scored.reduce((total, day) => total + (day.avg_energy ?? 0), 0) / scored.length;
    };
    return {
      weekdayListens: sum(weekdays),
      weekendListens: sum(weekend),
      weekdayEnergy: avgEnergy(weekdays),
      weekendEnergy: avgEnergy(weekend),
    };
  }, [days]);

  const hasData = !isLoading && data !== null && data.total_listens > 0;

  return (
    <>
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>DateTime</h1>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <div className={isLoading ? "content loading" : "content"}>
        {!isLoading && data !== null && data.total_listens === 0 ? (
          <section className="panel">
            <p className="empty-state">
              No DateTime patterns yet. Once more Last.fm listens are imported, this page will
              show when your music habits change.
            </p>
          </section>
        ) : (
          <>
            <section className="stats-grid datetime-summary-grid" aria-busy={isLoading}>
              <StatCard label="Total Listens" value={data?.total_listens ?? 0} />
              <section className="stat-card" aria-label="Most Active Month">
                <span>Most Active Month</span>
                <strong>
                  {data?.most_active_month ? formatMonthLabel(data.most_active_month) : "N/A"}
                </strong>
              </section>
              <section className="stat-card" aria-label="Most Active Day">
                <span>Most Active Day</span>
                <strong>{data?.most_active_day ?? "N/A"}</strong>
              </section>
              <section className="stat-card" aria-label="Most Active Hour">
                <span>Most Active Hour</span>
                <strong>{formatHour(data?.most_active_hour ?? null)}</strong>
              </section>
              <section className="stat-card" aria-label="Highest Energy">
                <span>Highest Energy</span>
                <strong>{data?.highest_energy_bucket ?? "N/A"}</strong>
              </section>
              <section className="stat-card" aria-label="Highest Valence">
                <span>Highest Valence</span>
                <strong>{data?.highest_valence_bucket ?? "N/A"}</strong>
              </section>
            </section>

            <section className="datetime-timeline-grid">
              <section className="panel datetime-timeline-panel">
                <div className="panel-heading">
                  <h2>Monthly Timeline</h2>
                  <span>Listens with energy overlay</span>
                </div>
                {monthly.length ? (
                  <div className="datetime-timeline-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart
                        data={monthly}
                        margin={{ top: 18, right: 16, bottom: 12, left: 0 }}
                      >
                        <CartesianGrid stroke="rgb(255 255 255 / 8%)" />
                        <XAxis
                          dataKey="year_month"
                          tickFormatter={formatMonthLabel}
                          tick={{ fill: "#b7beb8", fontSize: 12 }}
                          stroke="rgb(255 255 255 / 24%)"
                        />
                        <YAxis
                          yAxisId="listens"
                          tick={{ fill: "#b7beb8", fontSize: 12 }}
                          stroke="rgb(255 255 255 / 24%)"
                          allowDecimals={false}
                          hide={hideRealNumbers}
                        />
                        <YAxis
                          yAxisId="energy"
                          orientation="right"
                          domain={[0, 1]}
                          tick={{ fill: "#b7beb8", fontSize: 12 }}
                          stroke="rgb(255 255 255 / 24%)"
                        />
                        <Tooltip content={<TimelineTooltip />} cursor={{ fill: "rgb(255 255 255 / 6%)" }} />
                        <Bar
                          yAxisId="listens"
                          dataKey="total_listens"
                          radius={[6, 6, 0, 0]}
                          maxBarSize={56}
                          onClick={(entry: { payload?: DateTimeMonthBucket }) => {
                            const yearMonth = entry?.payload?.year_month;
                            if (yearMonth) {
                              setSelectedMonth(yearMonth);
                            }
                          }}
                          cursor="pointer"
                        >
                          {monthly.map((bucket) => (
                            <Cell
                              key={bucket.year_month}
                              fill={
                                bucket.year_month === selectedMonth
                                  ? "#54f58b"
                                  : "rgb(84 245 139 / 38%)"
                              }
                            />
                          ))}
                        </Bar>
                        <Line
                          yAxisId="energy"
                          type="monotone"
                          dataKey="avg_energy"
                          name="Energy"
                          stroke="#8cc7ff"
                          strokeWidth={3}
                          dot={{ r: 3, fill: "#8cc7ff" }}
                          connectNulls
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="empty-state">No monthly data yet.</p>
                )}
              </section>

              <MonthDetailPanel
                detail={monthDetail}
                isLoading={isMonthLoading}
                error={monthError}
              />
            </section>

            <section className="panel datetime-day-panel">
              <div className="panel-heading">
                <h2>Day of Week</h2>
                {weekdayWeekend.weekdayEnergy !== null &&
                weekdayWeekend.weekendEnergy !== null ? (
                  <span>
                    {weekdayWeekend.weekendEnergy > weekdayWeekend.weekdayEnergy
                      ? "Weekends run higher energy"
                      : "Weekdays run higher energy"}
                  </span>
                ) : (
                  <span>Mon–Sun breakdown</span>
                )}
              </div>
              {days.length ? (
                <div className="datetime-day-grid">
                  {DAY_ORDER.map((label) => {
                    const day = days.find((item) => item.day_of_week === label);
                    return day ? (
                      <DayCard day={day} maxListens={maxDayListens} key={label} />
                    ) : null;
                  })}
                </div>
              ) : (
                <p className="empty-state">No day-of-week data yet.</p>
              )}
            </section>

            <section className="panel datetime-hour-panel">
              <div className="panel-heading">
                <h2>Hour of Day</h2>
                <span>Listens by hour (local time)</span>
              </div>
              {hours.some((hour) => hour.total_listens > 0) ? (
                <div className="datetime-hour-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={hours} margin={{ top: 18, right: 16, bottom: 12, left: 0 }}>
                      <CartesianGrid stroke="rgb(255 255 255 / 8%)" />
                      <XAxis
                        dataKey="hour"
                        tickFormatter={(hour: number) => formatHour(hour)}
                        interval={2}
                        tick={{ fill: "#b7beb8", fontSize: 11 }}
                        stroke="rgb(255 255 255 / 24%)"
                      />
                      <YAxis
                        tick={{ fill: "#b7beb8", fontSize: 12 }}
                        stroke="rgb(255 255 255 / 24%)"
                        allowDecimals={false}
                        hide={hideRealNumbers}
                      />
                      <Tooltip content={<HourTooltip />} cursor={{ fill: "rgb(255 255 255 / 6%)" }} />
                      <Bar
                        dataKey="total_listens"
                        radius={[5, 5, 0, 0]}
                        fill="rgb(84 245 139 / 60%)"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="empty-state">No hourly data yet.</p>
              )}
            </section>

            <section className="panel datetime-heatmap-panel">
              <div className="panel-heading">
                <h2>Listening Heatmap</h2>
                <div className="weather-viz-controls" aria-label="Heatmap color mode">
                  {HEATMAP_MODES.map((mode) => (
                    <button
                      type="button"
                      className={heatmapMode === mode ? "active" : ""}
                      key={mode}
                      onClick={() => setHeatmapMode(mode)}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
              {hasData ? (
                <div className="datetime-heatmap">
                  <div className="datetime-heatmap-head" aria-hidden="true">
                    <span />
                    {Array.from({ length: 24 }, (_, hour) => (
                      <strong key={hour}>{hour}</strong>
                    ))}
                  </div>
                  {DAY_ORDER.map((day) => (
                    <div className="datetime-heatmap-row" key={day}>
                      <strong>{day}</strong>
                      {Array.from({ length: 24 }, (_, hour) => {
                        const cell = heatmapByCell.get(`${day}-${hour}`);
                        const safeCell: DateTimeHeatmapCell = cell ?? {
                          day_of_week: day,
                          hour,
                          total_listens: 0,
                          avg_valence: null,
                          avg_energy: null,
                          dominant_mood: null,
                        };
                        const intensity = heatmapIntensity(safeCell, heatmapMode, maxHeatmapListens);
                        const style: CSSProperties =
                          heatmapMode === "mood"
                            ? {
                                background:
                                  safeCell.total_listens === 0
                                    ? "rgb(255 255 255 / 4%)"
                                    : moodColor(safeCell.dominant_mood),
                                opacity: safeCell.total_listens === 0 ? 1 : 0.85,
                              }
                            : ({ "--heat": intensity } as CSSProperties);
                        return (
                          <div
                            className={
                              heatmapMode === "mood"
                                ? "datetime-heatmap-cell mood"
                                : "datetime-heatmap-cell"
                            }
                            key={hour}
                            style={style}
                            title={`${day} ${formatHour(hour)} · ${formatCount(
                              safeCell.total_listens,
                              "listens",
                            )} · ${safeCell.dominant_mood ?? "unclassified"} · Valence ${formatScore(
                              safeCell.avg_valence,
                            )} · Energy ${formatScore(safeCell.avg_energy)}`}
                          />
                        );
                      })}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">No heatmap data yet.</p>
              )}
              {heatmapMode === "mood" ? (
                <div className="datetime-heatmap-legend">
                  {Object.entries(MOOD_COLORS).map(([mood, color]) => (
                    <span key={mood}>
                      <i style={{ background: color }} />
                      {mood}
                    </span>
                  ))}
                </div>
              ) : null}
            </section>
          </>
        )}
      </div>
    </>
  );
}
