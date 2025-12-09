import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DrawIcon from "@mui/icons-material/Draw";
import PlaylistAddCheckIcon from "@mui/icons-material/PlaylistAddCheck";
import { BatchOrder } from "@/services/api/models/BatchOrder";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import {
  useBatchOrder,
  useBatchOrders,
} from "@/hooks/useBatchOrders/useBatchOrders";
import { useModal } from "@/components/presentational/modal/useModal";
import { ConfirmQuoteModal } from "@/components/templates/batch-orders/modals/ConfirmQuoteModal";
import { batchOrderActionsMessages } from "@/components/templates/batch-orders/view/translations";

const messages = defineMessages({
  batchOrderActionsLabel: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.batchOrderActionsLabel",
    description: "Label for the actions button",
    defaultMessage: "Actions",
  },
  alreadyCancelTooltip: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.alreadyCancelTooltip",
    description: "Text when the batch order has already been canceled",
    defaultMessage: "The batch order has already been canceled",
  },
  isNotCanceled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.isNotCanceled",
    description: "Text when the batch order is not canceled",
    defaultMessage: "You must cancel the batch order before refunding it.",
  },
  confirmQuoteDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmQuoteDisabled",
    description: "Text when the batch order quote cannot be confirmed",
    defaultMessage:
      "Quote can only be confirmed when batch order is in quoted state",
  },
  confirmQuoteModalTitle: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmQuoteModalTitle",
    description: "Title for the confirm quote modal",
    defaultMessage: "Confirm Quote",
  },
  confirmQuoteError: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmQuoteError",
    description: "Error message when quote confirmation fails",
    defaultMessage: "Failed to confirm quote. Please try again.",
  },
  confirmPurchaseOrderDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmPurchaseOrderDisabled",
    description: "Text when the batch order purchase order cannot be confirmed",
    defaultMessage:
      "Purchase order can only be confirmed when batch order is in quoted state with purchase order payment method, quote is signed, and total is set",
  },
  confirmBankTransferDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmBankTransferDisabled",
    description: "Text when the batch order bank transfer cannot be confirmed",
    defaultMessage:
      "Bank transfer can only be confirmed when batch order uses bank transfer payment method and is in pending, signing, or process payment state",
  },
  submitForSignatureDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.submitForSignatureDisabled",
    description: "Text when the batch order cannot be submitted for signature",
    defaultMessage:
      "Batch order can only be submitted for signature when in assigned, quoted, or to sign state",
  },
  generateOrdersDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.generateOrdersDisabled",
    description: "Text when the batch order orders cannot be generated",
    defaultMessage:
      "Orders can only be generated when batch order is in completed state",
  },
});

type Props = {
  batchOrder: BatchOrder;
};

export default function BatchOrderActionsButton({ batchOrder }: Props) {
  const intl = useIntl();
  const batchOrdersQuery = useBatchOrders({}, { enabled: false });
  const batchOrderQuery = useBatchOrder(batchOrder.id);
  const confirmQuoteModal = useModal();

  const handleConfirmQuote = async (total: string) => {
    batchOrdersQuery.methods.confirmQuote(
      {
        batchOrderId: batchOrder.id,
        total,
      },
      {
        onSuccess: batchOrderQuery.methods.invalidate,
      },
    );
  };

  const options = useMemo(() => {
    const allOptions: MenuOption[] = [
      {
        icon: <CheckCircleIcon />,
        mainLabel: intl.formatMessage(batchOrderActionsMessages.confirm_quote),
        isDisable: !batchOrder.available_actions.confirm_quote,
        disableMessage: intl.formatMessage(messages.confirmQuoteDisabled),
        onClick: confirmQuoteModal.handleOpen,
      },
      {
        icon: <CheckCircleIcon />,
        mainLabel: intl.formatMessage(
          batchOrderActionsMessages.confirm_purchase_order,
        ),
        isDisable: !batchOrder.available_actions.confirm_purchase_order,
        disableMessage: intl.formatMessage(
          messages.confirmPurchaseOrderDisabled,
        ),
        onClick: async () => {
          batchOrdersQuery.methods.confirmPurchaseOrder(
            { batchOrderId: batchOrder.id },
            { onSuccess: batchOrderQuery.methods.invalidate },
          );
        },
      },
      {
        icon: <CheckCircleIcon />,
        mainLabel: intl.formatMessage(
          batchOrderActionsMessages.confirm_bank_transfer,
        ),
        isDisable: !batchOrder.available_actions.confirm_bank_transfer,
        disableMessage: intl.formatMessage(
          messages.confirmBankTransferDisabled,
        ),
        onClick: async () => {
          batchOrdersQuery.methods.confirmBankTransfer(
            { batchOrderId: batchOrder.id },
            { onSuccess: batchOrderQuery.methods.invalidate },
          );
        },
      },
      {
        icon: <DrawIcon />,
        mainLabel: intl.formatMessage(
          batchOrderActionsMessages.submit_for_signature,
        ),
        isDisable: !batchOrder.available_actions.submit_for_signature,
        disableMessage: intl.formatMessage(messages.submitForSignatureDisabled),
        onClick: async () => {
          batchOrdersQuery.methods.submitForSignature(
            { batchOrderId: batchOrder.id },
            { onSuccess: batchOrderQuery.methods.invalidate },
          );
        },
      },
      {
        icon: <PlaylistAddCheckIcon />,
        mainLabel: intl.formatMessage(
          batchOrderActionsMessages.generate_orders,
        ),
        isDisable: !batchOrder.available_actions.generate_orders,
        disableMessage: intl.formatMessage(messages.generateOrdersDisabled),
        onClick: async () => {
          batchOrdersQuery.methods.generateOrders(
            { batchOrderId: batchOrder.id },
            { onSuccess: batchOrderQuery.methods.invalidate },
          );
        },
      },
      {
        icon: <CancelIcon />,
        mainLabel: intl.formatMessage(batchOrderActionsMessages.cancel),
        isDisable: !batchOrder.available_actions.cancel,
        disableMessage: intl.formatMessage(messages.alreadyCancelTooltip),
        onClick: async () => {
          await batchOrderQuery.methods.delete(batchOrder.id, {
            onSuccess: batchOrdersQuery.methods.invalidate,
          });
        },
      },
    ];

    return allOptions;
  }, [batchOrder, confirmQuoteModal]);

  if (options.length === 0) {
    return undefined;
  }

  return (
    <>
      <ButtonMenu
        data-testid="order-view-action-button"
        label={intl.formatMessage(messages.batchOrderActionsLabel)}
        id="order-view-action-button"
        variant="outlined"
        options={options}
      />
      <ConfirmQuoteModal
        title={intl.formatMessage(messages.confirmQuoteModalTitle)}
        open={confirmQuoteModal.open}
        handleClose={confirmQuoteModal.handleClose}
        onConfirm={handleConfirmQuote}
      />
    </>
  );
}
