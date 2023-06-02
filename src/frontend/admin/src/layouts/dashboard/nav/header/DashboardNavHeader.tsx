import * as React from "react";
import { styled, useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Image from "next/image";
import logo from "@/../public/images/logo/logo-fun.svg";

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
        <Image src={logo} width={150} alt="France Université Numérique logo" />
      </Box>
    </DrawerHeader>
  );
}
