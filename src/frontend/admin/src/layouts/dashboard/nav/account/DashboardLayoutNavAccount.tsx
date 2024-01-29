import * as React from "react";
import { useRef, useState } from "react";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { defineMessages, useIntl } from "react-intl";
import { useTheme } from "@mui/material/styles";
import { DashboardNavItemsList } from "@/layouts/dashboard/nav/item/list/DasboardNavItemsList";
import { useAuthContext } from "@/contexts/auth/AuthContext";
import { PATH_ADMIN } from "@/utils/routes/path";
import { CustomLink } from "@/components/presentational/link/CustomLink";

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
  djangoAdmin: {
    id: "layouts.dashboard.nav.account.djangoAdmin",
    defaultMessage: "Django admin",
    description: "Django admin link label",
  },
  logout: {
    id: "layouts.dashboard.nav.account.logout",
    defaultMessage: "Logout",
    description: "Logout label",
  },
  administrator: {
    id: "layouts.dashboard.nav.account.administrator",
    defaultMessage: "Administrator",
    description: "administrator label",
  },
});

type AccountMenuItem = {
  label: string;
  link?: string;
};

export function DashboardLayoutNavAccount() {
  const { user } = useAuthContext();
  const ref = useRef<HTMLButtonElement>(null);
  const [navAccountMenuIsOpen, setNavAccountMenuIsOpen] = useState(false);
  const intl = useIntl();
  const theme = useTheme();

  const menuItems: AccountMenuItem[] = [
    {
      label: intl.formatMessage(messages.djangoAdmin),
      link: process.env.NEXT_PUBLIC_DJANGO_ADMIN_BASE_URL,
    },
    {
      label: intl.formatMessage(messages.logout),
      link: PATH_ADMIN.auth.logout(),
    },
  ];

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
            <Avatar alt={user.username}>
              {user.username[0].toUpperCase()}
            </Avatar>
            <div>
              <Typography>{user.username}</Typography>
              <Typography color="text.secondary" variant="caption">
                {intl.formatMessage(messages.administrator)}
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
            {menuItems.map((item) => (
              <MenuItem
                onClick={() => {
                  handleCloseMenu();
                }}
              >
                {item.link && (
                  <CustomLink href={item.link}>{item.label}</CustomLink>
                )}
                {!item.link && item.label}
              </MenuItem>
            ))}
          </Menu>
        </Box>
      </DashboardNavItemsList>
    </Box>
  );
}
