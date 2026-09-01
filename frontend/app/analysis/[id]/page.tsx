"use client";

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

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { status, analysis, error } = useAnalysis(id);
  const [currentTime, setCurrentTime] = useState(0);
  const videoRef = useRef<VideoPanelHandle>(null);

  const seek = (seconds: number) => {
    videoRef.current?.seekTo(seconds);
    setCurrentTime(seconds);
  };

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        {error && !status && (
          <p className="mb-4 rounded-lg bg-severity-high/10 px-4 py-2 text-sm text-severity-high">{error}</p>
        )}

        {!status && !error && <ProcessingView stage="uploaded" progress={0} />}

        {status && status.status !== "completed" && status.status !== "failed" && (
          <ProcessingView stage={status.stage} progress={status.progress} />
        )}

        {status?.status === "failed" && <FailedView message={status.error_message} />}

        {status?.status === "completed" && analysis && (
          <div className="flex flex-col gap-6">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">{analysis.original_filename}</h1>
              {analysis.video_metadata && (
                <p className="text-sm text-foreground-muted">
                  {analysis.video_metadata.width}×{analysis.video_metadata.height} ·{" "}
                  {analysis.video_metadata.duration_seconds.toFixed(0)}s ·{" "}
                  {analysis.video_metadata.processed_frame_count} frames analyzed @{" "}
                  {analysis.video_metadata.processing_fps} fps
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
              <div className="flex flex-col gap-3 lg:col-span-3">
                <VideoPanel
                  ref={videoRef}
                  videoUrl={analysis.video_url}
                  annotatedVideoUrl={analysis.annotated_video_url}
                  onTimeUpdate={setCurrentTime}
                />
              </div>
              <div className="card overflow-hidden lg:col-span-2">
                <TacticalPitch players={analysis.players} ball={analysis.ball_positions} currentTime={currentTime} />
              </div>
            </div>

            {analysis.metrics && (
              <>
                <MetricsGrid metrics={analysis.metrics} />
                <TeamComparisonChart home={analysis.metrics.home} away={analysis.metrics.away} />
              </>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <InsightsPanel insights={analysis.insights} />
              <EventTimeline events={analysis.events} onSeek={seek} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
