"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, uploadVideo } from "@/lib/api";
import { AlertIcon, FilmIcon, UploadIcon } from "@/components/icons";

const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".avi"];

function isSupportedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

function formatSize(bytes: number): string {
  const mb = bytes / 1_000_000;
  return mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb.toFixed(0)} MB`;
}

export function UploadForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submitFile = useCallback(
    async (file: File) => {
      setError(null);
      if (!isSupportedFile(file)) {
        setError(`That file type isn't supported yet. Try ${ACCEPTED_EXTENSIONS.join(", ")}.`);
        return;
      }
      setUploading(file);
      try {
        const { analysis_id } = await uploadVideo(file);
        router.push(`/analysis/${analysis_id}`);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Upload failed. Is the backend running?";
        setError(message);
        setUploading(null);
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLElement>) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void submitFile(file);
    },
    [submitFile]
  );

  return (
    <div className="flex w-full flex-col gap-3">
      {/* A real button, so the dropzone is reachable by keyboard and
          announced as an upload control rather than a decorative div. */}
      <button
        type="button"
        disabled={Boolean(uploading)}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!uploading) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`card flex w-full flex-col items-center justify-center gap-3 px-8 py-12 text-center transition-colors duration-150 ${
          uploading
            ? "cursor-default border-grass-200 bg-grass-50"
            : dragActive
              ? "border-grass-500 bg-grass-50"
              : "cursor-pointer hover:border-line-strong hover:bg-surface-sunk"
        }`}
      >
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-xl border ${
            uploading || dragActive
              ? "border-grass-200 bg-grass-100 text-grass-700"
              : "border-line bg-surface-sunk text-ink-2"
          }`}
        >
          {uploading ? <FilmIcon size={22} /> : <UploadIcon size={22} />}
        </span>

        {uploading ? (
          <span className="flex flex-col gap-1">
            <span className="text-[15px] font-semibold">Uploading your match film…</span>
            <span className="truncate text-[13px] text-ink-3">
              {uploading.name} · {formatSize(uploading.size)}
            </span>
          </span>
        ) : (
          <span className="flex flex-col gap-1">
            <span className="text-[15px] font-semibold">
              Drop your match video here
            </span>
            <span className="text-[13px] text-ink-3">
              or click to browse — MP4, MOV, AVI
            </span>
          </span>
        )}

        {uploading ? (
          <span
            className="mt-1 h-1 w-32 overflow-hidden rounded-full bg-grass-200"
            role="progressbar"
            aria-label="Uploading"
          >
            <span className="block h-full w-1/3 animate-[upload-sweep_1.1s_ease-in-out_infinite] rounded-full bg-grass-600" />
          </span>
        ) : null}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void submitFile(file);
        }}
      />

      {error && (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-md border border-danger/25 bg-danger-soft px-3.5 py-2.5 text-[13px] leading-snug text-danger"
        >
          <AlertIcon size={16} className="mt-px shrink-0" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
