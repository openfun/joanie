import { styled } from "@mui/material/styles";
import { Box, BoxProps } from "@mui/material";

type StyledDndItemContainerProps = BoxProps & {
  showHandle?: boolean;
};

export const StyledDndItemContainer = styled(Box, {
  shouldForwardProp: (prop) => prop !== "showHandle",
})<StyledDndItemContainerProps>(({ showHandle, theme }) => {
  return {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: theme.spacing(1),
    position: "relative",
    "&:hover": {
      ".dnd-handle": {
        opacity: showHandle ? 0 : 1,
      },
    },
  };
});
