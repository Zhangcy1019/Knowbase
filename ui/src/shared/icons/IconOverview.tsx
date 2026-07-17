import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconOverview(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <rect x="3" y="3" width="5" height="5" rx="1.2" />
      <rect x="12" y="3" width="5" height="5" rx="1.2" />
      <rect x="3" y="12" width="5" height="5" rx="1.2" />
      <rect x="12" y="12" width="5" height="5" rx="1.2" />
    </NavIcon>
  );
}
