import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconPartition(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4.5 5.5h11" />
      <path d="M4.5 10h11" />
      <path d="M4.5 14.5h7.5" />
      <path d="M15.5 5.5v9" />
      <path d="M9.5 5.5v9" />
      <path d="M4.5 5.5v9" />
    </NavIcon>
  );
}
