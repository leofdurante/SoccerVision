"use client";

import Link from "next/link";
import { use, useMemo, useRef, useState } from "react";
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
import { AlertIcon, ClockIcon, UploadIcon } from "@/components/icons";

function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

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
  const requestedWindow =
    analysis?.analysis_window?.requested_start_seconds != null ||
    analysis?.analysis_window?.requested_end_seconds != null;

  // The backend caps how much of a long upload it analyses, so the dashboard
  // can describe a fraction of the match. Work out what was actually covered
  // and say so, rather than letting the metrics read as whole-match figures.
  const coverage = useMemo(() => {
    const frames = analysis?.players ?? [];
    if (frames.length === 0 || !meta) return null;
    let start = Infinity;
    let end = -Infinity;
    for (const frame of frames) {
      if (frame.timestamp < start) start = frame.timestamp;
      if (frame.timestamp > end) end = frame.timestamp;
    }
    if (!Number.isFinite(start)) return null;
    const duration = meta.duration_seconds;
    return { start, end, duration, partial: duration > 0 && end - start < duration * 0.9 };
  }, [analysis?.players, meta]);

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

            {coverage?.partial &&
              (requestedWindow ? (
                <div className="flex items-start gap-2.5 rounded-md border border-line bg-surface-sunk px-4 py-3">
                  <ClockIcon size={17} className="mt-px shrink-0 text-ink-3" />
                  <p className="text-[13px] leading-snug text-ink-2">
                    <span className="font-semibold text-ink">
                      Showing {formatClock(coverage.start)}&ndash;{formatClock(coverage.end)} of
                      this {formatClock(coverage.duration)} video
                    </span>{" "}
                    &mdash; the passage you asked to analyze. Everything below describes
                    that window.
                  </p>
                </div>
              ) : (
                <div className="flex items-start gap-2.5 rounded-md border border-warn/30 bg-warn-soft px-4 py-3">
                  <AlertIcon size={17} className="mt-px shrink-0 text-warn" />
                  <p className="text-[13px] leading-snug text-ink-2">
                    <span className="font-semibold text-ink">
                      Only {formatClock(coverage.start)}&ndash;{formatClock(coverage.end)} of this{" "}
                      {formatClock(coverage.duration)} video was analyzed.
                    </span>{" "}
                    The analyzer stops after a fixed number of frames. Upload again and
                    pick the passage you want, or raise{" "}
                    <code className="rounded-xs bg-surface px-1 py-px font-mono text-[12px]">
                      MAX_PROCESSED_FRAMES
                    </code>
                    .
                  </p>
                </div>
              ))}

            {/* Film + pitch ------------------------------------------------ */}
            <section aria-labelledby="film-heading" className="flex flex-col gap-3">
              <h2 id="film-heading" className="eyebrow">
                Film &amp; player positions
              </h2>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-7">
                <div className="lg:col-span-4">
                  <VideoPanel
                    ref={videoRef}
                    videoUrl={analysis.video_url}
                    annotatedVideoUrl={analysis.annotated_video_url}
                    onTimeUpdate={setCurrentTime}
                    startAtSeconds={coverage?.start}
                  />
                </div>

                <div className="card flex flex-col overflow-hidden lg:col-span-3">
                  <div className="flex items-center justify-between gap-2 border-b border-line-soft px-4 py-2.5">
                    <span className="eyebrow">
                      Camera view
                      {coverage && (
                        <span className="ml-2 font-normal normal-case tracking-normal text-ink-3">
                          {formatClock(coverage.start)}&ndash;{formatClock(coverage.end)}
                        </span>
                      )}
                    </span>
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
            {/* The camera pans and zooms to follow play and the pipeline has no
                pitch registration, so positions are relative to the frame, not
                the pitch. Say so once, prominently, rather than letting the
                numbers imply a precision they do not have. */}
            {analysis.metrics && (
              <section aria-labelledby="metrics-heading" className="flex flex-col gap-3">
                <h2 id="metrics-heading" className="eyebrow">
                  Tactical metrics
                </h2>
                <div className="flex items-start gap-2.5 rounded-md border border-line bg-surface-sunk px-4 py-3">
                  <AlertIcon size={17} className="mt-px shrink-0 text-ink-3" />
                  <p className="text-[13px] leading-snug text-ink-2">
                    <span className="font-semibold text-ink">
                      These figures are relative to the camera frame, not the pitch.
                    </span>{" "}
                    The camera pans and zooms to follow play, and the analyzer does not
                    yet register the video against pitch markings &mdash; so shape
                    measurements describe how players are spread within the shot. Use
                    them to compare moments in the same passage, not as absolute
                    distances.
                  </p>
                </div>
                <MetricsGrid
                  metrics={analysis.metrics}
                  ballSampleCount={analysis.ball_positions.length}
                />
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
