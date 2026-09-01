"use client";

import { useMemo } from "react";
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
const MAX_FRAME_GAP_SECONDS = 1.5; // don't render a player whose nearest sample is too far from currentTime
const TRAIL_WINDOW_SECONDS = 4;

const TEAM_COLOR: Record<Team, string> = {
  home: "var(--home)",
  away: "var(--away)",
  unknown: "#9aa39c",
};

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

  return (
    <svg viewBox={`0 0 100 ${100 * Y_SCALE}`} className="h-full w-full" preserveAspectRatio="xMidYMid meet">
      {/* Pitch surface */}
      <rect x={0} y={0} width={100} height={100 * Y_SCALE} fill="var(--pitch)" rx={1.5} />

      {/* Markings */}
      <g stroke="var(--pitch-line)" strokeWidth={0.4} fill="none">
        <rect x={1} y={1} width={98} height={100 * Y_SCALE - 2} />
        <line x1={50} y1={1} x2={50} y2={100 * Y_SCALE - 1} />
        <circle cx={50} cy={50 * Y_SCALE} r={8} />
        <circle cx={50} cy={50 * Y_SCALE} r={0.6} fill="var(--pitch-line)" />
        {/* penalty areas */}
        <rect x={1} y={19 * Y_SCALE} width={16} height={62 * Y_SCALE} />
        <rect x={83} y={19 * Y_SCALE} width={16} height={62 * Y_SCALE} />
        {/* six-yard boxes */}
        <rect x={1} y={37 * Y_SCALE} width={6} height={26 * Y_SCALE} />
        <rect x={93} y={37 * Y_SCALE} width={6} height={26 * Y_SCALE} />
      </g>

      {/* Player trails */}
      {showTrails &&
        currentPlayers.map(({ frame, trail }) =>
          trail.length > 1 ? (
            <polyline
              key={`trail-${frame.track_id}`}
              points={trail.map((f) => `${f.field_x},${(f.field_y ?? 0) * Y_SCALE}`).join(" ")}
              fill="none"
              stroke={TEAM_COLOR[frame.team]}
              strokeWidth={0.4}
              strokeOpacity={0.4}
            />
          ) : null
        )}

      {/* Ball */}
      {currentBall && currentBall.field_x !== null && currentBall.field_y !== null && (
        <circle
          cx={currentBall.field_x}
          cy={currentBall.field_y * Y_SCALE}
          r={1.1}
          fill="#fefefe"
          stroke="#1a1a1a"
          strokeWidth={0.25}
        />
      )}

      {/* Players */}
      {currentPlayers.map(({ frame }) => (
        <g key={frame.track_id} transform={`translate(${frame.field_x}, ${(frame.field_y ?? 0) * Y_SCALE})`}>
          <circle r={2.1} fill={TEAM_COLOR[frame.team]} stroke="#04140c" strokeWidth={0.25} />
          <text
            y={-2.6}
            textAnchor="middle"
            fontSize={2.4}
            fill="var(--pitch-line)"
            className="select-none"
          >
            {frame.track_id}
          </text>
        </g>
      ))}
    </svg>
  );
}
