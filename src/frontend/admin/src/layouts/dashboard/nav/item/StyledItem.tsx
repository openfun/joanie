import { styled } from "@mui/material/styles";
import { alpha, ListItemButton, ListItemProps } from "@mui/material";

type StyledItemProps = ListItemProps & {
  isActive?: boolean;
};

export const NAV = {
  W_BASE: 260,
  W_DASHBOARD: 280,
  W_DASHBOARD_MINI: 88,
  //
  H_DASHBOARD_ITEM: 48,
  H_DASHBOARD_ITEM_SUB: 36,
  //
  H_DASHBOARD_ITEM_HORIZONTAL: 32,
};

export const StyledItem = styled(ListItemButton, {
  shouldForwardProp: (prop) => prop !== "isActive",
})<StyledItemProps>(({ isActive, theme }) => {
  const activeStyle = {
    color: theme.palette.primary.main,
    backgroundColor: alpha(
      theme.palette.primary.main,
      theme.palette.action.selectedOpacity
    ),
  };
  return {
    position: "relative",
    textTransform: "capitalize",
    maxHeight: "40px",
    paddingLeft: theme.spacing(2),
    paddingRight: theme.spacing(1.5),
    marginBottom: theme.spacing(0.5),
    color: theme.palette.text.secondary,
    borderRadius: theme.shape.borderRadius,
    height: NAV.H_DASHBOARD_ITEM,
    // Sub item

    // Active item
    ...(isActive && {
      ...activeStyle,
      "&:hover": {
        ...activeStyle,
      },
    }),
  };
});
