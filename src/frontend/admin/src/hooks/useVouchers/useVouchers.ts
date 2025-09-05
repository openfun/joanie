import { defineMessages } from "react-intl";
import {
  useResource,
  useResources,
  UseResourcesProps,
} from "@/hooks/useResources";
import { Voucher, VoucherQuery } from "@/services/api/models/Voucher";
import { VoucherRepository } from "@/services/repositories/voucher/VoucherRepository";

export const useVouchersMessages = defineMessages({
  errorUpdate: {
    id: "hooks.useVouchers.errorUpdate",
    description:
      "Message d'erreur affiché à l'utilisateur quand la mise à jour d'un voucher échoue.",
    defaultMessage:
      "Une erreur est survenue lors de la mise à jour du voucher. Veuillez réessayer plus tard.",
  },
  errorGet: {
    id: "hooks.useVouchers.errorGet",
    description:
      "Message d'erreur affiché à l'utilisateur quand la récupération des vouchers échoue.",
    defaultMessage:
      "Une erreur est survenue lors de la récupération des vouchers. Veuillez réessayer plus tard.",
  },
  errorDelete: {
    id: "hooks.useVouchers.errorDelete",
    description:
      "Message d'erreur affiché à l'utilisateur quand la suppression d'un voucher échoue.",
    defaultMessage:
      "Une erreur est survenue lors de la suppression du voucher. Veuillez réessayer plus tard.",
  },
  errorCreate: {
    id: "hooks.useVouchers.errorCreate",
    description:
      "Message d'erreur affiché à l'utilisateur quand la création d'un voucher échoue.",
    defaultMessage:
      "Une erreur est survenue lors de la création du voucher. Veuillez réessayer plus tard.",
  },
  errorNotFound: {
    id: "hooks.useVouchers.errorNotFound",
    description:
      "Message d'erreur affiché à l'utilisateur quand aucun voucher ne correspond.",
    defaultMessage: "Impossible de trouver le voucher",
  },
});

export type VoucherListQuery = VoucherQuery & {};

const listProps: UseResourcesProps<Voucher, VoucherListQuery> = {
  queryKey: ["vouchersList"],
  apiInterface: () => ({
    get: async (filters) => {
      return VoucherRepository.getAll(filters);
    },
  }),
  session: true,
  messages: useVouchersMessages,
};

const props: UseResourcesProps<Voucher, VoucherQuery> = {
  queryKey: ["vouchers"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return VoucherRepository.get(id, otherFilters);
      }
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
export const useVouchers = useResources(listProps);

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useVoucher = useResource(props);
