import type { MetricsResponse, Team } from "@/types/analysis";

interface MetricsGridProps {
  metrics: MetricsResponse;
}

function TeamPill({ team }: { team: Team }) {
  const color = team === "home" ? "bg-home" : team === "away" ? "bg-away" : "bg-foreground-muted";
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium capitalize">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {team}
    </span>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-foreground-muted">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

function fmt(value: number | null, suffix = ""): string {
  return value === null ? "—" : `${value.toFixed(1)}${suffix}`;
}

function TeamCard({ team, metrics }: { team: Team; metrics: MetricsResponse["home"] }) {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between">
        <TeamPill team={team} />
        {metrics.formation && (
          <span className="rounded-full bg-surface-muted px-2.5 py-1 text-xs font-semibold" title="Heuristic estimate — not a trained classifier">
            {metrics.formation}
            <span className="ml-1 font-normal text-foreground-muted">
              ({Math.round((metrics.formation_confidence ?? 0) * 100)}% conf., heuristic)
            </span>
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <StatRow label="Width" value={fmt(metrics.width, " units")} />
        <StatRow label="Depth" value={fmt(metrics.depth, " units")} />
        <StatRow label="Avg spacing" value={fmt(metrics.avg_spacing, " units")} />
        <StatRow label="Compactness" value={metrics.compactness === null ? "—" : `${Math.round(metrics.compactness * 100)}%`} />
        <StatRow label="Defensive line height" value={fmt(metrics.defensive_line_height)} />
      </div>
      <div className="flex justify-between rounded-lg bg-surface-muted px-3 py-2 text-center text-xs">
        <div>
          <div className="font-semibold">{metrics.players_in_defensive_third}</div>
          <div className="text-foreground-muted">Def 3rd</div>
        </div>
        <div>
          <div className="font-semibold">{metrics.players_in_middle_third}</div>
          <div className="text-foreground-muted">Mid 3rd</div>
        </div>
        <div>
          <div className="font-semibold">{metrics.players_in_final_third}</div>
          <div className="text-foreground-muted">Final 3rd</div>
        </div>
      </div>
    </div>
  );
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TeamCard team="home" metrics={metrics.home} />
        <TeamCard team="away" metrics={metrics.away} />
      </div>

      {metrics.possession_estimate && (
        <div className="card flex items-center gap-3 p-4 text-sm">
          <span className="font-medium">Possession (estimated)</span>
          <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-surface-muted">
            <div className="h-full bg-home" style={{ width: `${(metrics.possession_estimate.home ?? 0.5) * 100}%` }} />
            <div className="h-full bg-away" style={{ width: `${(metrics.possession_estimate.away ?? 0.5) * 100}%` }} />
          </div>
          <span className="text-foreground-muted">
            {Math.round((metrics.possession_estimate.home ?? 0.5) * 100)}% / {Math.round((metrics.possession_estimate.away ?? 0.5) * 100)}%
          </span>
        </div>
      )}

      {metrics.numerical_advantages.length > 0 && (
        <div className="card flex flex-col gap-2 p-4">
          <h3 className="text-sm font-semibold text-foreground-muted">Numerical advantages</h3>
          <div className="flex flex-wrap gap-2">
            {metrics.numerical_advantages.map((adv) => (
              <span
                key={adv.zone}
                className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                  adv.advantage_team === "home" ? "bg-home/10 text-home" : "bg-away/10 text-away"
                }`}
              >
                {adv.advantage_label} · {adv.zone.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
