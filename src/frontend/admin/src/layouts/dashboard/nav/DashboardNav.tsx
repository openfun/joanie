import * as React from "react";
import Drawer from "@mui/material/Drawer";
import { useTheme } from "@mui/material/styles";
import { DashboardNavHeader } from "@/layouts/dashboard/nav/header/DashboardNavHeader";
import { DashboardNavContent } from "@/layouts/dashboard/nav/content/DashboardNavContent";
import { useResponsive } from "@/hooks/useResponsive";

interface Props {
  open: boolean;
  handleClose: () => void;
}

export function DashboardNav(props: Props) {
  const theme = useTheme();
  const mdDown = useResponsive("down", "md");

  if (mdDown) {
    return (
      <Drawer
        sx={{
          width: theme.navigation.width,
          display: { xs: "block", sm: "block", md: "none" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: theme.navigation.width,
            boxSizing: "border-box",
          },
        }}
        variant="temporary"
        anchor="left"
        open={props.open}
        onClose={props.handleClose}
      >
        <DashboardNavHeader />
        <DashboardNavContent onChangeRoute={props.handleClose} />
      </Drawer>
    );
  }

  return (
    <Drawer
      sx={{
        width: theme.navigation.width,
        display: { xs: "none", sm: "none", md: "block" },
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          borderRight: "1px solid rgb(240, 240, 240)",
          backgroundColor: theme.palette.grey[50],
          width: theme.navigation.width,
          boxSizing: "border-box",
        },
      }}
      variant="persistent"
      anchor="left"
      open={props.open}
      onClose={props.handleClose}
    >
      <DashboardNavHeader />
      <DashboardNavContent />
    </Drawer>
  );
}
