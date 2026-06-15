import type { CSSProperties, WheelEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { fetchWeatherCorrelation } from "../api";
import { formatCount, hideRealNumbers } from "../privacy";
import type {
  Period,
  TemperatureMoodTrend,
  WeatherCorrelationResponse,
  WeatherMoodPoint,
  WeatherSummary,
} from "../types";
import { AnimatedNumber } from "./AnimatedNumber";
import { PeriodSelector } from "./PeriodSelector";
import { StatCard } from "./StatCard";

interface WeatherViewProps {
  period: Period;
  onPeriodChange: (period: Period) => void;
}

type HeatmapMode = "percentage" | "minutes" | "streams";
type MoodDomain = [number, number];

const MOOD_QUADRANTS = ["Happy / Hype", "Calm / Chill", "Sad / Reflective", "Intense / Dark"];
const DEFAULT_DOMAIN: MoodDomain = [0, 1];
const MIN_FITTED_DOMAIN_WIDTH = 0.22;

function formatNumber(value: number | null, suffix = "") {
  if (value === null || Number.isNaN(value)) {
    return "N/A";
  }
  return `${value.toFixed(1)}${suffix}`;
}

function formatMoodScore(value: number | null) {
  if (value === null) {
    return "Pending mood model";
  }
  return `${(value * 100).toFixed(0)}%`;
}

function formatScore(value: number | null) {
  return value === null ? "N/A" : value.toFixed(2);
}

function formatAxisTick(value: number) {
  return Number(value.toFixed(2)).toString();
}

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

function fitDomainToValues(values: number[]): MoodDomain {
  const validValues = values.filter((value) => Number.isFinite(value));
  if (!validValues.length) {
    return DEFAULT_DOMAIN;
  }

  const min = Math.min(...validValues);
  const max = Math.max(...validValues);
  const span = max - min;
  const paddedWidth = Math.max(
    span + Math.max(span * 0.7, 0.08),
    MIN_FITTED_DOMAIN_WIDTH,
  );
  const width = Math.min(paddedWidth, 1);
  const center = (min + max) / 2;
  return clampDomain([center - width / 2, center + width / 2]);
}

function domainsEqual(left: MoodDomain, right: MoodDomain) {
  return Math.abs(left[0] - right[0]) < 0.0001 && Math.abs(left[1] - right[1]) < 0.0001;
}

function weatherMapDomains(response: WeatherCorrelationResponse | null): {
  x: MoodDomain;
  y: MoodDomain;
} {
  if (!response?.weather_mood_points.length) {
    return { x: DEFAULT_DOMAIN, y: DEFAULT_DOMAIN };
  }

  const points = [
    ...response.weather_mood_points,
    ...(response.mood_baseline.avg_valence !== null && response.mood_baseline.avg_energy !== null
      ? [
          {
            avg_valence: response.mood_baseline.avg_valence,
            avg_energy: response.mood_baseline.avg_energy,
          },
        ]
      : []),
  ];

  return {
    x: fitDomainToValues(points.map((point) => point.avg_valence)),
    y: fitDomainToValues(points.map((point) => point.avg_energy)),
  };
}

function heatmapValue(
  cell: WeatherCorrelationResponse["weather_mood_heatmap"][number],
  mode: HeatmapMode,
) {
  if (mode === "percentage") return cell.percentage;
  if (mode === "minutes") return cell.listening_minutes;
  return cell.stream_count;
}

function formatHeatmapValue(value: number, mode: HeatmapMode) {
  if (mode === "percentage") return `${Math.round(value * 100)}%`;
  if (mode === "minutes") return `${Math.round(value)} min`;
  return formatCount(value, "streams");
}

interface WeatherPointTooltipProps {
  active?: boolean;
  payload?: {
    payload: (WeatherMoodPoint & { display_weight: number }) | {
      weather_category: string;
      avg_valence: number | null;
      avg_energy: number | null;
      dominant_mood_quadrant: string;
      top_artist_name: string | null;
      stream_count: number;
      listening_minutes: number;
    };
  }[];
}

interface TemperatureTooltipProps {
  active?: boolean;
  payload?: {
    payload: TemperatureMoodTrend;
  }[];
}

function WeatherPointTooltip({ active, payload }: WeatherPointTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{point.weather_category}</strong>
      <span>{point.dominant_mood_quadrant}</span>
      <span>
        Valence {formatScore(point.avg_valence)} · Energy {formatScore(point.avg_energy)}
      </span>
      <span>
        {formatCount(point.stream_count, "streams")} · {Math.round(point.listening_minutes)} min
      </span>
      {point.top_artist_name ? <span>Top artist: {point.top_artist_name}</span> : null}
    </div>
  );
}

