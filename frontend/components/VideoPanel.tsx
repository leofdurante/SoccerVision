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
}

export const VideoPanel = forwardRef<VideoPanelHandle, VideoPanelProps>(function VideoPanel(
  { videoUrl, annotatedVideoUrl, onTimeUpdate },
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

  return (
    <div className="flex flex-col gap-3">
      <video
        ref={videoElRef}
        key={src}
        src={apiUrl(src)}
        controls
        className="aspect-video w-full rounded-lg border border-line bg-black shadow-sm"
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
