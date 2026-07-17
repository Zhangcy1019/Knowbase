import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconIngest(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M10 3.5v9" />
      <path d="M6.8 9.3 10 12.5l3.2-3.2" />
      <path d="M4.5 14.5v1a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-1" />
    </NavIcon>
  );
}
