// Mirrors backend/app/schemas/analysis.py — keep in sync by hand (no
// codegen step for this hackathon MVP).

export type Team = "home" | "away" | "unknown";

export type AnalysisStatus = "queued" | "processing" | "completed" | "failed";

export type Stage =
  | "uploaded"
  | "extracting_frames"
  | "detecting_players"
  | "tracking_players"
  | "classifying_teams"
  | "mapping_field"
  | "calculating_metrics"
  | "generating_insights"
  | "completed"
  | "failed";

export const STAGE_LABELS: Record<Stage, string> = {
  uploaded: "Uploaded",
  extracting_frames: "Extracting frames",
  detecting_players: "Detecting players & ball",
  tracking_players: "Tracking players",
  classifying_teams: "Classifying teams",
  mapping_field: "Mapping field positions",
  calculating_metrics: "Calculating tactical metrics",
  generating_insights: "Generating AI insights",
  completed: "Completed",
  failed: "Failed",
};

export interface AnalysisCreateResponse {
  analysis_id: string;
  status: AnalysisStatus;
}

export interface AnalysisStatusResponse {
  analysis_id: string;
  status: AnalysisStatus;
  stage: Stage;
  progress: number;
  error_message: string | null;
}

export interface VideoMetadata {
  fps: number;
  width: number;
  height: number;
  duration_seconds: number;
  frame_count: number;
  processing_fps: number;
  processed_frame_count: number;
}

export interface PlayerFrame {
  track_id: number;
  timestamp: number;
  bbox: [number, number, number, number];
  center: [number, number];
  confidence: number;
  team: Team;
  team_confidence: number;
  field_x: number | null;
  field_y: number | null;
}

export interface BallFrame {
  timestamp: number;
  bbox: [number, number, number, number];
  center: [number, number];
  confidence: number;
  field_x: number | null;
  field_y: number | null;
  possession_track_id: number | null;
  possession_team: Team | null;
}

export interface TeamMetrics {
  team: Team;
  width: number | null;
  depth: number | null;
  centroid: [number, number] | null;
  avg_spacing: number | null;
  compactness: number | null;
  defensive_line_height: number | null;
  formation: string | null;
  formation_confidence: number | null;
  formation_is_heuristic: boolean;
  players_in_defensive_third: number;
  players_in_middle_third: number;
  players_in_final_third: number;
}

export interface NumericalAdvantage {
  zone: string;
  home_count: number;
  away_count: number;
  advantage_team: Team;
  advantage_label: string;
}

export interface MetricsResponse {
  analysis_id: string;
  home: TeamMetrics;
  away: TeamMetrics;
  numerical_advantages: NumericalAdvantage[];
  possession_estimate: Record<string, number> | null;
}

export interface TacticalEvent {
  timestamp: number;
  type: string;
  severity: "low" | "medium" | "high";
  team: Team | null;
  description: string;
  source: "computer_vision_fact";
}

export interface TimelineEntry {
  timestamp: number;
  label: string;
  type: string;
}

export interface Insight {
  text: string;
  based_on: string[];
  source: "ai_interpretation" | "rule_based_fallback";
}

export interface AnalysisFullResponse {
  analysis_id: string;
  status: AnalysisStatus;
  stage: Stage;
  progress: number;
  original_filename: string;
  video_url: string;
  annotated_video_url: string | null;
  video_metadata: VideoMetadata | null;
  metrics: MetricsResponse | null;
  events: TacticalEvent[];
  timeline: TimelineEntry[];
  insights: Insight[];
  players: PlayerFrame[];
  ball_positions: BallFrame[];
  created_at: string;
  error_message: string | null;
}
