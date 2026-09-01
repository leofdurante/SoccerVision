"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, uploadVideo } from "@/lib/api";
import { AlertIcon, ArrowRightIcon, FilmIcon, UploadIcon } from "@/components/icons";
import {
  AnalysisRangePicker,
  DEFAULT_RANGE,
  resolveRange,
  type AnalysisRange,
} from "@/components/AnalysisRangePicker";
import {
  KitColorPicker,
  DEFAULT_KIT_COLORS,
  type KitColors,
} from "@/components/KitColorPicker";

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
  const [file, setFile] = useState<File | null>(null);
  const [range, setRange] = useState<AnalysisRange>(DEFAULT_RANGE);
  const [kits, setKits] = useState<KitColors>(DEFAULT_KIT_COLORS);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chooseFile = useCallback((candidate: File) => {
    if (!isSupportedFile(candidate)) {
      setError(`That file type isn't supported yet. Try ${ACCEPTED_EXTENSIONS.join(", ")}.`);
      return;
    }
    setError(null);
    setFile(candidate);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLElement>) => {
      e.preventDefault();
      setDragActive(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) chooseFile(dropped);
    },
    [chooseFile]
  );

  const submit = useCallback(async () => {
    if (!file) return;
    const resolved = resolveRange(range);
    if (resolved.error) {
      setError(resolved.error);
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const { analysis_id } = await uploadVideo(file, {
        startSeconds: resolved.startSeconds,
        endSeconds: resolved.endSeconds,
        ...(kits.enabled
          ? { homeKitHex: kits.home, awayKitHex: kits.away }
          : {}),
      });
      router.push(`/analysis/${analysis_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Upload failed. Is the backend running?"
      );
      setUploading(false);
    }
  }, [file, range, kits, router]);

  return (
    <div className="flex w-full flex-col gap-3">
      {file === null ? (
        // A real button, so the dropzone is reachable by keyboard and
        // announced as an upload control rather than a decorative div.
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          className={`card flex w-full cursor-pointer flex-col items-center justify-center gap-3 px-8 py-12 text-center transition-colors duration-150 ${
            dragActive
              ? "border-grass-500 bg-grass-50"
              : "hover:border-line-strong hover:bg-surface-sunk"
          }`}
        >
          <span
            className={`flex h-12 w-12 items-center justify-center rounded-xl border ${
              dragActive
                ? "border-grass-200 bg-grass-100 text-grass-700"
                : "border-line bg-surface-sunk text-ink-2"
            }`}
          >
            <UploadIcon size={22} />
          </span>
          <span className="flex flex-col gap-1">
            <span className="text-[15px] font-semibold">Drop your match video here</span>
            <span className="text-[13px] text-ink-3">or click to browse — MP4, MOV, AVI</span>
          </span>
        </button>
      ) : (
        <div className="card flex flex-col gap-5 p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-grass-200 bg-grass-50 text-grass-700">
              <FilmIcon size={20} />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <p className="truncate text-[14px] font-semibold" title={file.name}>
                {file.name}
              </p>
              <p className="text-[12px] text-ink-3">{formatSize(file.size)}</p>
            </div>
            {!uploading && (
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  setError(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="shrink-0 rounded-md px-2 py-1 text-[13px] text-ink-3 transition-colors hover:bg-surface-sunk hover:text-ink"
              >
                Change
              </button>
            )}
          </div>

          <AnalysisRangePicker value={range} onChange={setRange} disabled={uploading} />

          <KitColorPicker value={kits} onChange={setKits} disabled={uploading} />

          <button
            type="button"
            onClick={submit}
            disabled={uploading}
            className="btn btn-primary w-full"
          >
            {uploading ? (
              "Uploading…"
            ) : (
              <>
                Start analysis
                <ArrowRightIcon size={17} />
              </>
            )}
          </button>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          const picked = e.target.files?.[0];
          if (picked) chooseFile(picked);
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
