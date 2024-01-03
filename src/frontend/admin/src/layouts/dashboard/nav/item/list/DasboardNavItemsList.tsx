import * as React from "react";
import { PropsWithChildren } from "react";
import List from "@mui/material/List";
import ListSubheader from "@mui/material/ListSubheader";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import styles from "./DashboardNavItemsList.module.scss";

interface Props {
  subHeaderTitle: string;
}

export function DashboardNavItemsList(props: PropsWithChildren<Props>) {
  const theme = useTheme();
  return (
    <List
      className={styles.dashboardNavListContainer}
      subheader={
        <ListSubheader
          sx={{ backgroundColor: theme.palette.grey[50] + " !important" }}
          className={styles.navListSubHeader}
        >
          <Typography variant="subtitle2">{props.subHeaderTitle}</Typography>
        </ListSubheader>
      }
    >
      {props.children}
    </List>
  );
}
