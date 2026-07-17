import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconRuns(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4 5v10" />
      <path d="M10 5v10" />
      <path d="M16 5v10" />
      <circle cx="4" cy="8" r="1.6" />
      <circle cx="10" cy="12" r="1.6" />
      <circle cx="16" cy="7" r="1.6" />
      <path d="M5.5 8h3" />
      <path d="M11.5 11.2h3" />
    </NavIcon>
  );
}
