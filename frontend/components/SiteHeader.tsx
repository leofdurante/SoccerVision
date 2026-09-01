import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-pitch text-sm font-bold text-white">
            SV
          </span>
          <span className="text-lg font-semibold tracking-tight">SoccerVision</span>
        </Link>
        <span className="hidden text-sm text-foreground-muted sm:block">
          Computer-vision tactical analysis for uploaded match video
        </span>
      </div>
    </header>
  );
}
