interface TopListItem {
  id: string;
  name: string;
  subtitle?: string;
  count: number;
}

interface TopListProps {
  title: string;
  items: TopListItem[];
  countLabel: string;
}

export function TopList({ title, items, countLabel }: TopListProps) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="empty-state">No data yet</p>
      ) : (
        <ol className="top-list">
          {items.map((item) => (
            <li key={item.id}>
              <div className="top-list-copy">
                <span>{item.name}</span>
                {item.subtitle ? <small>{item.subtitle}</small> : null}
              </div>
              <strong aria-label={`${item.count} ${countLabel}`}>
                {item.count.toLocaleString()}
              </strong>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
