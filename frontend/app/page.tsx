import { SiteHeader } from "@/components/SiteHeader";
import { UploadForm } from "@/components/UploadForm";

const PIPELINE_STEPS = [
  { label: "Detect", detail: "Players and the ball, frame by frame" },
  { label: "Track", detail: "One persistent ID per player" },
  { label: "Classify", detail: "Your side vs. theirs, by shirt color" },
  { label: "Map", detail: "Camera angle flattened to a 2D pitch" },
  { label: "Analyze", detail: "Shape, spacing, overloads, events" },
];

export default function Home() {
  return (
    <>
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6">
        {/* Hero ------------------------------------------------------------ */}
        <section className="grid grid-cols-1 items-center gap-x-14 gap-y-10 py-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:py-20">
          <div className="flex flex-col items-start gap-5">
            <span className="inline-flex items-center gap-2 rounded-full border border-grass-200 bg-grass-50 px-3 py-1 text-[12px] font-medium text-grass-700">
              <span className="h-1.5 w-1.5 rounded-full bg-grass-500" />
              Built for match film, not live streams
            </span>

            <h1 className="max-w-[15ch] text-[2.5rem] font-semibold leading-[1.06] sm:text-[3.25rem]">
              Turn match film into a tactical breakdown
            </h1>

            <p className="max-w-[52ch] text-[17px] leading-[1.6] text-ink-2">
              Upload a full-field video of your game. SoccerVision finds every player
              and the ball, follows them through the match, flattens the camera angle
              onto a 2D pitch, and hands back the shape, spacing, and numbers-up
              moments you can take straight into training.
            </p>

          </div>

          <UploadForm />
        </section>

        {/* How it works ---------------------------------------------------- */}
        <section
          aria-labelledby="how-it-works"
          className="border-t border-line py-12 lg:py-16"
        >
          <h2 id="how-it-works" className="eyebrow">
            What happens after you upload
          </h2>

          <ol className="mt-6 grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-5">
            {PIPELINE_STEPS.map((step, i) => (
              <li key={step.label} className="flex flex-col gap-1.5 bg-surface p-5">
                <span className="tnum text-[12px] font-semibold text-grass-600">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="text-[15px] font-semibold">{step.label}</span>
                <span className="text-[13px] leading-snug text-ink-3">{step.detail}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* Honest limits --------------------------------------------------- */}
        <section className="border-t border-line py-10">
          <p className="max-w-[68ch] text-[13px] leading-relaxed text-ink-3">
            <span className="font-semibold text-ink-2">A note on the numbers.</span>{" "}
            SoccerVision analyzes uploaded video in batches — it does not process live
            or streamed footage. Formation and possession figures are heuristic
            estimates derived from computer-vision data, and they are labeled as such
            everywhere they appear in the dashboard.
          </p>
        </section>
      </main>
    </>
  );
}
