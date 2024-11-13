import * as React from "react";
import { styled } from "@mui/material/styles";
import MuiAppBar, { AppBarProps as MuiAppBarProps } from "@mui/material/AppBar";
import IconButton from "@mui/material/IconButton";
import classNames from "classnames";
import MenuOpenIcon from "@mui/icons-material/MenuOpen";
import Toolbar from "@mui/material/Toolbar";
import styles from "./DashboardLayoutHeader.module.scss";

interface AppBarProps extends MuiAppBarProps {
  open?: boolean;
}

const AppBar = styled(MuiAppBar, {
  shouldForwardProp: (prop) => prop !== "open",
})<AppBarProps>(({ theme, open }) => ({
  transition: theme.transitions.create(["margin", "width"], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  boxShadow: "none",
  background: "none",
  padding: theme.spacing(1, 2, 1, 1),
  ...(open && {
    [theme.breakpoints.down("md")]: {
      transition: "none",
      marginLeft: 0,
    },
    [theme.breakpoints.up("md")]: {
      width: `calc(100% - ${theme.navigation.width}px)`,
      marginLeft: `0px`,
    },

    transition: theme.transitions.create(["margin", "width"], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));

interface Props {
  open: boolean;
  onToggleNavigation: () => void;
}

export function DashboardLayoutHeader({ open, ...props }: Props) {
  return (
    <AppBar color="inherit" position="fixed" open={open}>
      <Toolbar className={styles.headerContainer}>
        <IconButton
          size="small"
          className={classNames({
            [styles.openNavigationButton]: true,
            [styles.navigationIsOpen]: open,
          })}
          onClick={props.onToggleNavigation}
        >
          <MenuOpenIcon fontSize="small" />
        </IconButton>
        <div id="header-actions" />
      </Toolbar>
    </AppBar>
  );
}
