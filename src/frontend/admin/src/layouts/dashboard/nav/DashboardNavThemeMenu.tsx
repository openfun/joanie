import { useState } from "react";
import { defineMessages, useIntl, FormattedMessage } from "react-intl";
import { useColorScheme } from "@mui/material/styles";
import Button from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import DarkMode from "@mui/icons-material/DarkMode";
import LightMode from "@mui/icons-material/LightMode";
import SettingsBrightness from "@mui/icons-material/SettingsBrightness";

type SchemeModes = "light" | "dark" | "system";

const messages = defineMessages({
  buttonAriaLabel: {
    id: "dashboard.nav.DashboardNavThemeMenu.buttonAriaLabel",
    defaultMessage: "Open color schemes menu",
    description: "Aria label of button to open color scheme menu",
  },
  light: {
    id: "dashboard.nav.DashboardNavThemeMenu.light",
    defaultMessage: "Light",
    description: "Label for light theme button",
  },
  dark: {
    id: "dashboard.nav.DashboardNavThemeMenu.dark",
    defaultMessage: "Dark",
    description: "Label for dark theme button",
  },
  system: {
    id: "dashboard.nav.DashboardNavThemeMenu.system",
    defaultMessage: "System",
    description: "Label for system theme button",
  },
});

const MODE_ICONS = {
  light: LightMode,
  dark: DarkMode,
  system: SettingsBrightness,
};

export function DashboardNavThemeMenu() {
  const intl = useIntl();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const { mode: activeMode, setMode } = useColorScheme();
  const ActiveModeIcon = MODE_ICONS[activeMode ?? "system"];

  const updateMode = (nextMode: SchemeModes) => {
    setMode(nextMode);
    handleClose();
  };

  return (
    <>
      <Button
        id="mode-menu-open-button"
        title={intl.formatMessage(messages.buttonAriaLabel)}
        aria-label={intl.formatMessage(messages.buttonAriaLabel)}
        aria-controls={open ? "basic-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={open ? "true" : undefined}
        onClick={handleClick}
        color="inherit"
        sx={{
          color: "text.secondary",
          minWidth: "80px",
        }}
      >
        <ActiveModeIcon />
      </Button>
      <Menu
        id="mode-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          "aria-labelledby": "basic-button",
        }}
      >
        {(["light", "dark", "system"] as SchemeModes[]).map((mode) => (
          <ModeMenuItem
            mode={mode}
            key={`menu-item-${mode}`}
            onClick={() => updateMode(mode)}
          />
        ))}
      </Menu>
    </>
  );
}

type ModeMenuItemProps = {
  mode: SchemeModes;
} & React.ComponentProps<typeof MenuItem>;

function ModeMenuItem({ mode, ...props }: ModeMenuItemProps) {
  const ModeIcon = MODE_ICONS[mode];

  return (
    <MenuItem {...props}>
      <ModeIcon sx={{ mr: 2 }} fontSize="small" />
      <FormattedMessage {...messages[mode]} />
    </MenuItem>
  );
}
