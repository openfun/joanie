import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  ResourcesQuery,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
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
  }),
  session: true,
  messages: useOrdersMessages,
};

// eslint-disable-next-line react-hooks/rules-of-hooks
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
    },
  };
};
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrder = useResource(orderProps);
