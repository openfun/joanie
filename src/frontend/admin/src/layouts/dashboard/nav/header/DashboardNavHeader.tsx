import * as React from "react";
import { styled, useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Image from "next/image";
import { defineMessages, useIntl } from "react-intl";
import logoLight from "@/../public/images/logo/logo-fun-light.svg";
import logoDark from "@/../public/images/logo/logo-fun-dark.svg";
import { CustomLink } from "@/components/presentational/link/CustomLink";
import { PATH_ADMIN } from "@/utils/routes/path";

const message = defineMessages({
  goBackToHome: {
    id: "layouts.dashboard.nav.header.DashboardNavHeader",
    defaultMessage: "Back to the homepage",
    description: "aria-label for the go back home link",
  },
});

const DrawerHeader = styled("div")(({ theme }) => {
  return {
    display: "flex",
    alignItems: "center",
    padding: theme.spacing(0, 2),
    // necessary for content to be below app bar
    ...theme.mixins.toolbar,
    justifyContent: "flex-start",
  };
});

export function DashboardNavHeader() {
  const theme = useTheme();
  const intl = useIntl();
  return (
    <DrawerHeader>
      <Box
        sx={{
          display: "flex",
          width: "100%",
          marginBottom: theme.spacing(2),
          justifyContent: "center",
          alignItems: "center",
          padding: theme.spacing(2),
        }}
      >
        <CustomLink
          href={PATH_ADMIN.rootAdmin}
          title={intl.formatMessage(message.goBackToHome)}
        >
          <Image
            src={theme.palette.mode === "light" ? logoLight : logoDark}
            width={150}
            alt="France Université Numérique logo"
          />
        </CustomLink>
      </Box>
    </DrawerHeader>
  );
}
