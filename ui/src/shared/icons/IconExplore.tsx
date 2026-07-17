import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconExplore(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M6 3.5h6l3 3v10A1.5 1.5 0 0 1 13.5 18h-7A1.5 1.5 0 0 1 5 16.5v-11A2 2 0 0 1 7 3.5Z" />
      <path d="M12 3.5v3h3" />
      <path d="M7.5 10h5" />
      <path d="M7.5 13h5" />
    </NavIcon>
  );
}
