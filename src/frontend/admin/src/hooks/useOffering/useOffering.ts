import { defineMessages, useIntl } from "react-intl";
import { useMutation } from "@tanstack/react-query";
import {
  QueryOptions,
  useResource,
  useResourcesCustom,
  UseResourcesProps,
} from "@/hooks/useResources";
import { ResourcesQuery } from "@/hooks/useResources/types";
import { OfferingRepository } from "@/services/repositories/offering/OfferingRepository";
import { Offering } from "@/services/api/models/Offerings";
import { DTOOfferingRule } from "@/services/api/models/OfferingRule";

const messages = defineMessages({
  errorUpdate: {
    id: "hooks.useCourseProductRelation.errorUpdate",
    description:
      "Error message shown to the user when course product relation update request fails.",
    defaultMessage:
      "An error occurred while updating the course product relation. Please retry later.",
  },
  errorUpdateOfferingRule: {
    id: "hooks.useCourseProductRelation.errorUpdateOfferingRule",
    description:
      "Error message shown to the user when offering rule update request fails.",
    defaultMessage:
      "An error occurred while updating the offering rule. Please retry later.",
  },
  errorGet: {
    id: "hooks.useCourseProductRelation.errorGet",
    description:
      "Error message shown to the user when course product relations fetch request fails.",
    defaultMessage:
      "An error occurred while fetching course product relations. Please retry later.",
  },
  errorDelete: {
    id: "hooks.useCourseProductRelation.errorDelete",
    description:
      "Error message shown to the user when course product relation deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the course product relation. Please retry later.",
  },
  errorDeleteOfferingRule: {
    id: "hooks.useCourseProductRelation.errorDeleteOfferingRule",
    description:
      "Error message shown to the user when offering rule deletion request fails.",
    defaultMessage:
      "An error occurred while deleting the offering rule. Please retry later.",
  },
  errorCreate: {
    id: "hooks.useCourseProductRelation.errorCreate",
    description:
      "Error message shown to the user when course product relation creation request fails.",
    defaultMessage:
      "An error occurred while creating the course product relation. Please retry later.",
  },
  errorCreateOfferingRule: {
    id: "hooks.useCourseProductRelation.errorCreateOfferingRule",
    description:
      "Error message shown to the user when offering rule creation request fails.",
    defaultMessage:
      "An error occurred while creating the offering rule. Please retry later.",
  },
  errorNotFound: {
    id: "hooks.useCourseProductRelation.errorNotFound",
    description:
      "Error message shown to the user when no course product relations matches.",
    defaultMessage: "Cannot find the course product relation",
  },
});

/**
 * Joanie Api hook to retrieve/create/update/delete course product relations
 * owned by the authenticated user.
 */
const props: UseResourcesProps<Offering, ResourcesQuery> = {
  queryKey: ["offering"],
  apiInterface: () => ({
    get: async (filters) => {
      if (filters?.id) {
        const { id, ...otherFilters } = filters;
        return OfferingRepository.get(id, otherFilters);
      }

      return OfferingRepository.getAll(filters);
    },
    create: OfferingRepository.create,
    update: async ({ id, ...payload }) => {
      return OfferingRepository.update(id, payload);
    },
    delete: async (id: string) => {
      return OfferingRepository.delete(id);
    },
  }),
  session: true,
  messages,
};

export const useOfferings = (
  filters?: ResourcesQuery,
  queryOptions?: QueryOptions<Offering>,
) => {
  const intl = useIntl();
  const custom = useResourcesCustom({ ...props, filters, queryOptions });
  const mutation = useMutation;

  return {
    ...custom,
    methods: {
      ...custom.methods,
      addOfferingRule: mutation({
        mutationFn: async (data: {
          offeringId: string;
          payload: DTOOfferingRule;
        }) => {
          return OfferingRepository.addOfferingRule(
            data.offeringId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorCreateOfferingRule),
          );
        },
      }).mutate,
      editOfferingRule: mutation({
        mutationFn: async (data: {
          offeringId: string;
          offeringRuleId: string;
          payload: DTOOfferingRule;
        }) => {
          return OfferingRepository.editOfferingRule(
            data.offeringId,
            data.offeringRuleId,
            data.payload,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorUpdateOfferingRule),
          );
        },
      }).mutate,
      deleteOfferingRule: mutation({
        mutationFn: async (data: {
          offeringId: string;
          offeringRuleId: string;
        }) => {
          return OfferingRepository.deleteOfferingRule(
            data.offeringId,
            data.offeringRuleId,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorDeleteOfferingRule),
          );
        },
      }).mutate,
      getOfferingRule: mutation({
        mutationFn: async (data: {
          offeringId: string;
          offeringRuleId: string;
        }) => {
          return OfferingRepository.getOfferingRule(
            data.offeringId,
            data.offeringRuleId,
          );
        },
        onSuccess: () => {
          custom.methods.invalidate();
        },
        onError: () => {
          custom.methods.setError(
            intl.formatMessage(messages.errorDeleteOfferingRule),
          );
        },
      }).mutate,
    },
  };
};

// eslint-disable-next-line react-hooks/rules-of-hooks
export const useOffering = useResource(props);
