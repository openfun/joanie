import * as React from "react";
import Button from "@mui/material/Button";
import DialogContentText from "@mui/material/DialogContentText";
import { defineMessages, useIntl } from "react-intl";
import {
  CustomModal,
  CustomModalProps,
} from "@/components/presentational/modal/Modal";

const messages = defineMessages({
  cancel: {
    id: "components.modal.alterModal.cancel",
    defaultMessage: "Cancel",
    description: "Cancel CTA label for alert modal",
  },
  validate: {
    id: "components.modal.alterModal.validate",
    defaultMessage: "Validate",
    description: "Validate CTA label for alert modal",
  },
});

export interface AlertModalProps extends CustomModalProps {
  message: string;
  handleAccept: () => void;
  validateLabel?: string;
}

export function AlertModal(props: AlertModalProps) {
  const intl = useIntl();
  const handleAccept = (): void => {
    props.handleClose();
    props.handleAccept();
  };

  return (
    <CustomModal
      {...props}
      actions={
        <>
          <Button onClick={props.handleClose}>
            {intl.formatMessage(messages.cancel)}
          </Button>
          <Button onClick={handleAccept} autoFocus>
            {props.validateLabel ?? intl.formatMessage(messages.validate)}
          </Button>
        </>
      }
    >
      <DialogContentText>{props.message}</DialogContentText>
    </CustomModal>
  );
}
