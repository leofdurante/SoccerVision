import type { SVGProps } from "react";

/**
 * One stroke-based icon family, drawn on a 24px grid at 1.6 stroke so every
 * glyph keeps the same weight next to 15px text. Replaces the emoji that
 * were standing in for icons.
 */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

/**
 * Brand mark: the pitch itself, seen from above — halfway line, centre circle
 * reduced to what survives at 28px. A ball glyph turns to mush at this size;
 * the halfway line and centre circle stay
 * readable and says "tactical view" rather than "sport".
 */
export function LogoMark({ size = 28, ...props }: SVGProps<SVGSVGElement> & { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <rect width="32" height="32" rx="8.5" fill="var(--grass-600)" />
      <g
        stroke="oklch(0.99 0.012 148)"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
        opacity="0.95"
      >
        <path d="M16 5.6v20.8" />
        <circle cx="16" cy="16" r="5.2" strokeWidth="1.7" />
      </g>
    </svg>
  );
}

export function UploadIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 15.5V4.5" />
      <path d="m7.8 8.7 4.2-4.2 4.2 4.2" />
      <path d="M4.5 14.8v2.7a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2.7" />
    </Icon>
  );
}

export function FilmIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2.2" />
      <path d="M3 9.4h18M3 14.6h18M8 5v14M16 5v14" />
    </Icon>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 4.8 21 20H3Z" />
      <path d="M12 10.4v3.8" />
      <path d="M12 17.1h.01" />
    </Icon>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m5 12.6 4.4 4.4L19 7.4" />
    </Icon>
  );
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4.5 12h15" />
      <path d="m13.8 6.3 5.7 5.7-5.7 5.7" />
    </Icon>
  );
}

export function PlayIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M8.4 5.7 18 12l-9.6 6.3Z" />
    </Icon>
  );
}

export function GridIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3" y="4.5" width="18" height="15" rx="2" />
      <path d="M12 4.5v15" />
      <circle cx="12" cy="12" r="3.1" />
      <path d="M3 9h2.6v6H3M21 9h-2.6v6H21" />
    </Icon>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3.6l1.9 4.9 4.9 1.9-4.9 1.9L12 17.2l-1.9-4.9-4.9-1.9 4.9-1.9Z" />
      <path d="M18.6 16.4l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7Z" />
    </Icon>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M12 7.4V12l3 1.8" />
    </Icon>
  );
}
