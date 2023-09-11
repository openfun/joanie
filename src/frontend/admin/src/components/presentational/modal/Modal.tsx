import * as React from "react";
import { PropsWithChildren, ReactElement } from "react";
import Dialog, { DialogProps } from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

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
      <DialogContent sx={{ padding: disablePadding ? 0 : 3 }}>
        {children}
      </DialogContent>
      {actions && <DialogActions>{actions}</DialogActions>}
    </Dialog>
  );
}
