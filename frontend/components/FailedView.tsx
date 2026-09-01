import Link from "next/link";
import { AlertIcon, ArrowRightIcon } from "@/components/icons";

interface FailedViewProps {
  message: string | null;
}

export function FailedView({ message }: FailedViewProps) {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col items-start gap-5 py-16 sm:py-24">
      <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-danger/25 bg-danger-soft text-danger">
        <AlertIcon size={22} />
      </span>
      <div className="flex flex-col gap-2">
        <h1 className="text-[26px] font-semibold leading-tight">This analysis didn&rsquo;t finish</h1>
        <p className="text-[15px] leading-relaxed text-ink-2">
          {message ?? "Something went wrong while processing this video."}
        </p>
      </div>
      <Link href="/" className="btn btn-primary">
        Upload another video
        <ArrowRightIcon size={17} />
      </Link>
    </div>
  );
}
