import * as React from "react";
import { MouseEvent, ReactElement, useMemo, useState } from "react";
import Popover, { PopoverOrigin, PopoverProps } from "@mui/material/Popover";
import MoreVertOutlinedIcon from "@mui/icons-material/MoreVertOutlined";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import MenuList from "@mui/material/MenuList";
import { MenuPopoverArrowValue } from "@/components/presentational/menu-popover/types";
import getPosition from "@/components/presentational/menu-popover/getPosition";

export interface ActionMenuPopoverItem {
  title: string;
  icon?: ReactElement;
  onClick?: () => void;
}

interface Props extends Omit<PopoverProps, "open"> {
  button?: ReactElement;
  menuItems: ActionMenuPopoverItem[];
  arrow?: MenuPopoverArrowValue;
  disabledArrow?: boolean;
  id?: string;
}

export function MenuPopover({
  menuItems,
  arrow = "top-left",
  disabledArrow,
  sx,
  ...other
}: Props) {
  const { style, anchorOrigin, transformOrigin } = getPosition(arrow);
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);

  const button = useMemo(() => {
    const id = other.id ?? "ActionMenuPopover";
    if (other.button) {
      return React.cloneElement(other.button, {
        onClick: handleClick,
        "data-testid": id,
      });
    }
    return (
      <IconButton data-testid={id} onClick={handleClick}>
        <MoreVertOutlinedIcon />
      </IconButton>
    );
  }, [other.button, open]);

  return (
    <>
      {button}
      <Popover
        open={Boolean(open)}
        anchorEl={anchorEl}
        anchorOrigin={anchorOrigin as PopoverOrigin}
        onClose={handleClose}
        transformOrigin={transformOrigin as PopoverOrigin}
        slotProps={{
          paper: {
            ...style,
            sx,
          },
        }}
        {...other}
      >
        <MenuList>
          {menuItems.map((item) => {
            return (
              <MenuItem
                onClick={() => {
                  handleClose();
                  item.onClick?.();
                }}
                key={item.title}
              >
                {item.icon && <ListItemIcon>{item.icon}</ListItemIcon>}
                <ListItemText>{item.title}</ListItemText>
              </MenuItem>
            );
          })}
        </MenuList>
      </Popover>
    </>
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
