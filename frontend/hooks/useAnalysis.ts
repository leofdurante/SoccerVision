"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, getAnalysis, getAnalysisStatus } from "@/lib/api";
import type { AnalysisFullResponse, AnalysisStatusResponse } from "@/types/analysis";

const POLL_INTERVAL_MS = 1500;

interface UseAnalysisResult {
  status: AnalysisStatusResponse | null;
  analysis: AnalysisFullResponse | null;
  error: string | null;
}

/**
 * Polls /status while the job is queued/processing, then fetches the
 * full analysis exactly once it reaches a terminal state. This is the
 * "frontend polls status" half of the upload -> process -> poll ->
 * dashboard flow described in the spec.
 */
export function useAnalysis(analysisId: string): UseAnalysisResult {
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisFullResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetchedFullOnce = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const statusResponse = await getAnalysisStatus(analysisId);
        if (cancelled) return;
        setStatus(statusResponse);
        setError(null);

        const terminal = statusResponse.status === "completed" || statusResponse.status === "failed";

        if (terminal && !fetchedFullOnce.current) {
          fetchedFullOnce.current = true;
          const full = await getAnalysis(analysisId);
          if (!cancelled) setAnalysis(full);
        }

        if (!terminal) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Could not reach the analysis server.";
        setError(message);
        timer = setTimeout(poll, POLL_INTERVAL_MS * 2);
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [analysisId]);

  return { status, analysis, error };
}
