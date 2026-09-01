"use client";

import { useId } from "react";

export type RangeMode = "first-5" | "first-15" | "custom";

export interface AnalysisRange {
  mode: RangeMode;
  /** mm:ss strings, only meaningful when mode is "custom". */
  from: string;
  to: string;
}

export const DEFAULT_RANGE: AnalysisRange = { mode: "first-5", from: "", to: "" };

const PRESETS: { mode: RangeMode; label: string; hint: string }[] = [
  { mode: "first-5", label: "First 5 minutes", hint: "Quick check that it all works" },
  { mode: "first-15", label: "First 15 minutes", hint: "Opening spell of the match" },
  { mode: "custom", label: "A specific passage", hint: "Pick the window you want to study" },
];

/** Accepts "mm:ss", "h:mm:ss" or a plain number of seconds. */
export function parseClock(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parts = trimmed.split(":");
  if (parts.some((p) => p === "" || !/^\d+$/.test(p))) return null;
  const nums = parts.map(Number);
  if (nums.length === 1) return nums[0];
  if (nums.length === 2) return nums[0] * 60 + nums[1];
  if (nums.length === 3) return nums[0] * 3600 + nums[1] * 60 + nums[2];
  return null;
}

/** Resolve the picker's state into the seconds the API expects. */
export function resolveRange(range: AnalysisRange): {
  startSeconds?: number;
  endSeconds?: number;
  error?: string;
} {
  if (range.mode === "first-5") return { startSeconds: 0, endSeconds: 5 * 60 };
  if (range.mode === "first-15") return { startSeconds: 0, endSeconds: 15 * 60 };

  const start = parseClock(range.from);
  const end = parseClock(range.to);
  if (start === null || end === null) {
    return { error: "Enter both times as mm:ss — for example 34:00 to 39:00." };
  }
  if (end <= start) {
    return { error: "The end time needs to come after the start time." };
  }
  return { startSeconds: start, endSeconds: end };
}

interface AnalysisRangePickerProps {
  value: AnalysisRange;
  onChange: (next: AnalysisRange) => void;
  disabled?: boolean;
}

export function AnalysisRangePicker({ value, onChange, disabled }: AnalysisRangePickerProps) {
  const groupName = useId();

  return (
    <fieldset disabled={disabled} className="flex flex-col gap-3 disabled:opacity-60">
      <legend className="eyebrow mb-2">How much should we analyze?</legend>

      <div className="flex flex-col gap-px overflow-hidden rounded-lg border border-line bg-line">
        {PRESETS.map((preset) => {
          const selected = value.mode === preset.mode;
          return (
            <label
              key={preset.mode}
              className={`flex cursor-pointer items-start gap-3 bg-surface px-4 py-3 transition-colors ${
                selected ? "bg-grass-50" : "hover:bg-surface-sunk"
              }`}
            >
              <input
                type="radio"
                name={groupName}
                checked={selected}
                onChange={() => onChange({ ...value, mode: preset.mode })}
                className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--grass-600)]"
              />
              <span className="flex flex-col gap-0.5">
                <span className="text-[14px] font-medium leading-tight">{preset.label}</span>
                <span className="text-[12px] leading-snug text-ink-3">{preset.hint}</span>
              </span>
            </label>
          );
        })}
      </div>

      {value.mode === "custom" && (
        <div className="flex flex-wrap items-center gap-2 text-[14px]">
          <label className="flex items-center gap-2">
            <span className="text-ink-2">From</span>
            <input
              value={value.from}
              onChange={(e) => onChange({ ...value, from: e.target.value })}
              placeholder="34:00"
              inputMode="numeric"
              aria-label="Start of the passage to analyze, as mm:ss"
              className="tnum w-[5.5rem] rounded-md border border-line-strong bg-surface px-2.5 py-2 text-center font-mono text-[14px]"
            />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-ink-2">to</span>
            <input
              value={value.to}
              onChange={(e) => onChange({ ...value, to: e.target.value })}
              placeholder="39:00"
              inputMode="numeric"
              aria-label="End of the passage to analyze, as mm:ss"
              className="tnum w-[5.5rem] rounded-md border border-line-strong bg-surface px-2.5 py-2 text-center font-mono text-[14px]"
            />
          </label>
        </div>
      )}

      <p className="text-[12px] leading-snug text-ink-3">
        Analysis runs frame by frame, so a shorter window finishes sooner. If your
        video is a broadcast, skip past the intro titles — kickoff is often several
        minutes in.
      </p>
    </fieldset>
  );
}
