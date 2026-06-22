import type { ReactNode, SVGProps } from "react";

// Outline icon system for CAA — 2px stroke, rounded caps, currentColor, 24×24 grid.
// No fills, no text inside, no decorative flourish: audit-grade and calm.

type IconProps = { size?: number; className?: string; strokeWidth?: number };

function Svg({ size = 18, strokeWidth = 2, className, children, ...rest }: IconProps & SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconArrowLeft = (p: IconProps) => (
  <Svg {...p}><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></Svg>
);
export const IconArrowRight = (p: IconProps) => (
  <Svg {...p}><path d="M5 12h14" /><path d="M12 5l7 7-7 7" /></Svg>
);
export const IconPlus = (p: IconProps) => (
  <Svg {...p}><path d="M12 5v14" /><path d="M5 12h14" /></Svg>
);
export const IconPencil = (p: IconProps) => (
  <Svg {...p}><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></Svg>
);
export const IconTrash = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 6h18" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6" /><path d="M14 11v6" />
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </Svg>
);
export const IconClose = (p: IconProps) => (
  <Svg {...p}><path d="M18 6 6 18" /><path d="M6 6l12 12" /></Svg>
);
export const IconUpload = (p: IconProps) => (
  <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 9l5-5 5 5" /><path d="M12 4v12" /></Svg>
);
export const IconDownload = (p: IconProps) => (
  <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" /></Svg>
);
export const IconDocument = (p: IconProps) => (
  <Svg {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" /><path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" />
  </Svg>
);
export const IconScan = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" />
    <path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    <path d="M7 12h10" />
  </Svg>
);
export const IconCheckCircle = (p: IconProps) => (
  <Svg {...p}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><path d="M22 4 12 14.01l-3-3" /></Svg>
);
export const IconXCircle = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6" /><path d="M9 9l6 6" /></Svg>
);
export const IconFlag = (p: IconProps) => (
  <Svg {...p}><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" /><path d="M4 22v-7" /></Svg>
);
export const IconClock = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></Svg>
);
export const IconDatabase = (p: IconProps) => (
  <Svg {...p}>
    <ellipse cx="12" cy="5" rx="9" ry="3" />
    <path d="M21 5v14c0 1.66-4 3-9 3s-9-1.34-9-3V5" />
    <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
  </Svg>
);
export const IconLink = (p: IconProps) => (
  <Svg {...p}>
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </Svg>
);
export const IconPercent = (p: IconProps) => (
  <Svg {...p}><path d="M19 5 5 19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></Svg>
);
export const IconScale = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3v18" /><path d="M7 21h10" />
    <path d="M3 7h4c2 0 4-1 5-2 1 1 3 2 5 2h4" />
    <path d="M6.5 7 3 14c0 1 1.5 1.8 3.5 1.8S10 15 10 14L6.5 7Z" />
    <path d="M17.5 7 14 14c0 1 1.5 1.8 3.5 1.8S21 15 21 14L17.5 7Z" />
  </Svg>
);
export const IconGauge = (p: IconProps) => (
  <Svg {...p}><path d="M12 13l4-4" /><path d="M3.34 19a10 10 0 1 1 17.32 0" /></Svg>
);
export const IconSearch = (p: IconProps) => (
  <Svg {...p}><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.3-4.3" /></Svg>
);
export const IconEye = (p: IconProps) => (
  <Svg {...p}><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></Svg>
);
export const IconChevronDown = (p: IconProps) => (
  <Svg {...p}><path d="M6 9l6 6 6-6" /></Svg>
);
export const IconBrackets = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 8V5a1 1 0 0 1 1-1h3" /><path d="M16 4h3a1 1 0 0 1 1 1v3" />
    <path d="M20 16v3a1 1 0 0 1-1 1h-3" /><path d="M8 20H5a1 1 0 0 1-1-1v-3" />
  </Svg>
);

// Brand monogram: corner brackets framing an "A" chevron with an emerald status dot.
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 10V6a2 2 0 0 1 2-2h3" />
        <path d="M22 4h3a2 2 0 0 1 2 2v4" />
        <path d="M27 22v4a2 2 0 0 1-2 2h-3" />
        <path d="M10 28H7a2 2 0 0 1-2-2v-4" />
        <path d="M11 22 16 10l5 12" />
        <path d="M13.2 17.4h5.6" />
      </g>
      <circle cx="16" cy="20.5" r="1.7" fill="#1E9E6B" />
    </svg>
  );
}

// Corner-bracket frame: the CAA "document detected / evidence captured" motif.
export function CornerFrame({
  children,
  variant = "full",
  className,
}: {
  children?: ReactNode;
  variant?: "full" | "diag";
  className?: string;
}) {
  return (
    <div className={`bracket-frame${variant === "diag" ? " diag" : ""}${className ? ` ${className}` : ""}`}>
      <span className="bracket tl" />
      <span className="bracket tr" />
      <span className="bracket bl" />
      <span className="bracket br" />
      {children}
    </div>
  );
}
