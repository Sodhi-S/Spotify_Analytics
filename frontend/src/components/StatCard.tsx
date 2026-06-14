import { AnimatedNumber } from "./AnimatedNumber";
import { formatCount } from "../privacy";

interface StatCardProps {
  label: string;
  value: number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <section className="stat-card" aria-label={label}>
      <span>{label}</span>
      <strong>
        <AnimatedNumber value={value} formatter={formatCount} />
      </strong>
    </section>
  );
}
