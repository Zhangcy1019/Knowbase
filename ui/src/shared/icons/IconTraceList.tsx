import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconTraceList(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <circle cx="5" cy="6" r="1.1" />
      <circle cx="5" cy="10" r="1.1" />
      <circle cx="5" cy="14" r="1.1" />
      <path d="M8 6h7" />
      <path d="M8 10h7" />
      <path d="M8 14h7" />
    </NavIcon>
  );
}
