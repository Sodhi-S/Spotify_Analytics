import type { Period } from "../types";
import { MoodDonutChart } from "./MoodDonutChart";
import { PeriodSelector } from "./PeriodSelector";

interface MoodsViewProps {
  period: Period;
  onPeriodChange: (period: Period) => void;
  moodBreakdown: Record<string, number>;
  isLoading: boolean;
  error: string | null;
}

export function MoodsView({
  period,
  onPeriodChange,
  moodBreakdown,
  isLoading,
  error,
}: MoodsViewProps) {
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

      <div className={isLoading ? "content loading" : "content"}>
        <section className="moods-page-grid">
          <MoodDonutChart moodBreakdown={moodBreakdown} />
        </section>
      </div>
    </>
  );
}
