import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconTraceDetail(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M6 4.5h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 14 15.5H6A1.5 1.5 0 0 1 4.5 14V6A1.5 1.5 0 0 1 6 4.5Z" />
      <path d="M7.5 8h5" />
      <path d="M7.5 10.5h5" />
      <path d="M7.5 13h3.2" />
    </NavIcon>
  );
}
