import type { Period } from "../types";

const PERIODS: { value: Period; label: string }[] = [
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "6m", label: "6m" },
  { value: "all", label: "All Time" },
];

interface PeriodSelectorProps {
  value: Period;
  onChange: (value: Period) => void;
}

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <div className="period-selector" role="tablist" aria-label="Listening period">
      {PERIODS.map((period) => (
        <button
          key={period.value}
          type="button"
          className={period.value === value ? "period-button active" : "period-button"}
          onClick={() => onChange(period.value)}
          aria-selected={period.value === value}
          role="tab"
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}
