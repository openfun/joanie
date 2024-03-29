import * as React from "react";
import { ReactNode } from "react";
import Button, { ButtonOwnProps } from "@mui/material/Button";
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
  message: string | ReactNode;
  handleAccept: () => void;
  validateLabel?: string;
  closeOnAccept?: boolean;
  validateColorButton?: ButtonOwnProps["color"];
}

export function AlertModal({
  handleAccept,
  validateLabel,
  validateColorButton,
  message,
  closeOnAccept = true,
  ...modalProps
}: AlertModalProps) {
  const intl = useIntl();
  const onHandleAccept = (): void => {
    if (closeOnAccept) {
      modalProps.handleClose();
    }
    handleAccept();
  };

  return (
    <CustomModal
      {...modalProps}
      actions={
        <>
          <Button onClick={modalProps.handleClose}>
            {intl.formatMessage(messages.cancel)}
          </Button>
          <Button
            onClick={onHandleAccept}
            color={validateColorButton}
            autoFocus
          >
            {validateLabel ?? intl.formatMessage(messages.validate)}
          </Button>
        </>
      }
    >
      <DialogContentText>{message}</DialogContentText>
    </CustomModal>
  );
}
