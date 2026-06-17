import type { CSSProperties } from "react";
import { useEffect } from "react";
import { formatCount } from "../privacy";
import { AnimatedNumber } from "./AnimatedNumber";
import { ImageThumbnail } from "./ImageThumbnail";
// pagination removed: TopList now renders all items passed to it

interface TopListItem {
  id: string;
  name: string;
  subtitle?: string;
  count: number;
  imageUrl?: string | null;
  imageKind?: "album" | "artist";
}

interface TopListProps {
  title: string;
  items: TopListItem[];
  countLabel: string;
  className?: string;
  variant?: "default" | "media";
  showCountLabel?: boolean;
  pageSize?: number;
}

export function TopList({
  title,
  items,
  countLabel,
  className = "",
  variant = "default",
  showCountLabel = false,
  pageSize = 3,
}: TopListProps) {
  useEffect(() => {
    // placeholder: items or pageSize changed
  }, [items, pageSize]);

  const visibleItems = items;

  return (
    <section className={`panel ${className}`.trim()}>
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="empty-state">No data yet</p>
      ) : (
        <>
          <ol className={variant === "media" ? "top-list top-list-media" : "top-list"}>
            {visibleItems.map((item, index) => (
              <li key={item.id} style={{ "--row-index": index } as CSSProperties}>
                {variant === "media" ? (
                  <ImageThumbnail
                    src={item.imageUrl}
                    className={
                      item.imageKind === "artist"
                        ? "top-list-artwork top-list-artist-image"
                        : "top-list-artwork"
                    }
                  />
                ) : null}
                <div className="top-list-copy">
                  <span>{item.name}</span>
                  {item.subtitle ? <small>{item.subtitle}</small> : null}
                </div>
                <strong className="top-list-count" aria-label={formatCount(item.count, countLabel)}>
                  <span>
                    <AnimatedNumber value={item.count} formatter={formatCount} />
                  </span>
                  {showCountLabel ? <small>{countLabel}</small> : null}
                </strong>
              </li>
            ))}
          </ol>
          {/* pagination removed - render full list */}
        </>
      )}
    </section>
  );
}
