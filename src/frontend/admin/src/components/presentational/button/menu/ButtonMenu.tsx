import * as React from "react";
import { ReactElement, useRef, useState } from "react";
import Button, { ButtonProps } from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { CustomMenuItem } from "@/components/presentational/menu-popover/CustomMenuItem";

export type MenuOption = {
  icon?: ReactElement<any>;
  mainLabel: string;
  rightLabel?: string | ReactElement;
  isDisable?: boolean;
  disableMessage?: string;
  onClick?: () => void;
};

export type ButtonMenuProps = ButtonProps & {
  label: string;
  id: string;
  options: MenuOption[];
};

export default function ButtonMenu({
  id,
  label,
  options = [],
  ...buttonProps
}: ButtonMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLButtonElement>(null);

  const handleOpenMenu = () => {
    setIsOpen(true);
  };

  const handleCloseMenu = () => {
    setIsOpen(false);
  };

  return (
    <div>
      <Button
        aria-controls={isOpen ? `${id}-menu` : undefined}
        aria-haspopup="true"
        aria-expanded={isOpen ? "true" : undefined}
        ref={ref}
        id={id}
        {...buttonProps}
        onClick={handleOpenMenu}
        endIcon={<KeyboardArrowDownIcon />}
      >
        {label}
      </Button>
      <Menu
        id={`${id}-menu`}
        anchorEl={ref.current}
        open={isOpen}
        onClose={handleCloseMenu}
        MenuListProps={{
          "aria-labelledby": id,
        }}
      >
        {options.map((menuOption) => (
          <CustomMenuItem
            handleClose={handleCloseMenu}
            menuOption={menuOption}
          />
        ))}
      </Menu>
    </div>
  );
}
