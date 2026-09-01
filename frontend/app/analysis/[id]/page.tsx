"use client";

import Link from "next/link";
import { use, useRef, useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { ProcessingView } from "@/components/ProcessingView";
import { FailedView } from "@/components/FailedView";
import { VideoPanel, type VideoPanelHandle } from "@/components/VideoPanel";
import { TacticalPitch } from "@/components/TacticalPitch";
import { MetricsGrid } from "@/components/MetricsGrid";
import { TeamComparisonChart } from "@/components/TeamComparisonChart";
import { InsightsPanel } from "@/components/InsightsPanel";
import { EventTimeline } from "@/components/EventTimeline";
import { useAnalysis } from "@/hooks/useAnalysis";
import { AlertIcon, UploadIcon } from "@/components/icons";

function MetaItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-2 text-[13px] text-ink-2 before:h-1 before:w-1 before:rounded-full before:bg-line-strong first:before:hidden">
      {children}
    </li>
  );
}

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { status, analysis, error } = useAnalysis(id);
  const [currentTime, setCurrentTime] = useState(0);
  const videoRef = useRef<VideoPanelHandle>(null);

  const seek = (seconds: number) => {
    videoRef.current?.seekTo(seconds);
    setCurrentTime(seconds);
  };

  const meta = analysis?.video_metadata;

  return (
    <>
      <SiteHeader
        trailing={
          <Link href="/" className="btn btn-secondary h-9 min-h-9 px-3 text-[13px]">
            <UploadIcon size={16} />
            New analysis
          </Link>
        }
      />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 pb-20">
        {error && !status && (
          <p
            role="alert"
            className="mt-6 flex items-start gap-2 rounded-md border border-danger/25 bg-danger-soft px-3.5 py-2.5 text-[13px] text-danger"
          >
            <AlertIcon size={16} className="mt-px shrink-0" />
            <span>{error}</span>
          </p>
        )}

        {!status && !error && <ProcessingView stage="uploaded" progress={0} />}

        {status && status.status !== "completed" && status.status !== "failed" && (
          <ProcessingView stage={status.stage} progress={status.progress} />
        )}

        {status?.status === "failed" && <FailedView message={status.error_message} />}

        {status?.status === "completed" && analysis && (
          <div className="flex flex-col gap-8">
            {/* Title block ------------------------------------------------- */}
            <div className="flex flex-col gap-2 border-b border-line py-8">
              <h1 className="truncate text-[28px] font-semibold leading-tight tracking-[-0.022em]">
                {analysis.original_filename}
              </h1>
              {meta && (
                <ul className="tnum flex flex-wrap items-center gap-x-4 gap-y-1">
                  <MetaItem>
                    {meta.width}&times;{meta.height}
                  </MetaItem>
                  <MetaItem>{meta.duration_seconds.toFixed(0)}s</MetaItem>
                  <MetaItem>
                    {meta.processed_frame_count.toLocaleString()} frames analyzed
                  </MetaItem>
                  <MetaItem>{meta.processing_fps} fps</MetaItem>
                </ul>
              )}
            </div>

            {/* Film + pitch ------------------------------------------------ */}
            <section aria-labelledby="film-heading" className="flex flex-col gap-3">
              <h2 id="film-heading" className="eyebrow">
                Film &amp; positions
              </h2>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-7">
                <div className="lg:col-span-4">
                  <VideoPanel
                    ref={videoRef}
                    videoUrl={analysis.video_url}
                    annotatedVideoUrl={analysis.annotated_video_url}
                    onTimeUpdate={setCurrentTime}
                  />
                </div>

                <div className="card flex flex-col overflow-hidden lg:col-span-3">
                  <div className="flex items-center justify-between gap-2 border-b border-line-soft px-4 py-2.5">
                    <span className="eyebrow">Pitch view</span>
                    <span className="flex items-center gap-3 text-[11px] text-ink-2">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-home" />
                        Home
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-away" />
                        Away
                      </span>
                    </span>
                  </div>
                  <div className="flex flex-1 items-center bg-surface-sunk p-3">
                    <TacticalPitch
                      players={analysis.players}
                      ball={analysis.ball_positions}
                      currentTime={currentTime}
                    />
                  </div>
                </div>
              </div>
            </section>

            {/* Metrics ----------------------------------------------------- */}
            {analysis.metrics && (
              <section aria-labelledby="metrics-heading" className="flex flex-col gap-3">
                <h2 id="metrics-heading" className="eyebrow">
                  Tactical metrics
                </h2>
                <MetricsGrid metrics={analysis.metrics} />
                <TeamComparisonChart home={analysis.metrics.home} away={analysis.metrics.away} />
              </section>
            )}

            {/* Read-out ---------------------------------------------------- */}
            <section aria-labelledby="readout-heading" className="flex flex-col gap-3">
              <h2 id="readout-heading" className="eyebrow">
                Read-out
              </h2>
              <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
                <InsightsPanel insights={analysis.insights} />
                <EventTimeline events={analysis.events} onSeek={seek} />
              </div>
            </section>
          </div>
        )}
      </main>
    </>
  );
}
