import * as React from "react";
import Drawer from "@mui/material/Drawer";
import { DashboardNavHeader } from "@/layouts/dashboard/nav/header/DashboardNavHeader";
import { DashboardNavContent } from "@/layouts/dashboard/nav/content/DashboardNavContent";
import { navigationWidth } from "@/layouts/dashboard/config";

interface Props {
  open: boolean;
  handleClose: () => void;
}

export function DashboardNav(props: Props) {
  return (
    <>
      <Drawer
        sx={{
          width: navigationWidth,
          padding: "10px",
          display: { xs: "none", sm: "block" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            borderRight: "1px solid rgb(240, 240, 240)",
            backgroundColor: "rgb(250, 250, 251)",
            width: navigationWidth,
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
          width: navigationWidth,
          display: { xs: "block", sm: "none" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: navigationWidth,
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
