import type { CSSProperties } from "react";
import { useEffect, useState } from "react";
import { formatCount } from "../privacy";
import { AnimatedNumber } from "./AnimatedNumber";
import { ImageThumbnail } from "./ImageThumbnail";
import { pageCount, pageItems, PaginationControls } from "./PaginationControls";

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
  const [page, setPage] = useState(1);
  const totalPages = pageCount(items.length, pageSize);
  const visibleItems = pageItems(items, Math.min(page, totalPages), pageSize);

  useEffect(() => {
    setPage(1);
  }, [items, pageSize]);

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
          <PaginationControls
            page={page}
            pageSize={pageSize}
            totalItems={items.length}
            onPageChange={setPage}
            label={`${title} pages`}
          />
        </>
      )}
    </section>
  );
}
