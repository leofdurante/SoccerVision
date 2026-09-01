import { STAGE_LABELS, type Stage } from "@/types/analysis";

const STAGE_ORDER: Stage[] = [
  "uploaded",
  "extracting_frames",
  "detecting_players",
  "tracking_players",
  "classifying_teams",
  "mapping_field",
  "calculating_metrics",
  "generating_insights",
  "completed",
];

interface ProcessingViewProps {
  stage: Stage;
  progress: number;
}

export function ProcessingView({ stage, progress }: ProcessingViewProps) {
  const currentIndex = STAGE_ORDER.indexOf(stage);

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col items-center gap-8 py-20">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-pitch/10 text-3xl">
        <span className="animate-pulse">⚽</span>
      </div>
      <div className="flex flex-col items-center gap-2 text-center">
        <h2 className="text-xl font-semibold">Analyzing your match footage</h2>
        <p className="text-sm text-foreground-muted">{STAGE_LABELS[stage]}…</p>
      </div>

      <div className="w-full">
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-muted">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${Math.max(4, progress)}%` }}
          />
        </div>
        <p className="mt-2 text-right text-xs text-foreground-muted">{progress}%</p>
      </div>

      <ol className="grid w-full grid-cols-2 gap-2 text-xs sm:grid-cols-3">
        {STAGE_ORDER.filter((s) => s !== "uploaded").map((s, i) => {
          const stepIndex = STAGE_ORDER.indexOf(s);
          const done = stepIndex < currentIndex || stage === "completed";
          const active = s === stage;
          return (
            <li
              key={s}
              className={`flex items-center gap-2 rounded-lg px-2.5 py-2 ${
                active ? "bg-accent/10 text-accent" : done ? "text-foreground-muted" : "text-foreground-muted/50"
              }`}
            >
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] ${
                  done || active ? "bg-accent text-[#04140c]" : "bg-surface-muted"
                }`}
              >
                {done && !active ? "✓" : i + 1}
              </span>
              {STAGE_LABELS[s]}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
