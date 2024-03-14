import * as React from "react";
import { ReactElement, useRef, useState } from "react";
import Button, { ButtonProps } from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";

export type MenuOption = {
  icon?: ReactElement;
  mainLabel: string;
  rightLabel?: string | ReactElement;
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
          <MenuItem
            key={menuOption.mainLabel}
            onClick={() => {
              handleCloseMenu();
              menuOption.onClick?.();
            }}
          >
            {menuOption.icon &&
              React.cloneElement(menuOption.icon, {
                fontSize: "small",
                sx: { mr: 1 },
              })}
            <ListItemText sx={{ mr: menuOption.rightLabel ? 3 : 0 }}>
              {menuOption.mainLabel}
            </ListItemText>
            {menuOption.rightLabel &&
              typeof menuOption.rightLabel === "string" && (
                <Typography variant="body2" color="text.secondary">
                  {menuOption.rightLabel}
                </Typography>
              )}
            {menuOption.rightLabel &&
              typeof menuOption.rightLabel !== "string" &&
              menuOption.rightLabel}
          </MenuItem>
        ))}
      </Menu>
    </div>
  );
}
