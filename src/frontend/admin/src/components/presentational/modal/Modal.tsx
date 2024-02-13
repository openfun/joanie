import * as React from "react";
import { PropsWithChildren, ReactElement } from "react";
import Dialog, { DialogProps } from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

export interface CustomModalProps extends DialogProps {
  title: string;
  open: boolean;
  handleOpen?: () => void;
  handleClose: () => void;
  toggleModal?: () => void;
  actions?: ReactElement;
  disablePadding?: boolean;
}

export function CustomModal({
  disablePadding = false,
  title,
  open,
  handleClose,
  actions,
  children,
  handleOpen,
  toggleModal,
  ...props
}: PropsWithChildren<CustomModalProps>) {
  return (
    <Dialog {...props} open={open} onClose={handleClose}>
      <DialogTitle>{title}</DialogTitle>
      <IconButton
        aria-label="close"
        onClick={handleClose}
        sx={{
          position: "absolute",
          right: 8,
          top: 8,
          color: (theme) => theme.palette.grey[500],
        }}
      >
        <CloseIcon />
      </IconButton>
      <DialogContent sx={{ padding: disablePadding ? 0 : 3 }}>
        {children}
      </DialogContent>
      {actions && <DialogActions>{actions}</DialogActions>}
    </Dialog>
  );
}
