import { defineMessages } from "react-intl";
import { BatchOrderStatesEnum } from "@/services/api/models/BatchOrder";

export const batchOrderStatesMessages = defineMessages<BatchOrderStatesEnum>({
  draft: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.draft",
    defaultMessage: "Draft",
    description: "Text for draft batch order state",
  },
  assigned: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.assigned",
    defaultMessage: "Assigned",
    description: "Text for assigned batch order state",
  },
  quoted: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.quoted",
    defaultMessage: "Quoted",
    description: "Text for quoted batch order state",
  },
  to_sign: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.to_sign",
    defaultMessage: "To sign",
    description: "Text for to sign batch order state",
  },
  signing: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.signing",
    defaultMessage: "Signing",
    description: "Text for signing batch order state",
  },
  pending: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.pending",
    defaultMessage: "Pending",
    description: "Text for pending batch order state",
  },
  process_payment: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.process_payment",
    defaultMessage: "Process payment",
    description: "Text for process payment batch order state",
  },
  failed_payment: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.failed_payment",
    defaultMessage: "Failed payment",
    description: "Text for failed payment batch order state",
  },
  canceled: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.canceled",
    defaultMessage: "Canceled",
    description: "Text for canceled batch order state",
  },
  completed: {
    id: "components.templates.batch-orders.view.batchOrderStatesMessages.completed",
    defaultMessage: "Completed",
    description: "Text for completed batch order state",
  },
});

export const batchOrderPaymentMethodsMessages = defineMessages({
  purchase_order: {
    id: "components.templates.batch-orders.view.batchOrderPaymentMethodsMessages.purchase_order",
    defaultMessage: "Purchase order",
    description: "Text for purchase order payment method",
  },
  bank_transfer: {
    id: "components.templates.batch-orders.view.batchOrderPaymentMethodsMessages.bank_transfer",
    defaultMessage: "Bank transfer",
    description: "Text for bank transfer payment method",
  },
  card_payment: {
    id: "components.templates.batch-orders.view.batchOrderPaymentMethodsMessages.card_payment",
    defaultMessage: "Card payment",
    description: "Text for card payment payment method",
  },
});
