import { useEffect, useMemo, useState } from "react";
import { fetchWeatherCorrelation } from "../api";
import type { Period, WeatherCorrelationResponse, WeatherSummary } from "../types";
import { PeriodSelector } from "./PeriodSelector";
import { StatCard } from "./StatCard";

interface WeatherViewProps {
  period: Period;
  onPeriodChange: (period: Period) => void;
}

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

function SummaryList({
  title,
  summaries,
}: {
  title: string;
  summaries: WeatherSummary[];
}) {
  const maxListens = Math.max(...summaries.map((item) => item.total_listens), 1);

  return (
    <section className="panel weather-summary-panel">
      <h2>{title}</h2>
      {summaries.length === 0 ? (
        <p className="empty-state">No weather data yet</p>
      ) : (
        <div className="weather-summary-list">
          {summaries.map((summary) => (
            <article className="weather-summary-row" key={summary.label}>
              <div className="weather-row-main">
                <strong>{summary.label}</strong>
                <span>{summary.total_listens.toLocaleString()} listens</span>
              </div>
              <div className="weather-meter" aria-hidden="true">
                <span style={{ width: `${(summary.total_listens / maxListens) * 100}%` }} />
              </div>
              <div className="weather-row-meta">
                <span>{summary.total_days} days</span>
                <span>{formatNumber(summary.avg_temp_c, "C")} avg</span>
                <span>{formatNumber(summary.total_precipitation, "mm")} precip</span>
                <span>{formatMoodScore(summary.avg_mood_score)}</span>
              </div>
              {summary.top_tags.length ? (
                <div className="tag-strip">
                  {summary.top_tags.slice(0, 5).map((tag) => (
                    <span key={tag.tag}>
                      {tag.tag} ({tag.listen_count.toLocaleString()})
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
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

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchWeatherCorrelation(period)
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

  const totals = useMemo(() => {
    const daily = data?.daily_data ?? [];
    const listens = daily.reduce((sum, day) => sum + day.total_listens, 0);
    const wetDays = daily.filter((day) => day.had_precipitation).length;
    const daysWithTemp = daily.filter((day) => day.temp_c !== null);
    const avgTemp =
      daysWithTemp.length === 0
        ? null
        : daysWithTemp.reduce((sum, day) => sum + (day.temp_c ?? 0), 0) /
          daysWithTemp.length;
    return {
      listens,
      weatherDays: daily.length,
      wetDays,
      avgTemp: Number.isFinite(avgTemp) ? avgTemp : null,
    };
  }, [data]);

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
          <StatCard label="Wet Days" value={totals.wetDays} />
        </section>

        <section className="weather-note">
          <strong>{formatNumber(totals.avgTemp, "C")}</strong>
          <span>
            {data?.weather_city ?? "Weather"} average temperature across matched listening days.
          </span>
        </section>

        <section className="weather-grid">
          <SummaryList title="By Weather" summaries={data?.summary_by_weather ?? []} />
          <SummaryList title="By Temperature" summaries={data?.summary_by_temperature ?? []} />
          <SummaryList title="By Season" summaries={data?.summary_by_season ?? []} />
        </section>

        <section className="panel weather-daily-panel">
          <h2>Daily Weather + Listening</h2>
          {data?.daily_data.length ? (
            <div className="weather-daily-table">
              <div className="weather-daily-row weather-daily-head">
                <span>Date</span>
                <span>Weather</span>
                <span>Temp</span>
                <span>Precip</span>
                <span>Listens</span>
                <span>Mood</span>
              </div>
              {data.daily_data.slice(-30).reverse().map((day) => (
                <div className="weather-daily-row" key={day.date}>
                  <strong>{day.date}</strong>
                  <span>{day.weather_category}</span>
                  <span>{formatNumber(day.temp_c, "C")}</span>
                  <span>{formatNumber(day.precipitation, "mm")}</span>
                  <span>{day.total_listens.toLocaleString()}</span>
                  <span>{formatMoodScore(day.mood_score)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">No joined weather/listening days yet</p>
          )}
        </section>
      </div>
    </>
  );
}
