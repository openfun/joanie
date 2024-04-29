import * as React from "react";
import MenuItem from "@mui/material/MenuItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { ConditionalTooltip } from "@/components/presentational/tooltip/ConditionalTooltip";
import { MenuOption } from "@/components/presentational/button/menu/ButtonMenu";

type Props = {
  handleClose: () => void;
  menuOption: MenuOption;
};
export function CustomMenuItem({ handleClose, menuOption }: Props) {
  return (
    <ConditionalTooltip
      key={menuOption.mainLabel}
      enableTooltip={!!menuOption?.isDisable}
      title={menuOption.disableMessage ?? ""}
    >
      <span data-testid={menuOption.mainLabel}>
        <MenuItem
          disabled={!!menuOption?.isDisable}
          onClick={() => {
            handleClose();
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
      </span>
    </ConditionalTooltip>
  );
}
