import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconTraceFocus(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <circle cx="10" cy="10" r="5.1" />
      <circle cx="10" cy="10" r="1.5" />
    </NavIcon>
  );
}
