import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Discount, DiscountQuery } from "@/services/api/models/Discount";
import { DiscountRepository } from "@/services/repositories/discount/DiscountRepository";

export const useDiscountsMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useDiscounts.errorUpdate",
    description:
      "Error message shown to the user when discount update request fails.",
    defaultMessage:
      "An error occurred while updating the discount. Please retry later.",
  },
  errorGet: {
    id: "hooks.useDiscounts.errorGet",
    description:
      "Error message shown to the user when discounts fetch request fails.",
    defaultMessage:
      "An error occurred while fetching discounts. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useDiscounts.errorDelete",
    description:
      "Error message shown to the user when discount deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the discount. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useDiscounts.errorCreate",
    description:
      "Error message shown to the user when discount creation request fails.",
    defaultMessage:
      "An error occurred while creating the discount. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useDiscounts.errorNotFound",
    description: "Error message shown to the user when no discount matches.",
    defaultMessage: "Cannot find the discount",
  },
});

export type DiscountListQuery = DiscountQuery & {};

const listProps: UseResourcesProps<Discount, DiscountListQuery> = {
  queryKey: ["discountsList"],
  apiInterface: () => ({
    get: async (filters) => {
      return DiscountRepository.getAll(filters);
    },
  }),
  session: true,
  messages: useDiscountsMessages,
};

const props: UseResourcesProps<Discount, DiscountQuery> = {
  queryKey: ["discounts"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return DiscountRepository.get(id, otherFilters);
      }
    },
    create: DiscountRepository.create,
    update: ({ id, ...payload }) => {
      return DiscountRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return DiscountRepository.delete(id);
    },
  }),
  session: true,
  messages: useDiscountsMessages,
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useDiscounts = useResources(listProps);

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useDiscount = useResource(props);
