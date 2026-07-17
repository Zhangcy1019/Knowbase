import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconTraceLoop(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M6 5.5h6a3 3 0 0 1 0 6H8.5" />
      <path d="M8.5 9 6 11.5 8.5 14" />
    </NavIcon>
  );
}
