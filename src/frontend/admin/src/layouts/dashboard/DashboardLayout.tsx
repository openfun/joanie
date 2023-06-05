import * as React from "react";
import { PropsWithChildren, useState } from "react";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import { DashboardLayoutHeader } from "@/layouts/dashboard/header/DashboardLayoutHeader";
import { DashboardNav } from "@/layouts/dashboard/nav/DashboardNav";

const Main = styled("main", { shouldForwardProp: (prop) => prop !== "open" })<{
  open?: boolean;
}>(({ theme, open }) => ({
  flexGrow: 1,
  marginTop: theme.spacing(7),
  padding: theme.spacing(3),
  transition: theme.transitions.create("margin", {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: `-${theme.navigation.width}px`,
  [theme.breakpoints.down("sm")]: {
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
}));

export function DashboardLayout(props: PropsWithChildren) {
  const [open, setOpen] = useState(true);
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
