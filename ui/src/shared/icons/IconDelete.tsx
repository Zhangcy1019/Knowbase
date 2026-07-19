import type { SVGProps } from "react";

export function IconDelete(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 7h16" />
      <path d="M9 7V5.5C9 4.67 9.67 4 10.5 4h3c.83 0 1.5.67 1.5 1.5V7" />
      <path d="M7.5 7l.6 11.1c.05.82.73 1.46 1.55 1.46h4.7c.82 0 1.5-.64 1.55-1.46L16.5 7" />
      <path d="M10 10.5v5.5" />
      <path d="M14 10.5v5.5" />
    </svg>
  );
}
