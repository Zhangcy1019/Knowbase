import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconBacklog(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4 6.5h12" />
      <path d="M4 10h12" />
      <path d="M4 13.5h8" />
      <path d="M14 13.5h2" />
      <path d="M5 4h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" />
    </NavIcon>
  );
}