function TemperatureTooltip({ active, payload }: TemperatureTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }
  const bucket = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{bucket.temperature_bucket}</strong>
      <span>
        Valence {formatScore(bucket.avg_valence)} · Energy {formatScore(bucket.avg_energy)}
      </span>
      <span>
        {formatCount(bucket.stream_count, "streams")} · {Math.round(bucket.listening_minutes)} min
      </span>
    </div>
  );
}

function WeatherSummaryCard({
  summary,
  index,
  maxListens,
}: {
  summary: WeatherSummary;
  index: number;
  maxListens: number;
}) {
  return (
    <article
      className="weather-summary-card"
      key={summary.label}
      style={{ "--row-index": index } as CSSProperties}
    >
      <div className="weather-row-main">
        <strong>{summary.label}</strong>
        <span>
          <AnimatedNumber
            value={summary.total_listens}
            formatter={(value) => formatCount(value, "listens")}
          />
        </span>
      </div>
      <div className="weather-meter" aria-hidden="true">
        <span
          style={{
            width: hideRealNumbers ? "100%" : `${(summary.total_listens / maxListens) * 100}%`,
          }}
        />
      </div>
      <div className="weather-row-meta">
        <span>{summary.total_days} days</span>
        <span>{formatNumber(summary.avg_temp_c, "C")} avg</span>
        <span>{formatNumber(summary.total_precipitation, "mm")} precip</span>
        <span>{formatMoodScore(summary.avg_mood_score)}</span>
      </div>
      {summary.top_tags.length ? (
        <div className="tag-strip">
          {summary.top_tags.slice(0, 3).map((tag) => (
            <span key={tag.tag}>
              {tag.tag} (<AnimatedNumber value={tag.listen_count} formatter={formatCount} />)
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function WeatherSummaryPreview({
  title,
  summaries,
  onSeeMore,
}: {
  title: string;
  summaries: WeatherSummary[];
  onSeeMore: () => void;
}) {
  const maxListens = hideRealNumbers
    ? 1
    : Math.max(...summaries.map((item) => item.total_listens), 1);

  return (
    <section className="panel weather-summary-panel weather-summary-preview-panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {summaries.length > 2 ? (
          <button type="button" className="weather-summary-more-button" onClick={onSeeMore}>
            See more
          </button>
        ) : null}
      </div>
      {summaries.length === 0 ? (
        <p className="empty-state">No weather data yet</p>
      ) : (
        <div className="weather-summary-list">
          {summaries.slice(0, 2).map((summary, index) => (
            <WeatherSummaryCard
              summary={summary}
              index={index}
              maxListens={maxListens}
              key={summary.label}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export function WeatherView({ period, onPeriodChange }: WeatherViewProps) {
  const [data, setData] = useState<WeatherCorrelationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heatmapMode, setHeatmapMode] = useState<HeatmapMode>("percentage");
  const [isWeatherSummaryModalOpen, setIsWeatherSummaryModalOpen] = useState(false);
  const [xDomain, setXDomain] = useState<MoodDomain>(DEFAULT_DOMAIN);
  const [yDomain, setYDomain] = useState<MoodDomain>(DEFAULT_DOMAIN);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setXDomain(DEFAULT_DOMAIN);
    setYDomain(DEFAULT_DOMAIN);

    fetchWeatherCorrelation(period)
      .then((response) => {
        if (!cancelled) {
          const fittedDomains = weatherMapDomains(response);
          setXDomain(fittedDomains.x);
          setYDomain(fittedDomains.y);
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
    if (!isWeatherSummaryModalOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsWeatherSummaryModalOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isWeatherSummaryModalOpen]);

  const totals = useMemo(() => {
    const daily = data?.daily_data ?? [];
    const listens = daily.reduce((sum, day) => sum + day.total_listens, 0);
    const daysWithTemp = daily.filter((day) => day.temp_c !== null);
    const avgTemp =
      daysWithTemp.length === 0
        ? null
        : daysWithTemp.reduce((sum, day) => sum + (day.temp_c ?? 0), 0) /
          daysWithTemp.length;
    return {
      listens,
      weatherDays: daily.length,
      avgTemp: Number.isFinite(avgTemp) ? avgTemp : null,
    };
  }, [data]);

  const weatherPointData = useMemo(
    () =>
      data?.weather_mood_points.map((point) => ({
        ...point,
        display_weight: hideRealNumbers ? 1 : point.stream_count,
      })) ?? [],
    [data],
  );

  const baselinePoint = useMemo(() => {
    if (
      data?.mood_baseline.avg_valence === null ||
      data?.mood_baseline.avg_energy === null ||
      data === null
    ) {
      return [];
    }
    return [
      {
        weather_category: "Overall average",
        avg_valence: data.mood_baseline.avg_valence,
        avg_energy: data.mood_baseline.avg_energy,
        dominant_mood_quadrant: "Baseline",
        top_artist_name: null,
        stream_count: data.mood_baseline.total_listens,
        listening_minutes: data.mood_baseline.listening_minutes,
        display_weight: hideRealNumbers ? 1 : data.mood_baseline.total_listens,
      },
    ];
  }, [data]);

  const heatmapRows = useMemo(() => {
    const labels = [...new Set((data?.weather_mood_heatmap ?? []).map((cell) => cell.weather_category))];
    const values = data?.weather_mood_heatmap ?? [];
    const maxValue = Math.max(...values.map((cell) => heatmapValue(cell, heatmapMode)), 0.01);
    return labels.map((label) => ({
      label,
      cells: MOOD_QUADRANTS.map((quadrant) => {
        const cell = values.find(
          (item) => item.weather_category === label && item.mood_quadrant === quadrant,
        );
        const value = cell ? heatmapValue(cell, heatmapMode) : 0;
        return {
          quadrant,
          cell,
          value,
          intensity: value / maxValue,
        };
      }),
    }));
  }, [data, heatmapMode]);

  const strongestHeatmapCell = data?.weather_mood_heatmap.find((cell) => cell.is_strongest);
  const baselineAvgValence = data?.mood_baseline.avg_valence ?? null;
  const baselineAvgEnergy = data?.mood_baseline.avg_energy ?? null;
  const weatherSummaryMaxListens = hideRealNumbers
    ? 1
    : Math.max(...(data?.summary_by_weather ?? []).map((item) => item.total_listens), 1);
  const fittedWeatherMapDomains = weatherMapDomains(data);
  const isWeatherMapZoomed =
    !domainsEqual(xDomain, fittedWeatherMapDomains.x) ||
    !domainsEqual(yDomain, fittedWeatherMapDomains.y);

  function handleWeatherMapZoom(direction: "in" | "out") {
    setXDomain((domain) => zoomDomain(domain, direction));
    setYDomain((domain) => zoomDomain(domain, direction));
  }

  function resetWeatherMapZoom() {
    setXDomain(fittedWeatherMapDomains.x);
    setYDomain(fittedWeatherMapDomains.y);
  }

  function handleWeatherMapWheel(event: WheelEvent<HTMLDivElement>) {
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
          <h1>Weather</h1>
        </div>
        <PeriodSelector value={period} onChange={onPeriodChange} />
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <div className={isLoading ? "content loading" : "content"}>
        <section className="stats-grid" aria-busy={isLoading}>
          <StatCard label="Weather Days" value={totals.weatherDays} />
          <StatCard label="Total Listens" value={totals.listens} />
          <section className="stat-card" aria-label="Avg Temperature">
            <span>Avg Temperature</span>
            <strong>{totals.avgTemp === null ? "N/A" : `${totals.avgTemp.toFixed(1)}C`}</strong>
          </section>
        </section>

        <section className="weather-map-summary-grid">
          <section className="panel weather-quadrant-panel">
            <div className="panel-heading">
              <h2>Weather Mood Map</h2>
              <div className="mood-map-controls" aria-label="Weather mood map zoom controls">
                <span>{weatherPointData.length} conditions</span>
                <button
                  type="button"
                  onClick={() => handleWeatherMapZoom("out")}
                  disabled={!isWeatherMapZoomed}
                >
                  -
                </button>
                <button type="button" onClick={() => handleWeatherMapZoom("in")}>
                  +
                </button>
                <button type="button" onClick={resetWeatherMapZoom} disabled={!isWeatherMapZoomed}>
                  Reset
                </button>
              </div>
            </div>
            {weatherPointData.length ? (
              <div className="mood-map-frame weather-map-frame" onWheel={handleWeatherMapWheel}>
                <div className="mood-quadrant-label mood-quadrant-calm">calm / chill</div>
                <div className="mood-quadrant-label mood-quadrant-hype">happy / hype</div>
                <div className="mood-quadrant-label mood-quadrant-heavy">intense / dark</div>
                <div className="mood-quadrant-label mood-quadrant-soft">sad / reflective</div>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 18, right: 20, bottom: 20, left: 0 }}>
                    <CartesianGrid stroke="rgb(255 255 255 / 8%)" />
                    <XAxis
                      type="number"
                      dataKey="avg_valence"
                      domain={xDomain}
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      tickFormatter={formatAxisTick}
                      stroke="rgb(255 255 255 / 24%)"
                      label={{
                        value: "Valence",
                        position: "insideBottom",
                        offset: -10,
                        fill: "#b7beb8",
                        fontSize: 12,
                      }}
                    />
                    <YAxis
                      type="number"
                      dataKey="avg_energy"
                      domain={yDomain}
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      tickFormatter={formatAxisTick}
                      stroke="rgb(255 255 255 / 24%)"
                      label={{
                        value: "Energy",
                        angle: -90,
                        position: "insideLeft",
                        fill: "#b7beb8",
                        fontSize: 12,
                      }}
                    />
                    <ZAxis type="number" dataKey="display_weight" range={[110, 230]} />
                    <ReferenceLine x={0.5} stroke="rgb(84 245 139 / 24%)" />
                    <ReferenceLine y={0.5} stroke="rgb(84 245 139 / 24%)" />
                    {baselineAvgValence !== null ? (
                      <ReferenceLine
                        x={baselineAvgValence}
                        stroke="rgb(255 255 255 / 18%)"
                        strokeDasharray="4 4"
                      />
                    ) : null}
                    {baselineAvgEnergy !== null ? (
                      <ReferenceLine
                        y={baselineAvgEnergy}
                        stroke="rgb(255 255 255 / 18%)"
                        strokeDasharray="4 4"
                      />
                    ) : null}
                    <Tooltip content={<WeatherPointTooltip />} />
                    <Scatter data={weatherPointData} fill="#54f58b">
                      <LabelList
                        dataKey="weather_category"
                        position="top"
                        className="weather-map-point-label"
                      />
                    </Scatter>
                    <Scatter data={baselinePoint} fill="#ffffff">
                      <LabelList
                        dataKey="weather_category"
                        position="bottom"
                        className="weather-map-baseline-label"
                      />
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="empty-state">No weather mood points yet.</p>
            )}
          </section>

          <WeatherSummaryPreview
            title="By Weather"
            summaries={data?.summary_by_weather ?? []}
            onSeeMore={() => setIsWeatherSummaryModalOpen(true)}
          />
        </section>

        <section className="weather-analytics-grid">
          <section className="panel weather-heatmap-panel">
            <div className="panel-heading">
              <h2>Weather vs Mood</h2>
              <div className="weather-viz-controls" aria-label="Heatmap value mode">
                {(["percentage", "minutes", "streams"] as HeatmapMode[]).map((mode) => (
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
            {data?.weather_mood_heatmap.length ? (
              <>
                <p className="weather-panel-callout">
                  {strongestHeatmapCell
                    ? `${strongestHeatmapCell.weather_category} is strongest for ${strongestHeatmapCell.mood_quadrant}.`
                    : "Your weather moods are ready to compare."}
                </p>
                <div className="weather-heatmap">
                  <div className="weather-heatmap-head" aria-hidden="true">
                    <span />
                    {MOOD_QUADRANTS.map((quadrant) => (
                      <strong key={quadrant}>{quadrant}</strong>
                    ))}
                  </div>
                  {heatmapRows.map((row) => (
                    <div className="weather-heatmap-row" key={row.label}>
                      <strong>{row.label}</strong>
                      {row.cells.map(({ quadrant, cell, value, intensity }) => (
                        <div
                          className={cell?.is_strongest ? "weather-heatmap-cell strongest" : "weather-heatmap-cell"}
                          key={quadrant}
                          style={{ "--heat": intensity } as CSSProperties}
                          title={`${row.label} · ${quadrant}: ${formatHeatmapValue(value, heatmapMode)}`}
                        >
                          <span>{formatHeatmapValue(value, heatmapMode)}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state">No weather mood heatmap yet.</p>
            )}
          </section>

          <section className="panel weather-temperature-panel">
            <div className="panel-heading">
              <h2>Temperature vs Mood</h2>
              <span>{data?.temperature_mood_callout ?? "Valence and energy by bucket"}</span>
            </div>
            {data?.temperature_mood_trends.length ? (
              <div className="weather-temperature-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.temperature_mood_trends} margin={{ top: 18, right: 24, bottom: 12, left: 0 }}>
                    <CartesianGrid stroke="rgb(255 255 255 / 8%)" />
                    <XAxis
                      dataKey="temperature_bucket"
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      stroke="rgb(255 255 255 / 24%)"
                    />
                    <YAxis
                      domain={[0, 1]}
                      tick={{ fill: "#b7beb8", fontSize: 12 }}
                      stroke="rgb(255 255 255 / 24%)"
                    />
                    <Tooltip content={<TemperatureTooltip />} />
                    <Line
                      type="monotone"
                      dataKey="avg_valence"
                      name="Valence"
                      stroke="#54f58b"
                      strokeWidth={3}
                      dot={{ r: 4, fill: "#54f58b" }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="avg_energy"
                      name="Energy"
                      stroke="#8cc7ff"
                      strokeWidth={3}
                      dot={{ r: 4, fill: "#8cc7ff" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="empty-state">No temperature mood trend yet.</p>
            )}
            {data?.temperature_mood_trends.length ? (
              <div className="weather-temperature-badges">
                {data.temperature_mood_trends
                  .filter((bucket) => bucket.is_highest_valence || bucket.is_highest_energy)
                  .map((bucket) => (
                    <span key={`${bucket.temperature_bucket}-${bucket.is_highest_valence ? "valence" : "energy"}`}>
                      {bucket.temperature_bucket}:{" "}
                      {bucket.is_highest_valence ? "highest valence" : "highest energy"}
                    </span>
                  ))}
              </div>
            ) : null}
          </section>
        </section>

        {isWeatherSummaryModalOpen ? (
          <div
            className="weather-summary-modal-backdrop"
            role="presentation"
            onClick={() => setIsWeatherSummaryModalOpen(false)}
          >
            <section
              className="weather-summary-modal panel"
              role="dialog"
              aria-modal="true"
              aria-labelledby="weather-summary-modal-title"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="panel-heading">
                <h2 id="weather-summary-modal-title">All Weather Types</h2>
                <button
                  type="button"
                  className="weather-summary-more-button"
                  onClick={() => setIsWeatherSummaryModalOpen(false)}
                >
                  Close
                </button>
              </div>
              {data?.summary_by_weather.length ? (
                <div className="weather-summary-modal-grid">
                  {data.summary_by_weather.map((summary, index) => (
                    <WeatherSummaryCard
                      summary={summary}
                      index={index}
                      maxListens={weatherSummaryMaxListens}
                      key={summary.label}
                    />
                  ))}
                </div>
              ) : (
                <p className="empty-state">No weather data yet</p>
              )}
            </section>
          </div>
        ) : null}
      </div>
    </>
  );
}
