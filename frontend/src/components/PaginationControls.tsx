interface PaginationControlsProps {
  page: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  label: string;
}

export function pageCount(totalItems: number, pageSize: number) {
  return Math.max(1, Math.ceil(totalItems / pageSize));
}

export function pageItems<T>(items: T[], page: number, pageSize: number) {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function PaginationControls({
  page,
  pageSize,
  totalItems,
  onPageChange,
  label,
}: PaginationControlsProps) {
  if (totalItems <= pageSize) {
    return null;
  }

  const totalPages = pageCount(totalItems, pageSize);
  const safePage = Math.min(page, totalPages);

  return (
    <nav className="pagination-controls" aria-label={label}>
      <button
        type="button"
        onClick={() => onPageChange(Math.max(1, safePage - 1))}
        disabled={safePage <= 1}
      >
        Prev
      </button>
      <span>
        {safePage} / {totalPages}
      </span>
      <button
        type="button"
        onClick={() => onPageChange(Math.min(totalPages, safePage + 1))}
        disabled={safePage >= totalPages}
      >
        Next
      </button>
    </nav>
  );
}
