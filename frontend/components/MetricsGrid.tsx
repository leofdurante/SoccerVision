import type { MetricsResponse, Team, TeamMetrics } from "@/types/analysis";

interface MetricsGridProps {
  metrics: MetricsResponse;
  /** How many frames the ball was actually detected in. Possession is derived
   *  from ball position, so a handful of detections makes it meaningless. */
  ballSampleCount: number;
}

// Below this many ball detections, a possession split is noise wearing a
// percentage sign — two detections in a minute can read as "100% / 0%".
const MIN_BALL_SAMPLES_FOR_POSSESSION = 25;

interface ComparisonRow {
  label: string;
  home: number | null;
  away: number | null;
  format: (v: number) => string;
}

function TeamLabel({ team, align }: { team: Team; align: "left" | "right" }) {
  const dot = team === "home" ? "bg-home" : team === "away" ? "bg-away" : "bg-ink-3";
  return (
    <span
      className={`flex items-center gap-2 text-[13px] font-semibold capitalize ${
        align === "right" ? "flex-row-reverse" : ""
      }`}
    >
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
      {team}
    </span>
  );
}

/**
 * Formation estimation reads player positions against pitch thirds and
 * lanes. Without pitch registration those positions are camera-relative,
 * so the label would be a guess wearing a confidence score. Withheld
 * until the mapping is real.
 */
function FormationTag() {
  return null;
}

/**
 * A center-out comparison bar: each side's bar is scaled against the larger
 * of the two values, so a coach can read "who is wider / deeper" without
 * comparing two separate cards.
 */
function ComparisonBar({ label, home, away, format }: ComparisonRow) {
  const missing = home === null && away === null;
  const max = Math.max(home ?? 0, away ?? 0) || 1;
  const homePct = home === null ? 0 : (home / max) * 100;
  const awayPct = away === null ? 0 : (away / max) * 100;

  return (
    <div className="grid grid-cols-[3.25rem_1fr_3.25rem] items-center gap-2.5 py-2.5 sm:grid-cols-[4.5rem_1fr_4.5rem] sm:gap-3">
      <span className="tnum text-right text-[14px] font-semibold">
        {home === null ? <span className="text-ink-3">&mdash;</span> : format(home)}
      </span>

      <div className="flex flex-col items-center gap-1.5">
        <span className="text-[11px] font-medium tracking-[0.01em] text-ink-3">{label}</span>
        {/* Empty tracks read as a stuck loading skeleton, so a row with no
            data on either side says so instead of drawing them. */}
        {missing ? (
          <span className="text-[11px] text-ink-3">not measured</span>
        ) : (
          <span className="flex w-full items-center gap-1">
            <span className="flex h-1.5 flex-1 justify-end overflow-hidden rounded-full bg-surface-sunk">
              <span className="h-full rounded-full bg-home" style={{ width: `${homePct}%` }} />
            </span>
            <span className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunk">
              <span className="h-full rounded-full bg-away" style={{ width: `${awayPct}%` }} />
            </span>
          </span>
        )}
      </div>

      <span className="tnum text-[14px] font-semibold">
        {away === null ? <span className="text-ink-3">&mdash;</span> : format(away)}
      </span>
    </div>
  );
}

