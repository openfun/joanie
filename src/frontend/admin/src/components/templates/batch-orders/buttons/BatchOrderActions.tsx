import * as React from "react";
import { useMemo } from "react";
import { defineMessages, useIntl } from "react-intl";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  BatchOrder,
  BatchOrderPaymentMethodEnum,
  BatchOrderStatesEnum,
} from "@/services/api/models/BatchOrder";
import ButtonMenu, {
  MenuOption,
} from "@/components/presentational/button/menu/ButtonMenu";
import {
  useBatchOrder,
  useBatchOrders,
} from "@/hooks/useBatchOrders/useBatchOrders";
import { useModal } from "@/components/presentational/modal/useModal";
import { ConfirmQuoteModal } from "@/components/templates/batch-orders/modals/ConfirmQuoteModal";

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
  cancelBatchOrder: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.cancelBatchOrder",
    description: "Label for the cancel batch order action",
    defaultMessage: "Cancel this batch order",
  },
  confirmQuote: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmQuote",
    description: "Label for the confirm quote action",
    defaultMessage: "Confirm quote",
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
  confirmPurchaseOrder: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmPurchaseOrder",
    description: "Label for the confirm purchase order action",
    defaultMessage: "Confirm purchase order",
  },
  confirmPurchaseOrderDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmPurchaseOrderDisabled",
    description: "Text when the batch order purchase order cannot be confirmed",
    defaultMessage:
      "Purchase order can only be confirmed when batch order is in quoted state with purchase order payment method, quote is signed, and total is set",
  },
  confirmBankTransfer: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmBankTransfer",
    description: "Label for the confirm bank transfer action",
    defaultMessage: "Confirm bank transfer",
  },
  confirmBankTransferDisabled: {
    id: "components.templates.batch-orders.buttons.batchOrderActionsButton.confirmBankTransferDisabled",
    description: "Text when the batch order bank transfer cannot be confirmed",
    defaultMessage:
      "Bank transfer can only be confirmed when batch order uses bank transfer payment method and is in pending, signing, or process payment state",
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
        mainLabel: intl.formatMessage(messages.confirmQuote),
        isDisable:
          batchOrder.state !== BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED,
        disableMessage: intl.formatMessage(messages.confirmQuoteDisabled),
        onClick: confirmQuoteModal.handleOpen,
      },
      {
        icon: <CheckCircleIcon />,
        mainLabel: intl.formatMessage(messages.confirmPurchaseOrder),
        isDisable:
          batchOrder.state !== BatchOrderStatesEnum.BATCH_ORDER_STATE_QUOTED ||
          batchOrder.payment_method !==
            BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_PURCHASE_ORDER ||
          !batchOrder.total,
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
        mainLabel: intl.formatMessage(messages.confirmBankTransfer),
        isDisable:
          batchOrder.payment_method !==
            BatchOrderPaymentMethodEnum.BATCH_ORDER_WITH_BANK_TRANSFER ||
          ![
            BatchOrderStatesEnum.BATCH_ORDER_STATE_SIGNING,
            BatchOrderStatesEnum.BATCH_ORDER_STATE_PENDING,
            BatchOrderStatesEnum.BATCH_ORDER_STATE_PROCESS_PAYMENT,
          ].includes(batchOrder.state),
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
        icon: <CancelIcon />,
        mainLabel: intl.formatMessage(messages.cancelBatchOrder),
        isDisable: [BatchOrderStatesEnum.BATCH_ORDER_STATE_CANCELED].includes(
          batchOrder.state,
        ),
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
