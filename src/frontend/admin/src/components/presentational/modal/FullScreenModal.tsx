import Slide from "@mui/material/Slide";
import * as React from "react";
import { PropsWithChildren } from "react";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import { useTheme } from "@mui/material/styles";
import Container from "@mui/material/Container";
import { CustomModalProps } from "@/components/presentational/modal/Modal";

type Props = Omit<CustomModalProps, "fullScreen" | "fullWidth"> & {};
export function FullScreenModal({
  disablePadding = false,
  title,
  open,
  handleClose,
  actions,
  children,
}: PropsWithChildren<Props>) {
  const theme = useTheme();
  return (
    <Dialog
      fullScreen
      open={open}
      onClose={handleClose}
      TransitionComponent={Transition}
    >
      <DialogTitle
        bgcolor={
          theme.palette.mode === "dark"
            ? theme.palette.grey[900]
            : theme.palette.grey[100]
        }
      >
        <IconButton
          edge="start"
          color="inherit"
          sx={{ mr: 1 }}
          onClick={handleClose}
          aria-label="close"
        >
          <CloseIcon />
        </IconButton>
        {title}
      </DialogTitle>
      <DialogContent sx={{ mt: 2, padding: disablePadding ? 0 : 3 }}>
        <Container maxWidth="lg">{children}</Container>
      </DialogContent>
      {actions && <DialogActions>{actions}</DialogActions>}
    </Dialog>
  );
}

const Transition = React.forwardRef(function Transition(
  props: PropsWithChildren<{}>,
  ref,
) {
  return (
    <Slide direction="up" ref={ref} {...props}>
      {props.children as React.ReactElement}
    </Slide>
  );
});
