"use client";

import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { apiUrl } from "@/lib/api";

export interface VideoPanelHandle {
  seekTo: (seconds: number) => void;
}

interface VideoPanelProps {
  videoUrl: string;
  annotatedVideoUrl: string | null;
  onTimeUpdate: (seconds: number) => void;
  /** Jump here once the video is ready — the analysed window rarely starts at 0. */
  startAtSeconds?: number;
}

export const VideoPanel = forwardRef<VideoPanelHandle, VideoPanelProps>(function VideoPanel(
  { videoUrl, annotatedVideoUrl, onTimeUpdate, startAtSeconds },
  ref
) {
  const videoElRef = useRef<HTMLVideoElement>(null);
  const [showAnnotated, setShowAnnotated] = useState(Boolean(annotatedVideoUrl));

  useImperativeHandle(ref, () => ({
    seekTo(seconds: number) {
      if (videoElRef.current) {
        videoElRef.current.currentTime = seconds;
      }
    },
  }));

  const src = showAnnotated && annotatedVideoUrl ? annotatedVideoUrl : videoUrl;

  // Landing at 0:00 on a video whose analysed window starts ten minutes in
  // shows an empty pitch and reads as a broken feature. Open on the window.
  const seekedFor = useRef<string | null>(null);
  const onLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const el = e.currentTarget;
    if (startAtSeconds === undefined || seekedFor.current === src) return;
    if (!Number.isFinite(el.duration) || startAtSeconds >= el.duration) return;
    seekedFor.current = src;
    el.currentTime = startAtSeconds;
    onTimeUpdate(startAtSeconds);
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
        onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
      />

      {annotatedVideoUrl && (
        <div className="flex items-center justify-between gap-3">
          <div className="segment" role="group" aria-label="Video source">
            <button
              type="button"
              aria-pressed={!showAnnotated}
              onClick={() => setShowAnnotated(false)}
              className="segment-item"
            >
              Original
            </button>
            <button
              type="button"
              aria-pressed={showAnnotated}
              onClick={() => setShowAnnotated(true)}
              className="segment-item"
            >
              With tracking
            </button>
          </div>
          <span className="hidden text-[12px] text-ink-3 sm:block">
            Boxes and IDs drawn by the detector
          </span>
        </div>
      )}
    </div>
  );
});
