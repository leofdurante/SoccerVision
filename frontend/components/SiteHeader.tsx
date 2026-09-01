import Link from "next/link";
import { LogoMark } from "@/components/icons";

interface SiteHeaderProps {
  /** Rendered on the right of the bar — page context, not a tagline. */
  trailing?: React.ReactNode;
}

export function SiteHeader({ trailing }: SiteHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur-sm">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-4 px-6">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md"
          aria-label="SoccerVision home"
        >
          <LogoMark size={30} />
          <span className="text-[17px] font-semibold tracking-[-0.02em]">SoccerVision</span>
        </Link>
        {trailing ? <div className="ml-auto flex min-w-0 items-center gap-3">{trailing}</div> : null}
      </div>
    </header>
  );
}
