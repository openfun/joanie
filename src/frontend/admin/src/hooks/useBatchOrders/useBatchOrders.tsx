import { defineMessages } from "react-intl";
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

export const useBatchOrdersMessages = defineMessages({
  errorGet: {
    id: "hooks.useBatchOrders.errorGet",
    description:
      "Error message shown to the user when batch orders fetch request fails.",
    defaultMessage:
      "An error occurred while fetching batch orders. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useBatchOrders.errorNotFound",
    description: "Error message shown to the user when no batch order matches.",
    defaultMessage: "Cannot find the batch order",
  },
});

export type BatchOrderListQuery = ResourcesQuery & {
  organization_ids?: string[];
  owner_ids?: string[];
  organizationId?: string;
  ownerId?: string;
  state?: string;
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

export const useBatchOrders = (
  filters?: BatchOrderListQuery,
  queryOptions?: QueryOptions<BatchOrderListItem>,
) => useResourcesCustom({ ...listProps, filters, queryOptions });
