"use client";

export interface KitColors {
  enabled: boolean;
  home: string;
  away: string;
}

export const DEFAULT_KIT_COLORS: KitColors = {
  enabled: false,
  home: "#1d4ed8",
  away: "#dc2626",
};

interface KitColorPickerProps {
  value: KitColors;
  onChange: (next: KitColors) => void;
  disabled?: boolean;
}

export function KitColorPicker({ value, onChange, disabled }: KitColorPickerProps) {
  return (
    <fieldset disabled={disabled} className="flex flex-col gap-3 disabled:opacity-60">
      <legend className="eyebrow mb-1">Shirt colours</legend>
      <p className="text-[12px] leading-snug text-ink-3">
        Optional. If you set both, people whose shirts match neither — refs, coaches,
        fans — are dropped.
      </p>

      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3">
        <input
          type="checkbox"
          className="mt-1"
          checked={value.enabled}
          onChange={(e) => onChange({ ...value, enabled: e.target.checked })}
        />
        <span className="flex flex-col gap-0.5">
          <span className="text-[14px] font-medium">I know the kit colours</span>
          <span className="text-[12px] text-ink-3">Home and away shirts as they appear on the video</span>
        </span>
      </label>

      {value.enabled && (
        <div className="grid grid-cols-2 gap-3">
          <ColorField
            label="Home"
            value={value.home}
            onChange={(home) => onChange({ ...value, home })}
          />
          <ColorField
            label="Away"
            value={value.away}
            onChange={(away) => onChange({ ...value, away })}
          />
        </div>
      )}
    </fieldset>
  );
}

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (hex: string) => void;
}) {
  return (
    <label className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2.5">
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-8 cursor-pointer rounded border border-line bg-transparent p-0"
        aria-label={`${label} kit colour`}
      />
      <span className="flex min-w-0 flex-col">
        <span className="text-[13px] font-medium">{label}</span>
        <span className="font-mono text-[11px] uppercase text-ink-3">{value}</span>
      </span>
    </label>
  );
}
