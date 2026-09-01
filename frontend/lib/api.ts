import type {
  AnalysisCreateResponse,
  AnalysisFullResponse,
  AnalysisStatusResponse,
} from "@/types/analysis";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/** The slice of the upload to analyze, in seconds from the start of the video. */
export interface AnalysisWindowRequest {
  startSeconds?: number;
  endSeconds?: number;
  homeKitHex?: string;
  awayKitHex?: string;
}

export async function uploadVideo(
  file: File,
  window: AnalysisWindowRequest = {}
): Promise<AnalysisCreateResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (window.startSeconds !== undefined) {
    formData.append("start_seconds", String(window.startSeconds));
  }
  if (window.endSeconds !== undefined) {
    formData.append("end_seconds", String(window.endSeconds));
  }
  if (window.homeKitHex) {
    formData.append("home_kit_hex", window.homeKitHex);
  }
  if (window.awayKitHex) {
    formData.append("away_kit_hex", window.awayKitHex);
  }

  const response = await fetch(apiUrl("/api/v1/analyses"), {
    method: "POST",
    body: formData,
  });
  return handleResponse<AnalysisCreateResponse>(response);
}

export async function getAnalysisStatus(analysisId: string): Promise<AnalysisStatusResponse> {
  const response = await fetch(apiUrl(`/api/v1/analyses/${analysisId}/status`), {
    cache: "no-store",
  });
  return handleResponse<AnalysisStatusResponse>(response);
}

export async function getAnalysis(analysisId: string): Promise<AnalysisFullResponse> {
  const response = await fetch(apiUrl(`/api/v1/analyses/${analysisId}`), {
    cache: "no-store",
  });
  return handleResponse<AnalysisFullResponse>(response);
}
