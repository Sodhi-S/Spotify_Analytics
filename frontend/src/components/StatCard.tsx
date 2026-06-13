interface StatCardProps {
  label: string;
  value: number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <section className="stat-card" aria-label={label}>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </section>
  );
}
