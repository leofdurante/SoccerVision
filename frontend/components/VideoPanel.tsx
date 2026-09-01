"use client";

import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { apiUrl } from "@/lib/api";

export interface VideoPanelHandle {
  /** Seek to an absolute timestamp in the source video's own timeline. */
  seekTo: (seconds: number) => void;
}

interface VideoPanelProps {
  videoUrl: string;
  annotatedVideoUrl: string | null;
  /** Always receives an ABSOLUTE timestamp, whichever source is playing. */
  onTimeUpdate: (seconds: number) => void;
  /**
   * Absolute offset of the analysed window. The annotated clip contains only
   * the analysed frames, so its own clock starts at 0 while the tracking data
   * is stamped in the original video's timeline — everything downstream keys
   * off absolute time, so the two have to be reconciled here.
   */
  analysisStartSeconds?: number;
}

export const VideoPanel = forwardRef<VideoPanelHandle, VideoPanelProps>(function VideoPanel(
  { videoUrl, annotatedVideoUrl, onTimeUpdate, analysisStartSeconds = 0 },
  ref
) {
  const videoElRef = useRef<HTMLVideoElement>(null);
  const [showAnnotated, setShowAnnotated] = useState(Boolean(annotatedVideoUrl));

  const usingAnnotated = showAnnotated && Boolean(annotatedVideoUrl);
  // The annotated clip's t=0 is the start of the analysed window.
  const offset = usingAnnotated ? analysisStartSeconds : 0;

  const toAbsolute = (elapsed: number) => elapsed + offset;
  const toElapsed = (absolute: number) => absolute - offset;

  useImperativeHandle(
    ref,
    () => ({
      seekTo(seconds: number) {
        const el = videoElRef.current;
        if (!el) return;
        const target = toElapsed(seconds);
        if (!Number.isFinite(target) || target < 0) return;
        el.currentTime = target;
        onTimeUpdate(seconds);
      },
    }),
    // Rebuild when the offset changes so a seek after toggling source lands right.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [offset, onTimeUpdate]
  );

  const src = usingAnnotated && annotatedVideoUrl ? annotatedVideoUrl : videoUrl;

  // Only the original needs seeking — the annotated clip already begins at the
  // window. Landing at 0:00 on a 103-minute original whose analysis starts ten
  // minutes in shows an empty pitch and reads as a broken feature.
  const seekedFor = useRef<string | null>(null);
  const onLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const el = e.currentTarget;
    if (seekedFor.current === src) return;
    seekedFor.current = src;

    if (usingAnnotated) {
      onTimeUpdate(toAbsolute(el.currentTime));
      return;
    }
    if (analysisStartSeconds > 0 && Number.isFinite(el.duration) && analysisStartSeconds < el.duration) {
      el.currentTime = analysisStartSeconds;
    }
    onTimeUpdate(el.currentTime);
  };

  const switchSource = (next: boolean) => {
    // Carry the viewing position across the toggle instead of jumping.
    const el = videoElRef.current;
    const absolute = el ? toAbsolute(el.currentTime) : analysisStartSeconds;
    setShowAnnotated(next);
    seekedFor.current = null;
    onTimeUpdate(absolute);
  };

  return (
    <div className="flex flex-col gap-3">
      <video
        ref={videoElRef}
        key={src}
        src={apiUrl(src)}
        controls
        className="aspect-video w-full rounded-lg border border-line bg-black shadow-sm"
        onLoadedMetadata={onLoadedMetadata}
        onTimeUpdate={(e) => onTimeUpdate(toAbsolute(e.currentTarget.currentTime))}
      />

      {annotatedVideoUrl && (
        <div className="flex items-center justify-between gap-3">
          <div className="segment" role="group" aria-label="Video source">
            <button
              type="button"
              aria-pressed={!showAnnotated}
              onClick={() => switchSource(false)}
              className="segment-item"
            >
              Original
            </button>
            <button
              type="button"
              aria-pressed={showAnnotated}
              onClick={() => switchSource(true)}
              className="segment-item"
            >
              With tracking
            </button>
          </div>
          <span className="hidden text-[12px] text-ink-3 sm:block">
            {usingAnnotated ? "Analyzed window only, at sampling rate" : "Full original video"}
          </span>
        </div>
      )}
    </div>
  );
});
