import * as React from "react";
import { useMemo, useState } from "react";
import { Avatar, Box, Menu, MenuItem, Typography } from "@mui/material";
import IconButton from "@mui/material/IconButton";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import NotificationsIcon from "@mui/icons-material/Notifications";
import { defineMessages, useIntl } from "react-intl";
import { faker } from "@faker-js/faker";
import styles from "./DashboardLayoutNavAccount.module.scss";
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
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const intl = useIntl();

  const avatarUrl = useMemo(() => {
    return faker.image.cats();
  }, []);

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
  };

  return (
    <Box className={styles.navSettingsContainer}>
      <DashboardNavItemsList
        subHeaderTitle={intl.formatMessage(messages.settingsSubHeader)}
      >
        <DashboardNavItem
          icon={<NotificationsIcon />}
          title={intl.formatMessage(messages.notificationNav)}
        />
        <div className={styles.navAvatarContainer}>
          <div className={styles.navAvatar}>
            <Avatar alt="John Doe" src={avatarUrl} />
            <div>
              <Typography>Nathan</Typography>
              <Typography color="text.secondary" variant="caption">
                Administrator
              </Typography>
            </div>
          </div>
          <IconButton onClick={handleOpenMenu}>
            <KeyboardArrowDownIcon />
          </IconButton>

          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
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
            open={Boolean(anchorEl)}
            onClose={handleCloseMenu}
          >
            <MenuItem onClick={handleCloseMenu}>Profile</MenuItem>
            <MenuItem onClick={handleCloseMenu}>My account</MenuItem>
          </Menu>
        </div>
      </DashboardNavItemsList>
    </Box>
  );
}
