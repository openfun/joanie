import * as React from "react";
import { ReactNode } from "react";
import Drawer from "@mui/material/Drawer";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import { DashboardNavHeader } from "@/layouts/dashboard/nav/header/DashboardNavHeader";
import { DashboardNavContent } from "@/layouts/dashboard/nav/content/DashboardNavContent";
import { useResponsive } from "@/hooks/useResponsive";
import { DashboardNavSelectLang } from "@/layouts/dashboard/nav/DashboardNavSelectLang";

interface Props {
  open: boolean;
  handleClose: () => void;
}

export function DashboardNav(props: Props) {
  const theme = useTheme();
  const mdDown = useResponsive("down", "md");

  const getContent = (): ReactNode => {
    return (
      <Box
        sx={{
          height: "100%",
          flexDirection: "column",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ flexDirection: "column", display: "flex", flexGrow: 1 }}>
          <DashboardNavHeader />
          <DashboardNavContent
            onChangeRoute={mdDown ? props.handleClose : undefined}
          />
        </Box>
        <DashboardNavSelectLang />
      </Box>
    );
  };

  if (mdDown) {
    return (
      <Drawer
        sx={{
          width: theme.navigation.width,
          display: { xs: "block", sm: "block", md: "none" },
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: theme.navigation.width,
            backgroundColor: theme.palette.grey[50],
            boxSizing: "border-box",
          },
        }}
        variant="temporary"
        anchor="left"
        open={props.open}
        onClose={props.handleClose}
      >
        {getContent()}
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
      {getContent()}
    </Drawer>
  );
}
