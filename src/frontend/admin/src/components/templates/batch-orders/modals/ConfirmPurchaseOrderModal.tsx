import * as React from "react";
import { useState } from "react";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import DialogContentText from "@mui/material/DialogContentText";
import { defineMessages, useIntl } from "react-intl";
import {
  CustomModal,
  CustomModalProps,
} from "@/components/presentational/modal/Modal";

const messages = defineMessages({
  cancel: {
    id: "components.templates.batch-orders.modals.confirmPurchaseOrderModal.cancel",
    defaultMessage: "Cancel",
    description: "Cancel button label for confirm purchase order modal",
  },
  confirm: {
    id: "components.templates.batch-orders.modals.confirmPurchaseOrderModal.confirm",
    defaultMessage: "Confirm",
    description: "Confirm button label for confirm purchase order modal",
  },
  description: {
    id: "components.templates.batch-orders.modals.confirmPurchaseOrderModal.description",
    defaultMessage:
      "Enter the purchase order reference to confirm the purchase order for this batch order.",
    description: "Description text for confirm purchase order modal",
  },
  referenceLabel: {
    id: "components.templates.batch-orders.modals.confirmPurchaseOrderModal.referenceLabel",
    defaultMessage: "Purchase order reference",
    description: "Label for purchase order reference input field",
  },
});

export interface ConfirmPurchaseOrderModalProps extends CustomModalProps {
  onConfirm: (reference: string) => void;
}

export function ConfirmPurchaseOrderModal({
  onConfirm,
  ...modalProps
}: ConfirmPurchaseOrderModalProps) {
  const intl = useIntl();
  const [reference, setReference] = useState("");

  const handleConfirm = (): void => {
    if (reference.trim()) {
      onConfirm(reference);
      modalProps.handleClose();
      setReference("");
    }
  };

  const handleCancel = (): void => {
    modalProps.handleClose();
    setReference("");
  };

  return (
    <CustomModal
      {...modalProps}
      actions={
        <>
          <Button onClick={handleCancel}>
            {intl.formatMessage(messages.cancel)}
          </Button>
          <Button
            onClick={handleConfirm}
            color="primary"
            variant="contained"
            disabled={!reference.trim()}
          >
            {intl.formatMessage(messages.confirm)}
          </Button>
        </>
      }
    >
      <DialogContentText sx={{ mb: 2 }}>
        {intl.formatMessage(messages.description)}
      </DialogContentText>
      <TextField
        autoFocus
        fullWidth
        label={intl.formatMessage(messages.referenceLabel)}
        value={reference}
        onChange={(e) => setReference(e.target.value)}
        type="text"
        inputProps={{
          "data-testid": "confirm-purchase-order-reference-input",
        }}
      />
    </CustomModal>
  );
}
