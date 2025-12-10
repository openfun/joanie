import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import {
  BatchOrder,
  BatchOrderListItem,
  BatchOrderQuery,
} from "@/services/api/models/BatchOrder";
import { BatchOrderRepository } from "@/services/repositories/batch-orders/BatchOrderRepository";
import { HttpError } from "@/services/http/HttpError";

export const useBatchOrdersMessages = defineMessages({
  errorGet: {
    id: "hooks.useBatchOrders.errorGet",
    description:
      "Error message shown to the user when batch orders fetch request fails.",
    defaultMessage:
      "An error occurred while fetching batch orders. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useBatchOrders.errorDelete",
    description:
      "Error message shown to the user when batch order deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the batch order. Please retry later.",
  },
  successConfirmQuote: {
    id: "hooks.useBatchOrders.successConfirmQuote",
    description:
      "Success message shown to the user when the batch order quote has been confirmed.",
    defaultMessage: "Batch order quote confirmed.",
  },
  errorConfirmQuote: {
    id: "hooks.useBatchOrders.errorConfirmQuote",
    description:
      "Error message shown to the user when batch order confirm quote request fails.",
    defaultMessage:
      "An error occurred while confirming the quote. Please retry later.",
  },
  successConfirmPurchaseOrder: {
    id: "hooks.useBatchOrders.successConfirmPurchaseOrder",
    description:
      "Success message shown to the user when the batch order purchase order has been confirmed.",
    defaultMessage: "Batch order purchase order confirmed.",
  },
  errorConfirmPurchaseOrder: {
    id: "hooks.useBatchOrders.errorConfirmPurchaseOrder",
    description:
      "Error message shown to the user when batch order confirm purchase order request fails.",
    defaultMessage:
      "An error occurred while confirming the purchase order. Please retry later.",
  },
  successConfirmBankTransfer: {
    id: "hooks.useBatchOrders.successConfirmBankTransfer",
    description:
      "Success message shown to the user when the batch order bank transfer has been confirmed.",
    defaultMessage: "Batch order bank transfer confirmed.",
  },
  errorConfirmBankTransfer: {
    id: "hooks.useBatchOrders.errorConfirmBankTransfer",
    description:
      "Error message shown to the user when batch order confirm bank transfer request fails.",
    defaultMessage:
      "An error occurred while confirming the bank transfer. Please retry later.",
  },
  successSubmitForSignature: {
    id: "hooks.useBatchOrders.successSubmitForSignature",
    description:
      "Success message shown to the user when the batch order has been submitted for signature.",
    defaultMessage:
      "Batch order submitted for signature. Invitation link sent.",
  },
  errorSubmitForSignature: {
    id: "hooks.useBatchOrders.errorSubmitForSignature",
    description:
      "Error message shown to the user when batch order submit for signature request fails.",
    defaultMessage:
      "An error occurred while submitting for signature. Please retry later.",
  },
  successGenerateOrders: {
    id: "hooks.useBatchOrders.successGenerateOrders",
    description:
      "Success message shown to the user when the batch order orders have been generated.",
    defaultMessage:
      "Batch order orders generated. Voucher codes sent to owner.",
  },
  errorGenerateOrders: {
    id: "hooks.useBatchOrders.errorGenerateOrders",
    description:
      "Error message shown to the user when batch order generate orders request fails.",
    defaultMessage:
      "An error occurred while generating orders. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useBatchOrders.errorNotFound",
    description: "Error message shown to the user when no batch order matches.",
    defaultMessage: "Cannot find the batch order",
  },
  errorExport: {
    id: "hooks.useBatchOrders.errorExport",
    description:
      "Error message shown to the user when batch order export request fails.",
    defaultMessage:
      "An error occurred while exporting batch orders. Please retry later.",
  },
});

export type BatchOrderListQuery = ResourcesQuery & {
  organization_ids?: string[];
  owner_ids?: string[];
  organizationId?: string;
  ownerId?: string;
  state?: string;
  payment_method?: string;
};

const listProps: UseResourcesProps<BatchOrderListItem, BatchOrderListQuery> = {
  queryKey: ["batchOrdersList"],
  apiInterface: () => ({
    get: async (filters) => {
      return BatchOrderRepository.getAll(filters);
    },
  }),
  session: true,
  messages: useBatchOrdersMessages,
};

const resourceProps: UseResourcesProps<BatchOrder, BatchOrderQuery> = {
  queryKey: ["batchOrders"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return BatchOrderRepository.get(id, otherFilters);
      }
    },
    delete: async (id: string) => {
      return BatchOrderRepository.delete(id);
    },
  }),
  session: true,
  messages: useBatchOrdersMessages,
};

export const useBatchOrders = (
  filters?: BatchOrderListQuery,
  queryOptions?: QueryOptions<BatchOrderListItem>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...listProps, filters, queryOptions });
  const mutation = useMutation;
  return {
    ...custom,
    methods: {
      ...custom.methods,
      confirmQuote: mutation({
        mutationFn: async (data: { batchOrderId: string; total: string }) => {
          return BatchOrderRepository.confirmQuote(
            data.batchOrderId,
            data.total,
          );
        },
        onSuccess: async () => {
          custom.methods.showSuccessMessage(
            intl.formatMessage(useBatchOrdersMessages.successConfirmQuote),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useBatchOrdersMessages.errorConfirmQuote),
          );
        },
      }).mutate,
      confirmPurchaseOrder: mutation({
        mutationFn: async (data: { batchOrderId: string }) => {
          return BatchOrderRepository.confirmPurchaseOrder(data.batchOrderId);
        },
        onSuccess: async () => {
          custom.methods.showSuccessMessage(
            intl.formatMessage(
              useBatchOrdersMessages.successConfirmPurchaseOrder,
            ),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(
                useBatchOrdersMessages.errorConfirmPurchaseOrder,
              ),
          );
        },
      }).mutate,
      confirmBankTransfer: mutation({
        mutationFn: async (data: { batchOrderId: string }) => {
          return BatchOrderRepository.confirmBankTransfer(data.batchOrderId);
        },
        onSuccess: async () => {
          custom.methods.showSuccessMessage(
            intl.formatMessage(
              useBatchOrdersMessages.successConfirmBankTransfer,
            ),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(
                useBatchOrdersMessages.errorConfirmBankTransfer,
              ),
          );
        },
      }).mutate,
      submitForSignature: mutation({
        mutationFn: async (data: { batchOrderId: string }) => {
          return BatchOrderRepository.submitForSignature(data.batchOrderId);
        },
        onSuccess: async () => {
          custom.methods.showSuccessMessage(
            intl.formatMessage(
              useBatchOrdersMessages.successSubmitForSignature,
            ),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(
                useBatchOrdersMessages.errorSubmitForSignature,
              ),
          );
        },
      }).mutate,
      generateOrders: mutation({
        mutationFn: async (data: { batchOrderId: string }) => {
          return BatchOrderRepository.generateOrders(data.batchOrderId);
        },
        onSuccess: async () => {
          custom.methods.showSuccessMessage(
            intl.formatMessage(useBatchOrdersMessages.successGenerateOrders),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useBatchOrdersMessages.errorGenerateOrders),
          );
        },
      }).mutate,
      export: mutation({
        mutationFn: async (data: { currentFilters: BatchOrderListQuery }) => {
          return BatchOrderRepository.export(data.currentFilters);
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useBatchOrdersMessages.errorExport),
          );
        },
      }).mutate,
    },
  };
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useBatchOrder = useResource(resourceProps);
