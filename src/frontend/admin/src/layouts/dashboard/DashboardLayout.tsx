import * as React from "react";
import { PropsWithChildren, useState } from "react";
import { styled, useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";

import useMediaQuery from "@mui/material/useMediaQuery";
import { DashboardLayoutHeader } from "@/layouts/dashboard/header/DashboardLayoutHeader";
import { DashboardNav } from "@/layouts/dashboard/nav/DashboardNav";

type Props = {
  open?: boolean;
};
const Main = styled("main", {
  shouldForwardProp: (prop) => prop !== "open",
})<Props>(({ theme, open }) => {
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));

  return {
    width: `calc(100% - ${
      open && isDesktop ? theme.navigation.width : 0
    }px - ${theme.spacing(3)} - ${theme.spacing(3)})`,
    marginTop: theme.spacing(7),
    padding: theme.spacing(3),
    transition: theme.transitions.create("margin", {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: `-${theme.navigation.width}px`,
    [theme.breakpoints.down("md")]: {
      transition: "none",
      marginLeft: 0,
    },
    ...(open && {
      transition: theme.transitions.create("margin", {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen,
      }),
      marginLeft: 0,
    }),
  };
});

export function DashboardLayout(props: PropsWithChildren) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [open, setOpen] = useState(!isMobile);
  const handleToggleDrawer = () => {
    setOpen(!open);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  return (
    <Box sx={{ display: "flex" }}>
      <DashboardLayoutHeader
        open={open}
        onToggleNavigation={handleToggleDrawer}
      />
      <DashboardNav open={open} handleClose={handleDrawerClose} />

      <Main open={open}>{props.children}</Main>
    </Box>
  );
}
