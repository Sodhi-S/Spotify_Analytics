import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { formatCount } from "../privacy";
import { AnimatedNumber } from "./AnimatedNumber";

const MOOD_COLORS: Record<string, string> = {
  happy: "#54f58b",
  sad: "#4b7cff",
  angry: "#ff5f6d",
  calm: "#4da3ff",
  energetic: "#f7c843",
  melancholic: "#6e756f",
  unclassified: "#54f58b",
};

const MOOD_ORDER = [
  "happy",
  "sad",
  "angry",
  "calm",
  "energetic",
  "melancholic",
  "unclassified",
];

interface MoodDonutChartProps {
  moodBreakdown: Record<string, number>;
}

interface MoodTooltipProps {
  active?: boolean;
  payload?: {
    payload: {
      name: string;
      value: number;
      percent: number;
    };
  }[];
}

function MoodTooltip({ active, payload }: MoodTooltipProps) {
  if (!active || !payload?.length) {
    return null;
  }

  const item = payload[0].payload as { name: string; value: number; percent: number };
  return (
    <div className="chart-tooltip">
      <strong>{item.name}</strong>
      <span>
        {formatCount(item.value, "listens")} · {(item.percent * 100).toFixed(1)}%
      </span>
    </div>
  );
}

export function MoodDonutChart({ moodBreakdown }: MoodDonutChartProps) {
  const total = Object.values(moodBreakdown).reduce((sum, count) => sum + count, 0);
  const classifiedTotal = Object.entries(moodBreakdown)
    .filter(([label]) => label !== "unclassified")
    .reduce((sum, [, count]) => sum + count, 0);

  const data = MOOD_ORDER.map((name) => {
    const value = moodBreakdown[name] ?? 0;
    return {
      name,
      value,
      percent: total > 0 ? value / total : 0,
    };
  }).filter((item) => item.value > 0);

  return (
    <section className="panel mood-panel">
      <div className="panel-heading">
        <h2>Mood Breakdown</h2>
        <span>
          <AnimatedNumber
            value={classifiedTotal}
            formatter={(value) => formatCount(value, "classified")}
          />
        </span>
      </div>

      {data.length === 0 ? (
        <p className="empty-state">No mood data yet</p>
      ) : (
        <div className="mood-chart-grid">
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="58%"
                  outerRadius="82%"
                  paddingAngle={2}
                  stroke="#101411"
                  strokeWidth={2}
                >
                  {data.map((entry) => (
                    <Cell key={entry.name} fill={MOOD_COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip content={<MoodTooltip />} />
                <text
                  x="50%"
                  y="48%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="chart-center-value"
                >
                  <AnimatedNumber value={classifiedTotal} formatter={formatCount} />
                </text>
                <text
                  x="50%"
                  y="58%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="chart-center-label"
                >
                  classified
                </text>
              </PieChart>
            </ResponsiveContainer>
          </div>

          <ul className="mood-legend">
            {MOOD_ORDER.map((mood) => (
              <li key={mood}>
                <span className="legend-swatch" style={{ background: MOOD_COLORS[mood] }} />
                <span>{mood}</span>
                <strong>
                  <AnimatedNumber value={moodBreakdown[mood] ?? 0} formatter={formatCount} />
                </strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
