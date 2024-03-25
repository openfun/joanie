import * as React from "react";
import { PropsWithChildren } from "react";
import Tooltip, { TooltipProps } from "@mui/material/Tooltip";

type Props = TooltipProps & {
  enableTooltip: boolean;
};
export function ConditionalTooltip({
  enableTooltip = true,
  children,
  ...tooltipProps
}: PropsWithChildren<Props>) {
  if (!enableTooltip) {
    return children;
  }

  return <Tooltip {...tooltipProps}>{children}</Tooltip>;
}
