import * as React from "react";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Image from "next/image";
import Typography from "@mui/material/Typography";
import styles from "@/layouts/dashboard/nav/DashboardLayoutNav.module.scss";

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
  return (
    <DrawerHeader>
      <Box className={styles.headerContent}>
        <Image
          src="/images/logo/logo-fun.svg"
          height={55}
          width={55}
          alt="FunMooc logo"
        />
        <Typography marginLeft="10px">Joanie Admin</Typography>
      </Box>
    </DrawerHeader>
  );
}
