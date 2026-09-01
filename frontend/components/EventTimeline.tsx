"use client";

import type { TacticalEvent } from "@/types/analysis";
import { PlayIcon } from "@/components/icons";

interface EventTimelineProps {
  events: TacticalEvent[];
  onSeek: (seconds: number) => void;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const SEVERITY: Record<TacticalEvent["severity"], { dot: string; label: string }> = {
  high: { dot: "bg-danger", label: "High" },
  medium: { dot: "bg-warn", label: "Medium" },
  low: { dot: "bg-ink-3", label: "Low" },
};

export function EventTimeline({ events, onSeek }: EventTimelineProps) {
  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp);

  return (
    <section className="card flex flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="eyebrow">Event timeline</h3>
        {sorted.length > 0 && (
          <span className="tnum text-[11px] text-ink-3">{sorted.length} moments</span>
        )}
      </div>

      {sorted.length === 0 ? (
        <p className="mt-3 border-t border-line-soft pt-4 text-[14px] text-ink-3">
          No notable tactical events were detected in this video.
        </p>
      ) : (
        <ul className="mt-3 flex max-h-80 flex-col divide-y divide-line-soft overflow-y-auto border-t border-line-soft">
          {sorted.map((event, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() => onSeek(event.timestamp)}
                className="group flex w-full items-center gap-3 py-2.5 pr-1 text-left transition-colors hover:bg-surface-sunk"
                title={`Jump to ${formatTimestamp(event.timestamp)}`}
              >
                <span className="tnum w-11 shrink-0 font-mono text-[12px] text-ink-3 group-hover:text-grass-600">
                  {formatTimestamp(event.timestamp)}
                </span>
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${SEVERITY[event.severity].dot}`}
                  title={`${SEVERITY[event.severity].label} severity`}
                />
                <span className="flex-1 text-[14px] leading-snug">{event.description}</span>
                <PlayIcon
                  size={15}
                  className="shrink-0 text-ink-3 opacity-0 transition-opacity group-hover:opacity-100"
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
