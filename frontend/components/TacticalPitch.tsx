"use client";

import { useId, useMemo } from "react";
import type { BallFrame, PlayerFrame, Team } from "@/types/analysis";

interface TacticalPitchProps {
  players: PlayerFrame[];
  ball: BallFrame[];
  currentTime: number;
  showTrails?: boolean;
}

// Visual-only compression of the y axis so the pitch reads as a realistic
// ~105x68m rectangle even though field_x/field_y are both normalized 0-100.
const Y_SCALE = 0.64;
const H = 100 * Y_SCALE;
const MAX_FRAME_GAP_SECONDS = 1.5; // don't render a player whose nearest sample is too far from currentTime
const TRAIL_WINDOW_SECONDS = 4;

// Markings, scaled from real dimensions (105m x 68m) into the 0-100 space.
const PAD = 1.4; // touchline inset
const PEN_W = 15.7; // 16.5m penalty area depth
const PEN_Y = 20.5 * Y_SCALE; // 40.3m wide, centred
const PEN_H = 59 * Y_SCALE;
const SIX_W = 5.2; // 5.5m six-yard box depth
const SIX_Y = 36.5 * Y_SCALE;
const SIX_H = 27 * Y_SCALE;
const SPOT_X = 10.5; // 11m penalty spot
const CIRCLE_R = 8.7; // 9.15m centre circle

const TEAM_COLOR: Record<Team, string> = {
  home: "var(--home)",
  away: "var(--away)",
  unknown: "var(--neutral-team)",
};

function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function nearestFrame<T extends { timestamp: number }>(frames: T[], t: number): T | null {
  let best: T | null = null;
  let bestDiff = Infinity;
  for (const frame of frames) {
    const diff = Math.abs(frame.timestamp - t);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = frame;
    }
  }
  return best && bestDiff <= MAX_FRAME_GAP_SECONDS ? best : null;
}

