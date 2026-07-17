import type { PropsWithChildren, SVGProps } from "react";

export function NavIcon({ children, ...props }: PropsWithChildren<SVGProps<SVGSVGElement>>) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}
