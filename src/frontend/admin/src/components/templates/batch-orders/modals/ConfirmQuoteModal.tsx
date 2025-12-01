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
    id: "components.templates.batch-orders.modals.confirmQuoteModal.cancel",
    defaultMessage: "Cancel",
    description: "Cancel button label for confirm quote modal",
  },
  confirm: {
    id: "components.templates.batch-orders.modals.confirmQuoteModal.confirm",
    defaultMessage: "Confirm",
    description: "Confirm button label for confirm quote modal",
  },
  description: {
    id: "components.templates.batch-orders.modals.confirmQuoteModal.description",
    defaultMessage:
      "Enter the total amount to confirm the quote for this batch order.",
    description: "Description text for confirm quote modal",
  },
  totalLabel: {
    id: "components.templates.batch-orders.modals.confirmQuoteModal.totalLabel",
    defaultMessage: "Total amount",
    description: "Label for total amount input field",
  },
  totalPlaceholder: {
    id: "components.templates.batch-orders.modals.confirmQuoteModal.totalPlaceholder",
    defaultMessage: "e.g., 123.45",
    description: "Placeholder for total amount input field",
  },
});

export interface ConfirmQuoteModalProps extends CustomModalProps {
  onConfirm: (total: string) => void;
}

export function ConfirmQuoteModal({
  onConfirm,
  ...modalProps
}: ConfirmQuoteModalProps) {
  const intl = useIntl();
  const [total, setTotal] = useState("");

  const handleConfirm = (): void => {
    if (total.trim()) {
      onConfirm(total);
      modalProps.handleClose();
      setTotal("");
    }
  };

  const handleCancel = (): void => {
    modalProps.handleClose();
    setTotal("");
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
            disabled={!total.trim()}
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
        label={intl.formatMessage(messages.totalLabel)}
        placeholder={intl.formatMessage(messages.totalPlaceholder)}
        value={total}
        onChange={(e) => setTotal(e.target.value)}
        type="number"
        inputProps={{
          "data-testid": "confirm-quote-total-input",
        }}
      />
    </CustomModal>
  );
}