function ThirdsStrip({ team, metrics }: { team: Team; metrics: TeamMetrics }) {
  const thirds = [
    { label: "Defensive", value: metrics.players_in_defensive_third },
    { label: "Middle", value: metrics.players_in_middle_third },
    { label: "Attacking", value: metrics.players_in_final_third },
  ];
  const bar = team === "home" ? "bg-home" : "bg-away";
  const peak = Math.max(...thirds.map((t) => t.value), 1);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <TeamLabel team={team} align="left" />
        <FormationTag />
      </div>

      <div className="flex flex-col gap-2 border-t border-line-soft pt-3">
        <span className="eyebrow">Players by third</span>
        {thirds.map((third) => (
          <div key={third.label} className="grid grid-cols-[5.5rem_1fr_1.5rem] items-center gap-3">
            <span className="text-[13px] text-ink-2">{third.label}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-surface-sunk">
              {third.value > 0 && (
                <span
                  className={`block h-full rounded-full ${bar}`}
                  style={{ width: `${(third.value / peak) * 100}%` }}
                />
              )}
            </span>
            <span className="tnum text-right text-[13px] font-semibold">{third.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MetricsGrid({ metrics, ballSampleCount }: MetricsGridProps) {
  const rows: ComparisonRow[] = [
    { label: "Width", home: metrics.home.width, away: metrics.away.width, format: (v) => v.toFixed(1) },
    { label: "Depth", home: metrics.home.depth, away: metrics.away.depth, format: (v) => v.toFixed(1) },
    {
      label: "Average spacing",
      home: metrics.home.avg_spacing,
      away: metrics.away.avg_spacing,
      format: (v) => v.toFixed(1),
    },
    {
      label: "Compactness",
      home: metrics.home.compactness,
      away: metrics.away.compactness,
      format: (v) => `${Math.round(v * 100)}%`,
    },
    {
      label: "Defensive line height",
      home: metrics.home.defensive_line_height,
      away: metrics.away.defensive_line_height,
      format: (v) => v.toFixed(1),
    },
  ];

  const homePossession = metrics.possession_estimate?.home ?? 0.5;
  const awayPossession = metrics.possession_estimate?.away ?? 0.5;

  return (
    <div className="flex flex-col gap-4">
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <TeamLabel team="home" align="left" />
          <h3 className="eyebrow">Team shape · camera-relative</h3>
          <TeamLabel team="away" align="right" />
        </div>

        <div className="mt-3 divide-y divide-line-soft border-t border-line-soft">
          {rows.map((row) => (
            <ComparisonBar key={row.label} {...row} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="card p-5">
          <ThirdsStrip team="home" metrics={metrics.home} />
        </div>
        <div className="card p-5">
          <ThirdsStrip team="away" metrics={metrics.away} />
        </div>
      </div>

      {metrics.possession_estimate && ballSampleCount < MIN_BALL_SAMPLES_FOR_POSSESSION && (
        <div className="card flex flex-col gap-1.5 p-5">
          <h3 className="eyebrow">Possession</h3>
          <p className="text-[13px] leading-snug text-ink-3">
            Not enough ball detections to estimate possession &mdash; the ball was
            found in {ballSampleCount} {ballSampleCount === 1 ? "frame" : "frames"} of
            this window. At this video resolution it is only a few pixels across, so
            the detector rarely picks it up.
          </p>
        </div>
      )}

      {metrics.possession_estimate && ballSampleCount >= MIN_BALL_SAMPLES_FOR_POSSESSION && (
        <div className="card flex flex-col gap-2.5 p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="eyebrow">Possession · estimated</h3>
            <span className="tnum text-[13px] font-semibold">
              <span className="text-home">{Math.round(homePossession * 100)}%</span>
              <span className="mx-1.5 font-normal text-ink-3">/</span>
              <span className="text-away">{Math.round(awayPossession * 100)}%</span>
            </span>
          </div>
          <div className="flex h-2 overflow-hidden rounded-full bg-surface-sunk">
            <div className="h-full bg-home" style={{ width: `${homePossession * 100}%` }} />
            <div className="h-full bg-away" style={{ width: `${awayPossession * 100}%` }} />
          </div>
        </div>
      )}

      {metrics.numerical_advantages.length > 0 && (
        <div className="card flex flex-col gap-3 p-5">
          <h3 className="eyebrow">Numerical advantages</h3>
          <ul className="flex flex-wrap gap-2">
            {metrics.numerical_advantages.map((adv) => (
              <li
                key={adv.zone}
                className={`flex items-baseline gap-2 rounded-md border px-2.5 py-1.5 text-[13px] ${
                  adv.advantage_team === "home"
                    ? "border-home/25 bg-home-soft"
                    : "border-away/25 bg-away-soft"
                }`}
              >
                <span
                  className={`tnum font-semibold ${
                    adv.advantage_team === "home" ? "text-home" : "text-away"
                  }`}
                >
                  {adv.advantage_label}
                </span>
                <span className="text-ink-2">{adv.zone.replace(/_/g, " ")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
