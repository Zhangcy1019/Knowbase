import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconQuery(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4.5 5.5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H9l-3.5 3v-3H6.5a2 2 0 0 1-2-2v-5Z" />
      <path d="M7.4 8h5.2" />
      <path d="M7.4 10.5h3.6" />
    </NavIcon>
  );
}
