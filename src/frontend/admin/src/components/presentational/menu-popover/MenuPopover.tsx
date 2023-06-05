import * as React from "react";
import { useState } from "react";
import Popover, { PopoverOrigin, PopoverProps } from "@mui/material/Popover";
import { MenuPopoverArrowValue } from "@/components/presentational/menu-popover/types";
import getPosition from "@/components/presentational/menu-popover/getPosition";

interface Props extends Omit<PopoverProps, "open"> {
  open: HTMLElement | null;
  arrow?: MenuPopoverArrowValue;
  disabledArrow?: boolean;
}

export function MenuPopover({
  open,
  children,
  arrow = "top-left",
  disabledArrow,
  sx,
  ...other
}: Props) {
  const { style, anchorOrigin, transformOrigin } = getPosition(arrow);

  return (
    <Popover
      open={Boolean(open)}
      anchorEl={open}
      anchorOrigin={anchorOrigin as PopoverOrigin}
      transformOrigin={transformOrigin as PopoverOrigin}
      PaperProps={{
        ...style,
        sx,
      }}
      {...other}
    >
      {children}
    </Popover>
  );
}

export const useMenuPopover = () => {
  const [openPopover, setOpenPopover] = useState<HTMLElement | null>(null);

  const open = (event: React.MouseEvent<HTMLElement>) => {
    setOpenPopover(event.currentTarget);
  };

  const close = () => {
    setOpenPopover(null);
  };

  return {
    isOpen: Boolean(openPopover),
    anchor: openPopover,
    open,
    close,
  };
};
