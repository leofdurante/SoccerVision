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
    <div className="flex flex-col gap-2">
      <video
        ref={videoElRef}
        key={src}
        src={apiUrl(src)}
        controls
        className="aspect-video w-full rounded-xl bg-black"
        onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
      />
      {annotatedVideoUrl && (
        <div className="flex items-center gap-2 self-start rounded-full bg-surface-muted p-1 text-xs">
          <button
            type="button"
            onClick={() => setShowAnnotated(false)}
            className={`rounded-full px-3 py-1 transition-colors ${!showAnnotated ? "bg-surface font-medium shadow-sm" : "text-foreground-muted"}`}
          >
            Original
          </button>
          <button
            type="button"
            onClick={() => setShowAnnotated(true)}
            className={`rounded-full px-3 py-1 transition-colors ${showAnnotated ? "bg-surface font-medium shadow-sm" : "text-foreground-muted"}`}
          >
            CV overlay
          </button>
        </div>
      )}
    </div>
  );
});
