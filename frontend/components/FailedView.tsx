import Link from "next/link";

interface FailedViewProps {
  message: string | null;
}

export function FailedView({ message }: FailedViewProps) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col items-center gap-4 py-20 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-severity-high/10 text-2xl">⚠️</div>
      <h2 className="text-xl font-semibold">Analysis failed</h2>
      <p className="max-w-md text-sm text-foreground-muted">
        {message ?? "Something went wrong while processing this video."}
      </p>
      <Link href="/" className="rounded-full bg-pitch px-5 py-2 text-sm font-medium text-white">
        Try another video
      </Link>
    </div>
  );
}
