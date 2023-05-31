import * as React from "react";
import { PropsWithChildren, ReactElement } from "react";
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";

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
