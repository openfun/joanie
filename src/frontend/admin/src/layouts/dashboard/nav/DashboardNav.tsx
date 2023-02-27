import * as React from "react";
import Drawer from "@mui/material/Drawer";
import { useTheme } from "@mui/material";
import { DashboardNavHeader } from "@/layouts/dashboard/nav/header/DashboardNavHeader";
import { DashboardNavContent } from "@/layouts/dashboard/nav/content/DashboardNavContent";
import { NAVIGATION_WIDTH } from "@/layouts/dashboard/config";

interface Props {
  open: boolean;
  handleClose: () => void;
}

export function DashboardNav(props: Props) {
  const theme = useTheme();
  return (
    <>
      <Drawer
        sx={{
          width: NAVIGATION_WIDTH,
          padding: theme.spacing(2),
          display: { xs: "none", sm: "block" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            borderRight: "1px solid rgb(240, 240, 240)",
            backgroundColor: theme.palette.grey["50"],
            width: NAVIGATION_WIDTH,
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
      <Drawer
        sx={{
          width: NAVIGATION_WIDTH,
          display: { xs: "block", sm: "none" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: NAVIGATION_WIDTH,
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
    </>
  );
}
