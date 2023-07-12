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
import ListItemText from "@mui/material/ListItemText";
import ListItemIcon from "@mui/material/ListItemIcon";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import ExitToAppIcon from "@mui/icons-material/ExitToApp";
import { DashboardNavItem } from "@/layouts/dashboard/nav/item/DashboardNavItem";
import { DashboardNavItemsList } from "@/layouts/dashboard/nav/item/list/DasboardNavItemsList";
import { useAuthContext } from "@/components/auth/context/AuthContext";

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
  profile: {
    id: "layouts.dashboard.nav.account.profile",
    defaultMessage: "Profile",
    description: "Profile nav label",
  },
  logout: {
    id: "layouts.dashboard.nav.account.logout",
    defaultMessage: "Logout",
    description: "Logout nav label",
  },
});

export function DashboardLayoutNavAccount() {
  const authContext = useAuthContext();
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

  const logout = () => {
    authContext.updateUser(null);
    // AuthRepository.logout(() => {
    //   authContext.updateUser(null);
    // });
  };

  return (
    <Box>
      <DashboardNavItemsList
        subHeaderTitle={intl.formatMessage(messages.settingsSubHeader)}
      >
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
            <MenuItem onClick={handleCloseMenu}>
              <ListItemIcon>
                <AccountCircleIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>
                {intl.formatMessage(messages.profile)}
              </ListItemText>
            </MenuItem>
            <MenuItem
              onClick={() => {
                logout();
                handleCloseMenu();
              }}
            >
              <ListItemIcon>
                <ExitToAppIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{intl.formatMessage(messages.logout)}</ListItemText>
            </MenuItem>
          </Menu>
        </Box>
        <DashboardNavItem
          icon={<NotificationsIcon />}
          title={intl.formatMessage(messages.notificationNav)}
        />
      </DashboardNavItemsList>
    </Box>
  );
}
