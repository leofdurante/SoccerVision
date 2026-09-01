import { SiteHeader } from "@/components/SiteHeader";
import { UploadForm } from "@/components/UploadForm";

const PIPELINE_STEPS = [
  { label: "Detect", detail: "Players & ball via YOLO" },
  { label: "Track", detail: "Persistent IDs via ByteTrack" },
  { label: "Classify", detail: "Team A vs Team B by shirt color" },
  { label: "Map", detail: "Camera view → 2D pitch" },
  { label: "Analyze", detail: "Shape, overloads, events" },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center gap-14 px-6 py-16">
        <div className="flex flex-col items-center gap-4 text-center">
          <span className="rounded-full bg-pitch/10 px-3 py-1 text-xs font-medium tracking-wide text-pitch uppercase">
            Upload-based match analysis
          </span>
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
            Turn match footage into tactical intelligence
          </h1>
          <p className="max-w-xl text-base text-foreground-muted">
            Upload a full-field soccer video. SoccerVision detects players and the ball,
            tracks them across the match, maps positions onto a 2D pitch, and surfaces
            tactical metrics, numerical advantages, and AI-generated coaching insights.
          </p>
        </div>

        <UploadForm />

        <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-5">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.label} className="card flex flex-col gap-1 px-4 py-4">
              <span className="text-xs font-medium text-foreground-muted">Step {i + 1}</span>
              <span className="text-sm font-semibold">{step.label}</span>
              <span className="text-xs text-foreground-muted">{step.detail}</span>
            </div>
          ))}
        </div>

        <p className="max-w-xl text-center text-xs text-foreground-muted">
          Batch analysis only — this project does not process live or streamed video.
          Formation and possession figures are heuristic estimates from computer-vision
          data, clearly labeled as such throughout the dashboard.
        </p>
      </main>
    </div>
  );
}
