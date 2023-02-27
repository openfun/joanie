import * as React from "react";
import { PropsWithChildren } from "react";
import { List, ListSubheader, Typography } from "@mui/material";
import styles from "./DashboardNavItemsList.module.scss";

interface Props {
  subHeaderTitle: string;
}

export function DashboardNavItemsList(props: PropsWithChildren<Props>) {
  return (
    <List
      className={styles.dashboardNavListContainer}
      subheader={
        <ListSubheader className={styles.navListSubHeader}>
          <Typography variant="subtitle2">{props.subHeaderTitle}</Typography>
        </ListSubheader>
      }
    >
      {props.children}
    </List>
  );
}
