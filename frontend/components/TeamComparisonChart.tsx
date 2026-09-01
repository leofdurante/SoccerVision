"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { TeamMetrics } from "@/types/analysis";

// Plotly touches `window` at import time, so it must never be evaluated
// during SSR — dynamic() with ssr:false keeps it client-only.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface TeamComparisonChartProps {
  home: TeamMetrics;
  away: TeamMetrics;
}

const TOKENS = ["--home", "--away", "--ink-3", "--line", "--surface"] as const;
type TokenName = (typeof TOKENS)[number];
type Palette = Record<TokenName, string>;

const FALLBACK: Palette = {
  "--home": "#2f6fd0",
  "--away": "#d4703a",
  "--ink-3": "#8a938c",
  "--line": "#dfe3dd",
  "--surface": "#ffffff",
};

/**
 * Plotly writes colors into canvas/SVG attributes, where `var(--token)` is
 * never resolved — the previous version passed CSS variables straight through
 * and silently fell back to Plotly's defaults. Resolve them off the document
 * instead, and re-resolve when the color scheme flips.
 */
function useResolvedPalette(): Palette {
  const [palette, setPalette] = useState<Palette>(FALLBACK);

  useEffect(() => {
    const read = () => {
      const computed = getComputedStyle(document.documentElement);
      const next = { ...FALLBACK };
      for (const token of TOKENS) {
        const value = computed.getPropertyValue(token).trim();
        if (value) next[token] = value;
      }
      setPalette(next);
    };

    read();
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    scheme.addEventListener("change", read);
    return () => scheme.removeEventListener("change", read);
  }, []);

  return palette;
}

export function TeamComparisonChart({ home, away }: TeamComparisonChartProps) {
  const palette = useResolvedPalette();

  const metrics: { label: string; home: number | null; away: number | null }[] = [
    { label: "Width", home: home.width, away: away.width },
    { label: "Depth", home: home.depth, away: away.depth },
    { label: "Avg spacing", home: home.avg_spacing, away: away.avg_spacing },
    {
      label: "Compactness",
      home: home.compactness !== null ? home.compactness * 100 : null,
      away: away.compactness !== null ? away.compactness * 100 : null,
    },
  ];

  const hasData = metrics.some((m) => m.home !== null || m.away !== null);

  return (
    <section className="card p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="eyebrow">Team shape comparison</h3>
        <span className="text-[11px] text-ink-3">
          Pitch units · compactness shown 0&ndash;100
        </span>
      </div>

      <div className="mt-2 border-t border-line-soft pt-2">
        {!hasData ? (
          <p className="py-10 text-center text-[14px] text-ink-3">
            Not enough tracked players in this video to compare team shape.
          </p>
        ) : (
        <Plot
          data={[
            {
              x: metrics.map((m) => m.label),
              y: metrics.map((m) => m.home),
              type: "bar",
              name: "Home",
              marker: { color: palette["--home"] },
              hovertemplate: "Home · %{x}<br>%{y:.1f}<extra></extra>",
            },
            {
              x: metrics.map((m) => m.label),
              y: metrics.map((m) => m.away),
              type: "bar",
              name: "Away",
              marker: { color: palette["--away"] },
              hovertemplate: "Away · %{x}<br>%{y:.1f}<extra></extra>",
            },
          ]}
          layout={{
            autosize: true,
            height: 250,
            margin: { t: 8, r: 8, b: 52, l: 36 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: {
              color: palette["--ink-3"],
              size: 11,
              family: "var(--font-archivo), sans-serif",
            },
            legend: { orientation: "h", y: -0.22, x: 0, font: { size: 12 } },
            barmode: "group",
            bargap: 0.34,
            bargroupgap: 0.12,
            hoverlabel: {
              bgcolor: palette["--surface"],
              bordercolor: palette["--line"],
              font: { size: 12 },
            },
            xaxis: { showgrid: false, zeroline: false, showline: false, ticklen: 6, tickcolor: "rgba(0,0,0,0)" },
            yaxis: {
              gridcolor: palette["--line"],
              griddash: "dot",
              zeroline: false,
              showline: false,
              ticklen: 0,
            },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
          useResizeHandler
        />
        )}
      </div>
    </section>
  );
}
