import type { TacticalEvent } from "@/types/analysis";

interface EventTimelineProps {
  events: TacticalEvent[];
  onSeek: (seconds: number) => void;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const SEVERITY_COLOR: Record<TacticalEvent["severity"], string> = {
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
};

export function EventTimeline({ events, onSeek }: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="card p-5 text-sm text-foreground-muted">
        No notable tactical events were detected in this video.
      </div>
    );
  }

  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp);

  return (
    <div className="card flex flex-col gap-1 p-5">
      <h3 className="mb-2 text-sm font-semibold">Event timeline</h3>
      <div className="flex max-h-72 flex-col overflow-y-auto">
        {sorted.map((event, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSeek(event.timestamp)}
            className="flex items-center gap-3 rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-surface-muted"
          >
            <span className="w-12 shrink-0 font-mono text-xs text-foreground-muted">
              {formatTimestamp(event.timestamp)}
            </span>
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_COLOR[event.severity]}`} />
            <span className="flex-1">{event.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
