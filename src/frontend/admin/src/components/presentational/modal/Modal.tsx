import * as React from "react";
import { PropsWithChildren, ReactElement } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

export interface CustomModalProps {
  title: string;
  open: boolean;
  handleClose: () => void;
  actions?: ReactElement;
}

export function CustomModal(props: PropsWithChildren<CustomModalProps>) {
  return (
    <Dialog open={props.open} onClose={props.handleClose}>
      <DialogTitle>{props.title}</DialogTitle>
      <DialogContent>{props.children}</DialogContent>
      {props.actions && <DialogActions>{props.actions}</DialogActions>}
    </Dialog>
  );
}
