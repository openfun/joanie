import * as React from "react";
import { PropsWithChildren, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function DashboardLayoutHeaderActions(props: PropsWithChildren) {
  const ref = useRef<Element | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    ref.current = document.querySelector<HTMLElement>("#header-actions");
    setMounted(true);
  }, []);

  return mounted && ref.current
    ? createPortal(<div>{props.children}</div>, ref.current)
    : null;
}
