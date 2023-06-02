import * as React from "react";
import { useRef, useState } from "react";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import NotificationsIcon from "@mui/icons-material/Notifications";
import { defineMessages, useIntl } from "react-intl";
import { useTheme } from "@mui/material/styles";
import { DashboardNavItem } from "@/layouts/dashboard/nav/item/DashboardNavItem";
import { DashboardNavItemsList } from "@/layouts/dashboard/nav/item/list/DasboardNavItemsList";

const messages = defineMessages({
  settingsSubHeader: {
    id: "layouts.dashboard.nav.account.settingsSubHeader",
    defaultMessage: "Account and settings",
    description: "Account subheader nav label",
  },
  notificationNav: {
    id: "layouts.dashboard.nav.account.notificationNav",
    defaultMessage: "Notifications",
    description: "Notifications navigation label",
  },
});

export function DashboardLayoutNavAccount() {
  const ref = useRef<HTMLButtonElement>(null);
  const [navAccountMenuIsOpen, setNavAccountMenuIsOpen] = useState(false);
  const intl = useIntl();
  const theme = useTheme();

  const handleOpenMenu = () => {
    setNavAccountMenuIsOpen(true);
  };

  const handleCloseMenu = () => {
    setNavAccountMenuIsOpen(false);
  };

  return (
    <Box>
      <DashboardNavItemsList
        subHeaderTitle={intl.formatMessage(messages.settingsSubHeader)}
      >
        <DashboardNavItem
          icon={<NotificationsIcon />}
          title={intl.formatMessage(messages.notificationNav)}
        />
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: `0 ${theme.spacing(2)}`,
            margin: `${theme.spacing(2)} 0`,
          }}
        >
          <Box display="flex" alignItems="center" gap="10px">
            <Avatar alt="John Doe">JD</Avatar>
            <div>
              <Typography>John</Typography>
              <Typography color="text.secondary" variant="caption">
                Administrator
              </Typography>
            </div>
          </Box>
          <IconButton ref={ref} onClick={handleOpenMenu}>
            <KeyboardArrowDownIcon />
          </IconButton>

          <Menu
            id="menu-appbar"
            anchorEl={ref.current}
            anchorOrigin={{
              vertical: "bottom",
              horizontal: "right",
            }}
            keepMounted
            elevation={1}
            transformOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
            open={navAccountMenuIsOpen}
            onClose={handleCloseMenu}
          >
            <MenuItem onClick={handleCloseMenu}>Profile</MenuItem>
            <MenuItem onClick={handleCloseMenu}>My account</MenuItem>
          </Menu>
        </Box>
      </DashboardNavItemsList>
    </Box>
  );
}
