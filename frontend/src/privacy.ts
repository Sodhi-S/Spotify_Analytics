export const hideRealNumbers = import.meta.env.VITE_HIDE_REAL_NUMBERS === "true";

export function formatCount(value: number, label?: string) {
  if (hideRealNumbers) {
    return label ? `Hidden ${label}` : "Hidden";
  }
  const formatted = value.toLocaleString();
  return label ? `${formatted} ${label}` : formatted;
}

export function formatDuration(ms: number) {
  if (hideRealNumbers) {
    return "Hidden";
  }
  if (!ms) {
    return "0m";
  }
  const minutes = Math.round(ms / 60000);
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours === 0) {
    return `${minutes}m`;
  }
  return `${hours}h ${remainingMinutes}m`;
}
