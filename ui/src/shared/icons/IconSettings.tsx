import type { SVGProps } from "react";

import { NavIcon } from "./NavIcon";

export function IconSettings(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <circle cx="10" cy="10" r="2.3" />
      <path d="M10 3.5v1.7" />
      <path d="M10 14.8v1.7" />
      <path d="M3.5 10h1.7" />
      <path d="M14.8 10h1.7" />
      <path d="M5.4 5.4l1.2 1.2" />
      <path d="M13.4 13.4l1.2 1.2" />
      <path d="M14.6 5.4l-1.2 1.2" />
      <path d="M6.6 13.4l-1.2 1.2" />
    </NavIcon>
  );
}
