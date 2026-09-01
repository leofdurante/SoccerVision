import { STAGE_LABELS, type Stage } from "@/types/analysis";
import { CheckIcon } from "@/components/icons";

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
  const steps = STAGE_ORDER.filter((s) => s !== "uploaded");

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-8 py-16 sm:py-24">
      <div className="flex flex-col gap-2">
        <h1 className="text-[26px] font-semibold leading-tight">Analyzing your match film</h1>
        <p className="text-[15px] text-ink-2">
          This runs frame by frame, so a full half takes a few minutes. You can leave
          this page open — it updates on its own.
        </p>
      </div>

      <div className="flex flex-col gap-2.5">
        <div className="flex items-baseline justify-between">
          <span className="text-[14px] font-medium">{STAGE_LABELS[stage]}</span>
          <output className="tnum text-[14px] font-semibold text-grass-600">{progress}%</output>
        </div>
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-surface-sunk"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Analysis progress"
        >
          <div
            className="h-full rounded-full bg-grass-600 transition-[width] duration-700 ease-out"
            style={{ width: `${Math.max(2, progress)}%` }}
          />
        </div>
      </div>

      <ol className="flex flex-col overflow-hidden rounded-lg border border-line bg-surface">
        {steps.map((s, i) => {
          const stepIndex = STAGE_ORDER.indexOf(s);
          const done = stepIndex < currentIndex || stage === "completed";
          const active = s === stage;
          return (
            <li
              key={s}
              aria-current={active ? "step" : undefined}
              className={`flex items-center gap-3 border-b border-line-soft px-4 py-2.5 text-[14px] last:border-b-0 ${
                active ? "bg-grass-50 font-medium text-grass-900" : done ? "text-ink-2" : "text-ink-3"
              }`}
            >
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold ${
                  done
                    ? "bg-grass-600 text-[oklch(0.99_0.01_148)]"
                    : active
                      ? "bg-grass-600 text-[oklch(0.99_0.01_148)]"
                      : "border border-line bg-surface-sunk text-ink-3"
                }`}
              >
                {done && !active ? (
                  <CheckIcon size={12} strokeWidth={2.6} />
                ) : active ? (
                  <span className="h-1.5 w-1.5 animate-[pulse-ring_1.4s_ease-in-out_infinite] rounded-full bg-current" />
                ) : (
                  <span className="tnum">{i + 1}</span>
                )}
              </span>
              {STAGE_LABELS[s]}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
