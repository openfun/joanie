import { defineMessages } from "react-intl";
import {
  ResourcesQuery,
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Order, OrderListItem, OrderQuery } from "@/services/api/models/Order";
import { OrderRepository } from "@/services/repositories/orders/OrderRepository";

export const useOrdersMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useOrders.errorUpdate",
    description:
      "Error message shown to the user when order update request fails.",
    defaultMessage:
      "An error occurred while updating the order. Please retry later.",
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
export const useOrders = useResources(listProps);
// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOrder = useResource(orderProps);
