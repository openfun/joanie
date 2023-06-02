import * as React from "react";
import { ReactElement } from "react";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import styles from "./DashboardNavItem.module.scss";
import { StyledItem } from "@/layouts/dashboard/nav/item/StyledItem";

interface Props {
  icon: ReactElement;
  title: string;
  isActive?: boolean;
  onClick?: () => void;
}

export function DashboardNavItem({
  icon,
  title,
  isActive = false,
  ...props
}: Props) {
  return (
    <StyledItem key={title} onClick={props.onClick} isActive={isActive}>
      <ListItemIcon className={styles.dashboardNavItem}>
        {React.cloneElement(icon, {
          color: isActive ? "primary" : "",
        })}
      </ListItemIcon>
      <ListItemText
        primary={
          <Typography variant="caption" color="text.secondary">
            {title}
          </Typography>
        }
      />
    </StyledItem>
  );
}
