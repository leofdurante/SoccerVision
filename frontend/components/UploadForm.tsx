"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, uploadVideo } from "@/lib/api";

const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".avi"];

function isSupportedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function UploadForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFile = useCallback(
    async (file: File) => {
      setError(null);
      if (!isSupportedFile(file)) {
        setError(`Unsupported file type. Please upload ${ACCEPTED_EXTENSIONS.join(", ")}.`);
        return;
      }
      setUploading(true);
      try {
        const { analysis_id } = await uploadVideo(file);
        router.push(`/analysis/${analysis_id}`);
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "Upload failed. Is the backend running?";
        setError(message);
        setUploading(false);
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void submitFile(file);
    },
    [submitFile]
  );

  return (
    <div className="w-full max-w-xl">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`card flex cursor-pointer flex-col items-center justify-center gap-3 border-2 border-dashed px-8 py-14 text-center transition-colors ${
          dragActive ? "border-accent bg-surface-muted" : "border-border"
        }`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-pitch/10 text-2xl">⚽</div>
        {uploading ? (
          <>
            <p className="text-base font-medium">Uploading match video…</p>
            <p className="text-sm text-foreground-muted">This starts the analysis job automatically.</p>
          </>
        ) : (
          <>
            <p className="text-base font-medium">Drop a match video here, or click to browse</p>
            <p className="text-sm text-foreground-muted">Supports MP4, MOV, AVI</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void submitFile(file);
          }}
        />
      </div>
      {error && (
        <p className="mt-3 rounded-lg bg-severity-high/10 px-4 py-2 text-sm text-severity-high">{error}</p>
      )}
    </div>
  );
}
