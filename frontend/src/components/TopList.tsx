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
  className?: string;
  variant?: "default" | "media";
  showCountLabel?: boolean;
}

export function TopList({
  title,
  items,
  countLabel,
  className = "",
  variant = "default",
  showCountLabel = false,
}: TopListProps) {
  return (
    <section className={`panel ${className}`.trim()}>
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="empty-state">No data yet</p>
      ) : (
        <ol className={variant === "media" ? "top-list top-list-media" : "top-list"}>
          {items.map((item) => (
            <li key={item.id}>
              {variant === "media" ? <div className="top-list-artwork" aria-hidden="true" /> : null}
              <div className="top-list-copy">
                <span>{item.name}</span>
                {item.subtitle ? <small>{item.subtitle}</small> : null}
              </div>
              <strong className="top-list-count" aria-label={`${item.count} ${countLabel}`}>
                <span>{item.count.toLocaleString()}</span>
                {showCountLabel ? <small>{countLabel}</small> : null}
              </strong>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