export function TacticalPitch({ players, ball, currentTime, showTrails = true }: TacticalPitchProps) {
  const gradientId = useId();

  const byTrack = useMemo(() => {
    const map = new Map<number, PlayerFrame[]>();
    for (const frame of players) {
      if (frame.field_x === null || frame.field_y === null) continue;
      const list = map.get(frame.track_id) ?? [];
      list.push(frame);
      map.set(frame.track_id, list);
    }
    for (const list of map.values()) list.sort((a, b) => a.timestamp - b.timestamp);
    return map;
  }, [players]);

  const currentPlayers = useMemo(() => {
    const results: { frame: PlayerFrame; trail: PlayerFrame[] }[] = [];
    for (const [, frames] of byTrack) {
      const current = nearestFrame(frames, currentTime);
      if (!current) continue;
      const trail = showTrails
        ? frames.filter((f) => f.timestamp <= currentTime && f.timestamp >= currentTime - TRAIL_WINDOW_SECONDS)
        : [];
      results.push({ frame: current, trail });
    }
    return results;
  }, [byTrack, currentTime, showTrails]);

  const currentBall = useMemo(() => nearestFrame(ball, currentTime), [ball, currentTime]);

  // The backend analyses only a bounded window of long uploads, so the
  // playhead is routinely outside the tracked range. Say so rather than
  // painting an empty pitch that reads as a broken feature.
  const covered = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const frame of players) {
      if (frame.timestamp < min) min = frame.timestamp;
      if (frame.timestamp > max) max = frame.timestamp;
    }
    return Number.isFinite(min) ? { start: min, end: max } : null;
  }, [players]);

  const outOfRange =
    covered !== null &&
    currentPlayers.length === 0 &&
    (currentTime < covered.start - MAX_FRAME_GAP_SECONDS ||
      currentTime > covered.end + MAX_FRAME_GAP_SECONDS);

  return (
    <svg
      viewBox={`-1 -1 102 ${H + 2}`}
      className="h-full w-full"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Two-dimensional pitch showing tracked player positions at the current video time"
    >
      <defs>
        <radialGradient id={`${gradientId}-vignette`} cx="50%" cy="50%" r="72%">
          <stop offset="55%" stopColor="#000" stopOpacity="0" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.16" />
        </radialGradient>
      </defs>

      {/* Turf, with mown stripes so the pitch reads as a surface, not a swatch */}
      <rect x={0} y={0} width={100} height={H} fill="var(--pitch)" rx={1} />
      <g>
        {[0, 2, 4, 6, 8].map((i) => (
          <rect key={i} x={i * 10} y={0} width={10} height={H} fill="var(--pitch-alt)" />
        ))}
      </g>
      <rect x={0} y={0} width={100} height={H} rx={1} fill={`url(#${gradientId}-vignette)`} />

      {/* Markings */}
      <g stroke="var(--pitch-line)" strokeWidth={0.32} fill="none" strokeLinejoin="round">
        <rect x={PAD} y={PAD} width={100 - PAD * 2} height={H - PAD * 2} />
        <line x1={50} y1={PAD} x2={50} y2={H - PAD} />
        <circle cx={50} cy={H / 2} r={CIRCLE_R} />

        {/* Penalty and six-yard boxes */}
        <rect x={PAD} y={PEN_Y} width={PEN_W} height={PEN_H} />
        <rect x={100 - PAD - PEN_W} y={PEN_Y} width={PEN_W} height={PEN_H} />
        <rect x={PAD} y={SIX_Y} width={SIX_W} height={SIX_H} />
        <rect x={100 - PAD - SIX_W} y={SIX_Y} width={SIX_W} height={SIX_H} />

        {/* Penalty arcs — clipped to the part outside each box */}
        <path d={`M ${PAD + PEN_W} ${H / 2 - 5.1} A ${CIRCLE_R} ${CIRCLE_R} 0 0 1 ${PAD + PEN_W} ${H / 2 + 5.1}`} />
        <path
          d={`M ${100 - PAD - PEN_W} ${H / 2 - 5.1} A ${CIRCLE_R} ${CIRCLE_R} 0 0 0 ${100 - PAD - PEN_W} ${H / 2 + 5.1}`}
        />

        {/* Corner arcs */}
        <path d={`M ${PAD + 1.1} ${PAD} A 1.1 1.1 0 0 1 ${PAD} ${PAD + 1.1}`} />
        <path d={`M ${PAD} ${H - PAD - 1.1} A 1.1 1.1 0 0 1 ${PAD + 1.1} ${H - PAD}`} />
        <path d={`M ${100 - PAD - 1.1} ${PAD} A 1.1 1.1 0 0 0 ${100 - PAD} ${PAD + 1.1}`} />
        <path d={`M ${100 - PAD} ${H - PAD - 1.1} A 1.1 1.1 0 0 0 ${100 - PAD - 1.1} ${H - PAD}`} />

        {/* Goals */}
        <rect x={PAD - 1.5} y={H / 2 - 3.4} width={1.5} height={6.8} />
        <rect x={100 - PAD} y={H / 2 - 3.4} width={1.5} height={6.8} />
      </g>

      {/* Spots */}
      <g fill="var(--pitch-line)">
        <circle cx={50} cy={H / 2} r={0.5} />
        <circle cx={PAD + SPOT_X} cy={H / 2} r={0.42} />
        <circle cx={100 - PAD - SPOT_X} cy={H / 2} r={0.42} />
      </g>

      {/* Movement trails over the last few seconds */}
      {showTrails &&
        currentPlayers.map(({ frame, trail }) =>
          trail.length > 1 ? (
            <polyline
              key={`trail-${frame.track_id}`}
              points={trail.map((f) => `${f.field_x},${(f.field_y ?? 0) * Y_SCALE}`).join(" ")}
              fill="none"
              stroke={TEAM_COLOR[frame.team]}
              strokeWidth={0.55}
              strokeOpacity={0.45}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null
        )}

      {/* Ball */}
      {currentBall && currentBall.field_x !== null && currentBall.field_y !== null && (
        <g transform={`translate(${currentBall.field_x}, ${currentBall.field_y * Y_SCALE})`}>
          <circle r={2.0} fill="#000" fillOpacity={0.18} />
          <circle r={1.15} fill="#ffffff" stroke="#12211a" strokeWidth={0.28} />
        </g>
      )}

      {/* Out-of-range notice */}
      {outOfRange && (
        <g>
          <rect x={0} y={0} width={100} height={H} rx={1} fill="#04140c" fillOpacity={0.62} />
          <text
            x={50}
            y={H / 2 - 2.6}
            textAnchor="middle"
            fontSize={3.6}
            fontWeight={600}
            fill="#ffffff"
            className="select-none"
          >
            No tracking data here
          </text>
          <text
            x={50}
            y={H / 2 + 3.4}
            textAnchor="middle"
            fontSize={2.9}
            fill="#ffffff"
            fillOpacity={0.78}
            className="select-none"
          >
            {`Analysis covers ${formatClock(covered.start)}\u2013${formatClock(covered.end)}`}
          </text>
        </g>
      )}

      {/* Players */}
      {currentPlayers.map(({ frame }) => (
        <g key={frame.track_id} transform={`translate(${frame.field_x}, ${(frame.field_y ?? 0) * Y_SCALE})`}>
          <ellipse cy={0.55} rx={2.1} ry={1.1} fill="#000" fillOpacity={0.18} />
          <circle r={2.25} fill={TEAM_COLOR[frame.team]} stroke="#ffffff" strokeWidth={0.42} />
          <text
            y={0.78}
            textAnchor="middle"
            fontSize={2.1}
            fontWeight={600}
            fill="#ffffff"
            className="pointer-events-none select-none"
          >
            {frame.track_id}
          </text>
        </g>
      ))}
    </svg>
  );
}
