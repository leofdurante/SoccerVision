"use client";

import dynamic from "next/dynamic";
import type { TeamMetrics } from "@/types/analysis";

// Plotly touches `window` at import time, so it must never be evaluated
// during SSR — dynamic() with ssr:false keeps it client-only.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface TeamComparisonChartProps {
  home: TeamMetrics;
  away: TeamMetrics;
}

export function TeamComparisonChart({ home, away }: TeamComparisonChartProps) {
  const metrics: { label: string; home: number | null; away: number | null }[] = [
    { label: "Width", home: home.width, away: away.width },
    { label: "Depth", home: home.depth, away: away.depth },
    { label: "Avg spacing", home: home.avg_spacing, away: away.avg_spacing },
    { label: "Compactness ×100", home: home.compactness !== null ? home.compactness * 100 : null, away: away.compactness !== null ? away.compactness * 100 : null },
  ];

  return (
    <div className="card p-4">
      <h3 className="mb-2 text-sm font-semibold text-foreground-muted">Team shape comparison</h3>
      <Plot
        data={[
          {
            x: metrics.map((m) => m.label),
            y: metrics.map((m) => m.home),
            type: "bar",
            name: "Home",
            marker: { color: "#2f7ff2" },
          },
          {
            x: metrics.map((m) => m.label),
            y: metrics.map((m) => m.away),
            type: "bar",
            name: "Away",
            marker: { color: "#f2664d" },
          },
        ]}
        layout={{
          autosize: true,
          height: 260,
          margin: { t: 10, r: 10, b: 40, l: 40 },
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: "var(--foreground-muted)", size: 11 },
          legend: { orientation: "h", y: -0.2 },
          barmode: "group",
          yaxis: { gridcolor: "var(--border)" },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
