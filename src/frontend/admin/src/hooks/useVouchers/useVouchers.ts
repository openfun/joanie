import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Voucher, VoucherQuery } from "@/services/api/models/Voucher";
import { VoucherRepository } from "@/services/repositories/voucher/VoucherRepository";
import { ApiResourceInterface } from "@/hooks/useResources/types";

export const useVouchersMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useVouchers.errorUpdate",
    description:
      "Error message shown to the user when voucher update request fails.",
    defaultMessage:
      "An error occurred while updating the voucher. Please retry later.",
  },
  errorGet: {
    id: "hooks.useVouchers.errorGet",
    description:
      "Error message shown to the user when vouchers fetch request fails.",
    defaultMessage:
      "An error occurred while fetching vouchers. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useVouchers.errorDelete",
    description:
      "Error message shown to the user when voucher deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the voucher. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useVouchers.errorCreate",
    description:
      "Error message shown to the user when voucher creation request fails.",
    defaultMessage:
      "An error occurred while creating the voucher. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useVouchers.errorNotFound",
    description: "Error message shown to the user when no voucher matches.",
    defaultMessage: "Cannot find the voucher",
  },
});

const props: UseResourcesProps<
  Voucher,
  VoucherQuery,
  ApiResourceInterface<Voucher, VoucherQuery>
> = {
  queryKey: ["vouchers"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return VoucherRepository.get(id, otherFilters);
      }
      return VoucherRepository.getAll(filters);
    },
    create: VoucherRepository.create,
    update: ({ id, ...payload }) => {
      return VoucherRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return VoucherRepository.delete(id);
    },
  }),
  session: true,
  messages: useVouchersMessages,
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useVouchers = useResources(props);

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useVoucher = useResource(props);
