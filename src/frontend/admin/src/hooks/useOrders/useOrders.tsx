import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { Order, OrderListItem, OrderQuery } from "@/services/api/models/Order";
import { OrderRepository } from "@/services/repositories/orders/OrderRepository";
import { HttpError } from "@/services/http/HttpError";

export const useOrdersMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useOrders.errorUpdate",
    description:
      "Error message shown to the user when order update request fails.",
    defaultMessage:
      "An error occurred while updating the order. Please retry later.",
  },
  successCertificateGenerate: {
    id: "hooks.useOrders.successCertificateGenerate",
    description:
      "Success message shown to the user when the certificate has been generated.",
    defaultMessage: "Certificate successfully generated.",
  },
  successRefund: {
    id: "hooks.useOrders.successRefund",
    description:
      "Success message shown to the user when the order is being refunded.",
    defaultMessage: "Refunding order.",
  },
  errorGet: {
    id: "hooks.useOrders.errorGet",
    description:
      "Error message shown to the user when orders fetch request fails.",
    defaultMessage:
      "An error occurred while fetching orders. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useOrders.errorDelete",
    description:
      "Error message shown to the user when order deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the order. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useOrders.errorCreate",
    description:
      "Error message shown to the user when order creation request fails.",
    defaultMessage:
      "An error occurred while creating the order. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useOrders.errorNotFound",
    description: "Error message shown to the user when no order matches.",
    defaultMessage: "Cannot find the order",
  },
  errorExport: {
    id: "hooks.useOrders.errorExport",
    description:
      "Error message shown to the user when order export request fails.",
    defaultMessage:
      "An error occurred while exporting orders. Please retry later.",
  },
});

export type OrderListQuery = ResourcesQuery & {
  product_ids?: string[];
  course_ids?: string[];
  organization_ids?: string[];
  owner_ids?: string[];
  productId?: string;
  courseId?: string;
  organizationId?: string;
  ownerId?: string;
  state?: string;
};

const listProps: UseResourcesProps<OrderListItem, OrderListQuery> = {
  queryKey: ["ordersList"],
  apiInterface: () => ({
    get: async (filters) => {
      return OrderRepository.getAll(filters);
    },
  }),
  session: true,
  messages: useOrdersMessages,
};

const orderProps: UseResourcesProps<Order, OrderQuery> = {
  queryKey: ["orders"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return OrderRepository.get(id, otherFilters);
      }
    },
    delete: async (id: string) => {
      return OrderRepository.delete(id);
    },
    refund: async (id: string) => {
      return OrderRepository.refund(id);
    },
    export: async (filters) => {
      return OrderRepository.export(filters);
    },
  }),
  session: true,
  messages: useOrdersMessages,
};

export const useOrders = (
  filters?: OrderQuery,
  queryOptions?: QueryOptions<OrderListItem>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...listProps, filters, queryOptions });
  const mutation = useMutation;
  return {
    ...custom,
    methods: {
      ...custom.methods,
      generateCertificate: mutation({
        mutationFn: async (data: { orderId: string }) => {
          return OrderRepository.generateCertificate(data.orderId);
        },
        onSuccess: () => {
          custom.methods.invalidate();
          custom.methods.showSuccessMessage(
            intl.formatMessage(useOrdersMessages.successCertificateGenerate),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useOrdersMessages.errorUpdate),
          );
        },
      }).mutate,
      refund: mutation({
        mutationFn: async (data: { orderId: string }) => {
          return OrderRepository.refund(data.orderId);
        },
        onSuccess: () => {
          custom.methods.invalidate();
          custom.methods.showSuccessMessage(
            intl.formatMessage(useOrdersMessages.successRefund),
          );
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useOrdersMessages.errorUpdate),
          );
        },
      }).mutate,
      export: mutation({
        mutationFn: async (data: { currentFilters: OrderListQuery }) => {
          return OrderRepository.export(data.currentFilters);
        },
        onError: (error: HttpError) => {
          custom.methods.setError(
            error.data?.details ??
              intl.formatMessage(useOrdersMessages.errorExport),
          );
        },
      }).mutate,
    },
  };
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrder = useResource(orderProps);
