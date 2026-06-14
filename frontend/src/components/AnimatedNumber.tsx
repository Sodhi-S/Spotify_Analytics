import { useEffect, useMemo, useState } from "react";
import { hideRealNumbers } from "../privacy";

interface AnimatedNumberProps {
  value: number;
  durationMs?: number;
  formatter?: (value: number) => string;
  decimals?: number;
}

const DEFAULT_DURATION_MS = 850;

function easeOutQuint(progress: number) {
  return 1 - Math.pow(1 - progress, 5);
}

export function AnimatedNumber({
  value,
  durationMs = DEFAULT_DURATION_MS,
  formatter,
  decimals = 0,
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const safeValue = Number.isFinite(value) ? value : 0;
  const format = useMemo(
    () =>
      formatter ??
      ((current: number) =>
        current.toLocaleString(undefined, {
          maximumFractionDigits: decimals,
          minimumFractionDigits: decimals,
        })),
    [decimals, formatter],
  );

  useEffect(() => {
    if (hideRealNumbers) {
      setDisplayValue(safeValue);
      return;
    }

    let frameId = 0;
    const startedAt = performance.now();

    const tick = (timestamp: number) => {
      const progress = Math.min((timestamp - startedAt) / durationMs, 1);
      const eased = easeOutQuint(progress);
      const rawValue = safeValue * eased;
      const precision = 10 ** decimals;
      setDisplayValue(Math.round(rawValue * precision) / precision);
      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      } else {
        setDisplayValue(safeValue);
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [durationMs, safeValue]);

  return <>{hideRealNumbers ? format(safeValue) : format(displayValue)}</>;
}
